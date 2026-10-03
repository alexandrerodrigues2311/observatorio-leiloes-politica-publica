"""Executed PP analysis; all empirical outputs and scenarios are separately labeled."""
from pathlib import Path
import json,csv,collections,datetime,re,unicodedata,statistics,zipfile,io,hashlib,math
import numpy as np
from statistics_pp import logistic,incidence,cox,check
R=Path(__file__).resolve().parents[1];O=R/'data/complete';O.mkdir(exist_ok=True)
def save(name,obj):(O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf8')
def csvsave(name,rows):
 if not rows:return
 with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
def fold(s):return ''.join(x for x in unicodedata.normalize('NFKD',str(s)) if not unicodedata.combining(x)).upper()
def proc(s):
 m=re.fullmatch(r'(\d{1,6})/(\d{4})',str(s).strip().replace('.',''))
 if not m:return ''
 a=m[1].zfill(6);return a[:3]+'.'+a[3:]+'/'+m[2]
def days(a,b):return (datetime.date.fromisoformat(b[:10])-datetime.date.fromisoformat(a[:10])).days
def date(x):return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',x or ''))
def money(s):return float(str(s).replace('.','').replace(',','.')) if s else 0.
def readcsv(n):return list(csv.DictReader((R/'data/raw'/n).open(encoding='utf-8-sig'),delimiter=';'))
D=json.loads((R/'data/raw/analitico_preservado.json').read_text(encoding='utf8'));S=json.loads((R/'data/derived/scm_extract.json').read_text(encoding='utf8'))
cut='2026-10-02';exclusive='2026-10-03';ref={r['origem']:r for r in D['rows']};offers=readcsv('ResultadoRodadaDisponibilidade.csv');social=readcsv('ResultadoAvaliacaoSocial.csv');stock=readcsv('EstoqueAreas.csv')
offer_groups=collections.defaultdict(list)
for x in offers:offer_groups[(int(x['Rodada']),x['NumeroArea'],proc(x['ProcessoMinerario']))].append(x)
ref.update(D['cycleResolution']['rows'])
cut_by_round={int(a['round']):a['homologation'] for a in D['areaScenario']['areas']}

# A historical strategic-mineral proxy, explicitly not a PNMCE designation.
groups={'I':{'enxofre','fosfato','potássio','molibdênio'},'II':{'cobalto','cobre','estanho','grafita','platina','lítio','nióbio','níquel','silício','tálio','tântalo','terras raras','titânio','tungstênio','urânio','vanádio'},'III':{'alumínio','cobre','ferro','grafita','ouro','manganês','nióbio','urânio'}}
tokens={
 'enxofre':['ENXOFRE'],'fosfato':['FOSFATO','FOSFORITA','APATITA'],'potássio':['POTASSIO','SILVITA','CARNALITA'],'molibdênio':['MOLIBDENIO','MOLIBDENITA'],
 'cobalto':['COBALTO'],'cobre':['COBRE'],'estanho':['ESTANHO','CASSITERITA'],'grafita':['GRAFITA'],'platina':['PLATINA','PALADIO','RODIO','RUTENIO','IRIDIO','OSMIO'],
 'lítio':['LITIO','ESPODUMENIO','PETALITA','LEPIDOLITA'],'nióbio':['NIOBIO','PIROCLORO'],'níquel':['NIQUEL'],'silício':['SILICIO'],'tálio':['TALIO'],
 'tântalo':['TANTALO','TANTALITA'],'terras raras':['TERRAS RARAS','MONAZITA','XENOTIMA'],'titânio':['TITANIO','ILMENITA','RUTILO'],'tungstênio':['TUNGSTENIO','SCHEELITA','WOLFRAMITA'],
 'urânio':['URANIO'],'vanádio':['VANADIO'],'alumínio':['ALUMINIO','BAUXITA'],'ferro':['FERRO','HEMATITA','MAGNETITA'],'ouro':['OURO'],'manganês':['MANGANES']}
audit_sub={}
def classify(names):
 hits=set();amb=set()
 for name in names:
  f=fold(name);local=set()
  for mineral,terms in tokens.items():
   if any(re.search(r'\b'+t+r'\b',f) for t in terms):local.add(mineral)
  if 'COLUMBITA' in f:local|={'nióbio'};amb.add('columbita pode conter tântalo; apenas nióbio incluído')
  if 'QUARTZO' in f or 'QUARTZITO' in f or 'AREIA' in f:amb.add('material silicoso não incluído automaticamente como silício')
  audit_sub[name]={'original':name,'mapped':' | '.join(sorted(local)),'notes':' | '.join(sorted(amb))}
  hits|=local
 return sorted(hits),sorted(amb)
def substances(p,t=None):
 records=S['substances'].get(p,[])
 return sorted(set(x['name'] for x in records if not t or ((not x['DTInicioVigencia'] or x['DTInicioVigencia'][:10]<=t) and (not x['DTFimVigencia'] or x['DTFimVigencia'][:10]>=t))))

# Human-readable operational event codebook. Unclassified codes are retained, not guessed.
codebook=[];tax={}
for x in S['taxonomy']:
 code=x['code'];label=x['label'];f=fold(label);family=x['family'];stage=x['stage'];reason='Descrição literal do evento.'
 if code in ['119','339','108']:family='misto_incorporacao_cessao';reason='Descrição mistura incorporação e cessão; excluído da definição estrita.'
 if any(t in f for t in ['EMOLUMENT','PROVENIENTE','ASSENTIMENTO','CDN','EXIGENCIA','INTIMACAO','DOCUMENTO DIVERSO','COMPROVANTE']):stage='contexto';reason='Ato auxiliar; não prova pedido ou efetivação da cessão.'
 elif 'DISTRATO' in f:stage='pedido_distrato';reason='Solicitação de desfazimento não equivale a desfazimento efetivo.'
 elif any(t in f for t in ['ANULAD','CANCELAD','CASSAD','S/EFEITO']):stage='reversao_candidata';reason='Conferir o ato atingido. Reversão de negativa não equivale a anulação da cessão.'
 elif any(t in f for t in ['NEGAD','NEGA ']):stage='negativa';reason='Não representa transferência concluída.'
 item={**x,'family':family,'stage':stage,'justification':reason};codebook.append(item);tax[code]=item
strict={k for k,x in tax.items() if x['stage']=='efetivacao' and x['family'] in ['cessao_total','cessao_parcial']}
return_codes={'2463','2464','2466','2471','2472','2473'}
payment_codes={'2463','2471','2778'}
negative_payment={'2464','2472','2473'}
for code in sorted(return_codes|payment_codes|negative_payment,key=int):codebook.append({'code':code,'label':S['event_names'][code],'family':'pagamento_continuidade','stage':'interrupcao' if code in return_codes else 'pagamento_registrado','justification':'Evidência cadastral; não substitui conciliação bancária. Evento limitado ao ciclo correspondente.'})
save('event_codebook.json',codebook)
edges=collections.defaultdict(list)
for e in S['links']:edges[e['source']].append(e)
cycles=collections.defaultdict(list)
for a in D['areaScenario']['areas']:cycles[a['origin']].append(a['homologation'])
audits=[];all_events=[];trajectories=[];rows=[];seen_events=set()
cess_csv=collections.defaultdict(set)
with (R/'data/raw/Cessoes_de_Direitos.csv').open(encoding='cp1252',newline='') as f:
 for x in csv.DictReader(f):
  try:t=datetime.datetime.strptime(x['Data da Cessão'],'%d/%m/%Y').date().isoformat()
  except ValueError:continue
  cess_csv[proc(x['Processo'])].add(t)

for a in D['areaScenario']['areas']:
 start=a['homologation'];end=min([t for t in cycles[a['origin']] if t>start]+[exclusive]);root=a['origin'];rawref=ref[root]
 intervals={root:[(start,end)]};queue=collections.deque([(root,start,end)]);used=[];visited=set()
 while queue:
  p,lo,hi=queue.popleft()
  if (p,lo,hi) in visited:continue
  visited.add((p,lo,hi))
  for link in edges[p]:
   t=link['date'];stop=min(hi,link['end'] or hi)
   if not date(t) or not lo<=t<stop:continue
   child=link['target'];stop=min([v for v in cycles.get(child,[]) if v>=t]+[stop]);interval=(t,stop)
   if t>=stop:continue
   if child==root:continue
   used.append(link)
   if interval not in intervals.get(child,[]):intervals.setdefault(child,[]).append(interval);queue.append((child,t,stop))
 events=[]
 for p,windows in intervals.items():
  for e in S['events'].get(p,[]):
   if any(lo<=e['date']<hi for lo,hi in windows):events.append({**e,'process':p,'label':S['event_names'].get(e['code'],e['code']),'days':days(start,e['date'])})
 exits=[e for e in events if e['process']==root and e['code'] in return_codes]
 exit_day=min((e['days'] for e in exits),default=None)
 histories=[e for e in events if e['code'] in strict]
 unique={ (e['process'],e['date'],tax[e['code']]['family']):e for e in histories};histories=sorted(unique.values(),key=lambda e:(e['date'],e['process']))
 strict_events=[e for e in histories if exit_day is None or e['days']<exit_day]
 successor=[e for e in strict_events if e['process']!=root]
 root_only=[e for e in strict_events if e['process']==root]
 reversals=[e for e in events if e['code'] in tax and tax[e['code']]['stage']=='reversao_candidata']
 sensitive=[e for e in strict_events if not any(z['process']==e['process'] and z['date']>=e['date'] for z in reversals)]
 requests=[e for e in events if e['code'] in tax and tax[e['code']]['stage']=='pedido' and tax[e['code']]['family'] in ['cessao_total','cessao_parcial']]
 approvals=[e for e in events if e['code'] in tax and tax[e['code']]['stage']=='aprovacao' and tax[e['code']]['family'] in ['cessao_total','cessao_parcial']]
 denials=[e for e in events if e['code'] in tax and tax[e['code']]['stage']=='negativa']
 corporate=[e for e in events if e['code'] in tax and tax[e['code']]['stage']=='efetivacao' and e['code'] not in strict]
 owners=[]
 for p,windows in intervals.items():
  people=[x for x in S['owners'].get(p,[]) if x['role']=='1' and date(x['start'])]
  for x in people:
   if not any(lo<x['start']<hi for lo,hi in windows):continue
   prior=[y for y in people if y['id']!=x['id'] and y['start']<x['start'] and date(y['end']) and y['end']<=x['start']]
   if prior:
    prev=max(prior,key=lambda y:y['end']);owners.append({'process':p,'date':x['start'],'from':prev['id'],'to':x['id'],'gap':days(prev['end'],x['start'])})
 first=strict_events[0]['days'] if strict_events else None;follow=days(start,min(end,cut));cause=1 if first is not None and (exit_day is None or first<exit_day) else 2 if exit_day is not None else 0;time=first if cause==1 else exit_day if cause==2 else follow
 names=substances(root,start);minerals,ambiguity=classify(names);fallback=not names
 if fallback:names=[x.strip() for x in rawref['substancia'].split(';') if x.strip()];minerals,ambiguity=classify(names)
 offer=offer_groups.get((a['round'],str(a['area']),root),[]);winners=sorted(set(x['NomeVencedor'] for x in offer if x['Situacao']=='Arrematada'))
 raw_area=rawref.get('ha','');area=money(raw_area) if raw_area else 0
 post_titles=[e for e in events if e['code'] in {'201','323','400','625','624','705','730','2210'} and (first is not None and e['days']>first)]
 confirmed=[e for e in events if e['code'] in payment_codes];unpaid_new=[e for e in events if e['code'] in negative_payment]
 r={'key':a['key'],'origin':root,'round':a['round'],'area':str(a['area']),'start':start,'end':end,'bid':a['cents']/100,'unpaid':int(a['unpaid']),'unpaid_current':int(bool(unpaid_new)),'payment_record':int(bool(confirmed)),'payment_conflict':int(bool(confirmed) and bool(unpaid_new)),'winner':winners[0] if len(winners)==1 else '', 'state':rawref['uf'],'city':rawref['municipio'],'regime':rawref['regime'],'ha':area,'minerals':' | '.join(minerals),'strategic':int(bool(minerals)),'substance_fallback':fallback,'substances':'; '.join(names),'nodes':len(intervals),'request':int(bool(requests)),'approval':int(bool(approvals)),'denial':int(bool(denials)),'cession':int(bool(strict_events)),'cessions':len(strict_events),'total_cessions':sum(tax[e['code']]['family']=='cessao_total' for e in strict_events),'partial_cessions':sum(tax[e['code']]['family']=='cessao_parcial' for e in strict_events),'reversal':int(bool(reversals)),'cession_no_later_reversal':int(bool(sensitive)),'cession_successor_only':int(bool(successor)),'cession_root_only':int(bool(root_only) and not successor),'cession_excluding_unpaid':int(bool(strict_events) and not a['unpaid']),'corporate':int(bool(corporate)),'holder':int(bool(owners)),'holder_n':len({(x['process'],x['date'],x['to']) for x in owners}),'first_days':first,'exit_days':exit_day,'time':time,'cause':cause,'followup':follow,'first_cfem':rawref.get('primeiro_depois'),'cfem':(rawref.get('depois') or {}).get('reais',0),'fiscal_eligible':bool(rawref.get('depois') is not None and D['businessOutcomes']['origins'][root]['state'] not in ['returned_unpaid','free_unpaid','paid_without_request']),'post_cession_title':bool(post_titles),'csv_cession_match':int(any(e['date'] in cess_csv[e['process']] for e in strict_events))}
 rows.append(r)
 if strict_events or corporate or owners:
  enriched=[]
  relevant=[e for e in events if e['code'] in tax or e['code'] in return_codes|payment_codes|{'201','323','400','625','624','705','730','2210'}]
  for e in relevant:
   entry={k:e[k] for k in ['process','date','code','label','days']}
   entry['stage']=tax.get(e['code'],{}).get('stage','marco');entry['family']=tax.get(e['code'],{}).get('family','marco');entry['reversal_candidate']=any(z['process']==e['process'] and z['date']>=e['date'] for z in reversals)
   enriched.append(entry)
  trajectories.append({'summary':r,'links':used,'events':sorted(enriched,key=lambda x:(x['date'],x['process'])),'holders':[{**x,'from_name':S['people'].get(x['from'],{}).get('name','Não identificado'),'to_name':S['people'].get(x['to'],{}).get('name','Não identificado')} for x in owners]})
 for e in strict_events:
  all_events.append({'key':a['key'],'origin':root,'round':a['round'],'process':e['process'],'date':e['date'],'code':e['code'],'family':tax[e['code']]['family'],'days':e['days'],'matched_csv':e['date'] in cess_csv[e['process']]})
print('Trajectories built',len(rows),flush=True)
csvsave('award_analysis.csv',rows);csvsave('cession_events.csv',all_events);save('trajectories_internal.json',trajectories)

def summary(rs):
 event=[r['first_days'] for r in rs if r['first_days'] is not None]
 return {'n':len(rs),'bid':sum(r['bid'] for r in rs),'unpaid':sum(r['unpaid'] for r in rs),'unpaid_value':sum(r['bid'] for r in rs if r['unpaid']),'cession':sum(r['cession'] for r in rs),'cessions':sum(r['cessions'] for r in rs),'recurrent':sum(r['cessions']>1 for r in rs),'total':sum(r['total_cessions'] for r in rs),'partial':sum(r['partial_cessions'] for r in rs),'request':sum(r['request'] for r in rs),'approval':sum(r['approval'] for r in rs),'denial':sum(r['denial'] for r in rs),'reversal':sum(r['reversal'] for r in rs),'holder':sum(r['holder'] for r in rs),'corporate':sum(r['corporate'] for r in rs),'observed_median':float(np.median(event)) if event else None,'under180':sum(x<=180 for x in event),'under365':sum(x<=365 for x in event),'eligible':sum(r['fiscal_eligible'] for r in rs),'cfem_positive':sum(r['cfem']>0 and r['fiscal_eligible'] for r in rs),'payment_record':sum(r['payment_record'] for r in rs),'payment_conflict':sum(r['payment_conflict'] for r in rs)}
results={'overall':summary(rows),'by_round':{str(k):summary([r for r in rows if r['round']==k]) for k in sorted({r['round'] for r in rows})},'by_regime':{k:summary([r for r in rows if r['regime']==k]) for k in sorted({r['regime'] for r in rows})},'sensitivity':{k:sum(r[k] for r in rows) for k in ['cession','cession_no_later_reversal','cession_successor_only','cession_root_only','cession_excluding_unpaid','holder','csv_cession_match','unpaid_current','payment_record','payment_conflict']},'independent_event_keys':len({(e['process'],e['date'],e['family']) for e in all_events}),'overlap_holder_cession':dict(collections.Counter(f'cessao={r["cession"]};titular={r["holder"]}' for r in rows)),'code_counts':dict(collections.Counter(e['code'] for e in all_events))}
aj=incidence([r['time'] for r in rows],[r['cause'] for r in rows]);results['incidence']=aj
results['incidence_rounds']={str(k):incidence([r['time'] for r in rows if r['round']==k],[r['cause'] for r in rows if r['round']==k]) for k in sorted({r['round'] for r in rows})}
# Cluster bootstrap of first-event incidence at 365 and 730 days.
rng=np.random.default_rng(20261003);cluster=collections.defaultdict(list)
for r in rows:cluster[r['origin']].append(r)
ck=list(cluster);boot=[]
for b in range(200):
 sampled=[r for k in rng.choice(ck,len(ck),replace=True) for r in cluster[k]];v=incidence([r['time'] for r in sampled],[r['cause'] for r in sampled],horizons=[365,730])['horizons'];boot.append([x['incidence'] for x in v])
results['incidence_ci']={str(h):{'lo':float(np.quantile(np.array(boot)[:,i],.025)),'hi':float(np.quantile(np.array(boot)[:,i],.975)),'replicates':200} for i,h in enumerate([365,730])}
print('Incidence calculated',flush=True)

# Association models. No look-ahead covariates such as later titles.
modelrows=[r for r in rows if r['round']!=1 and r['ha']>0]
names=['Intercepto','Log do lance','Log da área','Regime lavra','Substância estratégica proxy','Rodada 3','Rodada 4','Rodada 5','Rodada 8']
X=np.array([[1,math.log1p(r['bid']),math.log1p(r['ha']),int('Lavra' in r['regime']),r['strategic'],*[int(r['round']==k) for k in [3,4,5,8]]] for r in modelrows]);Y=np.array([r['unpaid'] for r in modelrows]);cl=np.array([r['origin'] for r in modelrows])
fit=logistic(X,Y,cl);pred=fit.pop('probabilities');fit['variables']=names;fit['excluded_round1']='Nenhum sinal de não pagamento; exclusão evita separação completa.';results['logistic_nonpayment']=fit
threshold=np.quantile([r['bid'] for r in modelrows],.99);keep=np.array([r['bid']<=threshold for r in modelrows]);sens=logistic(X[keep],Y[keep],cl[keep]);sens.pop('probabilities');sens['variables']=names;sens['threshold']=threshold;results['logistic_without_top1']=sens
coxfit=cox(X[:,1:],[r['time'] for r in modelrows],[r['cause']==1 for r in modelrows]);coxfit['variables']=names[1:];results['cox_cession']=coxfit
# Complete-followup comparison to avoid maturity bias.
fixed=[r for r in rows if r['followup']>=730];results['fixed_730']={str(k):{'n':len(a:=[r for r in fixed if r['round']==k]),'cession':sum(r['first_days'] is not None and r['first_days']<=730 for r in a),'exit':sum(r['exit_days'] is not None and r['exit_days']<=730 for r in a)} for k in sorted({r['round'] for r in fixed})}
# Payment concentration, descriptive bands, winner portfolios without exposing personal IDs.
bands=[0,1000,10000,100000,1000000,float('inf')];results['bid_bands']=[]
for lo,hi in zip(bands,bands[1:]):
 rs=[r for r in rows if lo<=r['bid']<hi];results['bid_bands'].append({'lo':lo,'hi':None if math.isinf(hi) else hi,**summary(rs)})
unpaid=sorted([r['bid'] for r in rows if r['unpaid']],reverse=True);results['concentration']={str(k):sum(unpaid[:k])/sum(unpaid) for k in [1,5,10,20,50,100]}
winnergroups=collections.defaultdict(list)
for r in rows:
 if r['winner']:winnergroups[r['winner']].append(r)
results['winner_portfolios']=[{'size':label,**summary([r for rs in winnergroups.values() if lo<=len(rs)<=hi for r in rs])} for label,lo,hi in [('1',1,1),('2 a 5',2,5),('6 a 20',6,20),('21 ou mais',21,99999)]]
# Historical screen of minimum bid; explicitly not behavioral prediction.
results['minimum_screens']=[]
for reserve in [0,1000,5000,10000,25000,50000,100000,250000]:
 kept=[r for r in rows if r['bid']>=reserve];excluded=[r for r in rows if r['bid']<reserve];results['minimum_screens'].append({'reserve':reserve,'retained':len(kept),'excluded':len(excluded),'excluded_value':sum(r['bid'] for r in excluded),'excluded_signal':sum(r['unpaid'] for r in excluded),'excluded_signal_value':sum(r['bid'] for r in excluded if r['unpaid']),'remaining_signal_value':sum(r['bid'] for r in kept if r['unpaid'])})
# Stylized calibrated reduced-form sensitivity. NOT equilibrium or causal estimates.
base_rate=sum(Y)/len(Y);results['incentive_scenarios']=[]
for reserve in [0,10000,50000,100000]:
 kept=[r for r in rows if r['bid']>=reserve];nominal=sum(r['bid'] for r in kept);bad=sum(r['bid'] for r in kept if r['unpaid'])
 for guarantee in [0,.02,.05,.10]:
  for elasticity in [.5,1.5,3.]:
   entry=math.exp(-elasticity*guarantee)
   for efficacy in [0,.25,.5]:
    # Recovery on guarantee intentionally excluded; require lawful execution evidence.
    proxy=entry*(nominal-bad*(1-efficacy));results['incentive_scenarios'].append({'reserve':reserve,'guarantee':guarantee,'entry_elasticity':elasticity,'default_reduction_assumed':efficacy,'participation_factor':entry,'commitment_proxy':proxy,'guarantee_locked':entry*nominal*guarantee,'break_even_default_reduction':max(0,(nominal-bad)*(1/entry-1)/bad) if bad else None,'label':'Cenário hipotético; complemento do sinal não é pagamento confirmado.'})

# Strategic proxy on the financial cohorts and every round of offers.
results['strategic_comparison']={'proxy':summary([r for r in rows if r['strategic']]),'other':summary([r for r in rows if not r['strategic']])}
results['strategic_minerals']={m:summary([r for r in rows if m in r['minerals'].split(' | ')]) for m in tokens}
results['strategic_rounds']={str(k):summary([r for r in rows if r['round']==k and r['strategic']]) for k in sorted({r['round'] for r in rows})}
offered=[]
for (round_,area,p),rs in offer_groups.items():
 names=substances(p);mins,amb=classify(names);statuses=sorted(set(x['Situacao'] for x in rs));offered.append({'round':round_,'area':area,'process':p,'statuses':' | '.join(statuses),'substances':'; '.join(names),'minerals':' | '.join(mins),'proxy':int(bool(mins)),'coverage':bool(names),'basis':'Cadastro 02/10/2026; retrospectivo, não prova informação disponível no edital.'})
for x in social:
 p=proc(x['ProcessoMinerario']);mins,amb=classify(substances(p));offered.append({'round':6,'area':x['NumeroArea'],'process':p,'statuses':x['Situacao'],'substances':'; '.join(substances(p)),'minerals':' | '.join(mins),'proxy':int(bool(mins)),'coverage':bool(substances(p)),'basis':'Cadastro 02/10/2026; avaliação social.'})
# Dedup social records by area/process, preserving requested as terminal status.
offered_unique={}
for x in offered:
 key=(x['round'],x['area'],x['process'])
 if key not in offered_unique or x['statuses']=='Requerido':offered_unique[key]=x
offered=list(offered_unique.values());csvsave('all_rounds_minerals.csv',offered);csvsave('substance_mapping.csv',list(audit_sub.values()));results['all_rounds']={str(k):{'areas':len(rs:=[x for x in offered if x['round']==k]),'proxy':sum(x['proxy'] for x in rs),'without_substance':sum(not x['coverage'] for x in rs),'statuses':dict(collections.Counter(x['statuses'] for x in rs))} for k in range(1,9)}
results['mineral_proxy_note']='Resolução SGM/MME 2/2021, com minerais portadores explicitamente mapeados. Não equivale a enquadramento legal PNMCE nem a reserva comprovada.'
results['checks']=check();results['parameters']={'cutoff':cut,'fiscal_cutoff':'2026-06','bootstrap_seed':20261003,'bootstrap_replicates':200,'event_units':'processo/data/família dentro de ciclo e intervalo de associação','cox_ties':'Breslow','logistic_covariance':'sandwich agrupado por origem','first_event_competition':'retorno/liberação explícita da origem nos códigos 2463 2464 2466 2471 2472 2473','unpaid_model_outcome':'sinal preservado, não conciliação financeira','mineral_asof':'data da homologação, fallback explicitado; todas ofertas usam retrato 02/10/2026'}
save('results.json',results)
print(json.dumps({'overall':results['overall'],'sensitivity':results['sensitivity'],'models':[fit['converged'],coxfit['converged']],'checks':results['checks']},ensure_ascii=True),flush=True)
