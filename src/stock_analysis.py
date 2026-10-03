from pathlib import Path
import json,csv,zipfile,io,collections,re,datetime,unicodedata,statistics
R=Path(__file__).resolve().parents[1];O=R/'data/complete';cut='2026-10-02'
def save(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def fold(s):return ''.join(x for x in unicodedata.normalize('NFKD',s) if not unicodedata.combining(x)).upper()
def proc(s):
 m=re.fullmatch(r'(\d{1,6})/(\d{4})',str(s).strip().replace('.',''))
 if not m:return ''
 n=m[1].zfill(6);return n[:3]+'.'+n[3:]+'/'+m[2]
def csvwrite(n,rows):
 with (O/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
cfg=json.loads((O/'mineral_config.json').read_text(encoding='utf8'))
def minerals(s):
 f=fold(s);out={k for k,terms in cfg['tokens'].items() if any(re.search(r'\b'+t+r'\b',f) for t in terms)}
 if 'COLUMBITA' in f:out.add('nióbio')
 return sorted(out)
source=list(csv.DictReader((R/'data/raw/EstoqueAreas.csv').open(encoding='utf-8-sig'),delimiter=';'));by={};bad=[]
for x in source:
 p=proc(x['ProcessoMinerario'])
 if p:
  if p in by:
   # Preserve the first nonempty value; never overwrite fuller metadata with blanks.
   by[p]={k:by[p].get(k) or x.get(k,'') for k in x}
  else:by[p]=x
 else:bad.append(x['ProcessoMinerario'])
z=zipfile.ZipFile(R/'data/raw/scm.zip')
def rows(n):
 path=next(x for x in z.namelist() if x.replace('\\','/').split('/')[-1]==n+'.txt')
 with io.TextIOWrapper(z.open(path),encoding='cp1252',errors='replace',newline='') as f:yield from csv.DictReader(f,delimiter=';')
names={x['IDEvento']:x['DSEvento'] for x in rows('Evento')};phases={x['IDFaseProcesso']:x['DSFaseProcesso'] for x in rows('FaseProcesso')}
rules={
 'entrada_disponibilidade':{'328','329','2463','2464','2865'},
 'apta':{'2275'},
 'selecionada':{'303','309','314','1123','1315','2465','2649','2651','2652'},
 'livre':{'99','2466','2470','2471','2472','2473','2743'},
 'suspensa':{'1313','2650'},
 'revisao':{'357','1348','1349','1350','1351','1352','1353','1354','1355','1666','1667','1809','1827','2653','2777','2956'},
 'oferta':{'305','310','677','1814','1836','2304','2305','2310','2338','2339','2467','2468','2469','2677','2802','2836'},
 'recurso_pendente':{'360','1805','1887'},
 'recurso_decidido':{'369','386','1806','1807','1888','1889','2963'},
 'desbloqueio':{'1883','2883'},
}
stage={code:k for k,cs in rules.items() for code in cs};events=collections.defaultdict(list);invalid_dates=0;total=0
for x in rows('ProcessoEvento'):
 total+=1
 if x['IDEvento'] not in stage:continue
 t=x['DTEvento'][:10];p=proc(x['DSProcesso'])
 if not p or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',t) or t>'2026-10-02':continue
 try:datetime.date.fromisoformat(t)
 except ValueError:invalid_dates+=1;continue
 events[p].append((t,x['IDEvento']))
print('Stock relevant events',sum(map(len,events.values())),len(events),flush=True)
P={};census=collections.Counter()
for x in rows('Processo'):
 p=proc(x['DSProcesso']);census[(x['IDFaseProcesso'],x['BTAtivo'])]+=1
 if p in by or p in events or x['IDFaseProcesso'] in ['8','15']:P[p]=x
statecodes=set().union(*(rules[k] for k in ['entrada_disponibilidade','apta','selecionada','livre','suspensa','revisao','oferta','desbloqueio']))
entrances=rules['entrada_disponibilidade']|rules['apta'];qual=[];history=collections.Counter();flow=collections.Counter();cross=collections.Counter();overlap=collections.Counter();yearly=collections.defaultdict(collections.Counter);eventcount=collections.Counter()
for p,x in P.items():
 ev=sorted(set(events.get(p,[])));oper=[e for e in ev if e[1] in statecodes];lastdate=oper[-1][0] if oper else '';same=[e for e in oper if e[0]==lastdate];states={stage[e[1]] for e in same};latest=next(iter(states)) if len(states)==1 else 'ambigua_mesma_data' if states else 'sem_evento_estado'
 entering=[e for e in oper if e[1] in entrances];lastentry=entering[-1][0] if entering else ''
 age=(datetime.date.fromisoformat(cut)-datetime.date.fromisoformat(lastentry)).days if lastentry else None
 rec=[e for e in ev if e[1] in rules['recurso_pendente']];dec=[e for e in ev if e[1] in rules['recurso_decidido']];appeal=bool(rec and (not dec or rec[-1][0]>dec[-1][0]))
 sx=by.get(p);status=sx['SituacaoEstoque'] if sx else 'Fora do arquivo SOPLE';active=x['BTAtivo']=='S';phase=x['IDFaseProcesso'];mins=minerals(sx['Substancia']) if sx else []
 discrepancy=bool(sx and status=='Apta para Disponibilidade' and ((not active) or latest in ['selecionada','livre','suspensa','revisao','ambigua_mesma_data'] or appeal))
 overlap['scm_active_8_15' if active and phase in ['8','15'] else 'other']+=1
 if sx:cross[(status,phase,x['BTAtivo'])]+=1
 for t,c in ev:eventcount[c]+=1
 for t,c in oper:flow[(t[:4],stage[c])]+=1
 for year in range(2020,2027):
  limit=f'{year}-12-31' if year<2026 else cut;relevant=[e for e in oper if e[0]<=limit]
  if relevant:
   lt=relevant[-1][0];ss={stage[c] for t,c in relevant if t==lt};yearly[str(year)][next(iter(ss)) if len(ss)==1 else 'ambigua_mesma_data']+=1
 qual.append({'process':p,'active':active,'phase':phase,'phase_name':phases.get(phase,''),'sople':status,'state':sx['UnidadeFederacao'] if sx else '', 'city':sx['Municipio'] if sx else '', 'substance':sx['Substancia'] if sx else '', 'minerals':' | '.join(mins),'proxy':bool(mins),'nominated':sx['IndicaNominacao'] if sx else '', 'listed':sx['IndicaDisponibilizacaoEdital'] if sx else '', 'last_operational_event':lastdate,'last_state':latest,'last_codes':' | '.join(c for t,c in same),'last_entry':lastentry,'age_days':age,'appeal_unresolved_signal':appeal,'apt_conflict':discrepancy,'entry_records':len(entering),'reentry':len(entering)>1})
csvwrite('stock_process_audit.csv',qual)
active=[r for r in qual if r['active'] and r['phase'] in ['8','15']];sople=[r for r in qual if r['sople']!='Fora do arquivo SOPLE'];apt=[r for r in sople if r['sople']=='Apta para Disponibilidade'];opencandidates=[r for r in qual if r['last_state'] in ['entrada_disponibilidade','apta','oferta','desbloqueio']]
def age_summary(rs):
 ages=[r['age_days'] for r in rs if r['age_days'] is not None]
 return {'n':len(rs),'dated':len(ages),'without_entry':len(rs)-len(ages),'median_days':statistics.median(ages) if ages else None,'over2years':sum(a>730 for a in ages),'over5years':sum(a>1826 for a in ages),'over10years':sum(a>3652 for a in ages),'unresolved_appeal':sum(r['appeal_unresolved_signal'] for r in rs),'proxy':sum(r['proxy'] for r in rs),'conflict':sum(r['apt_conflict'] for r in rs),'reentry':sum(r['reentry'] for r in rs)}
result={'date':cut,'raw_rows':len(source),'valid_sople_keys':len(by),'invalid_identifiers':len(bad),'invalid_examples':bad[:10],'scm_processes_examined':sum(census.values()),'scm_event_rows_examined':total,'event_coverage':len(events),'active_phase_stock':age_summary(active),'sople_apt':age_summary(apt),'event_open_candidates':age_summary(opencandidates),'sople_status':{k:age_summary([r for r in sople if r['sople']==k]) for k in sorted({r['sople'] for r in sople})},'phase_census':[{'phase':p,'active':a,'n':n} for (p,a),n in census.items()],'crosswalk':[{'sople':s,'phase':p,'active':a,'n':n} for (s,p,a),n in cross.items()],'active_in_sople':sum(r['sople']!='Fora do arquivo SOPLE' for r in active),'active_missing_sople':sum(r['sople']=='Fora do arquivo SOPLE' for r in active),'apt_active_8_15':sum(r['active'] and r['phase'] in ['8','15'] for r in apt),'apt_current_states':dict(collections.Counter(r['last_state'] for r in apt)),'yearly_event_states':{k:dict(v) for k,v in yearly.items()},'annual_event_counts':[{'year':y,'state':s,'n':n} for (y,s),n in flow.items() if y>='2020'],'regions':{uf:age_summary([r for r in sople if r['state']==uf]) for uf in sorted({r['state'] for r in sople})},'strategic_stock':{m:age_summary([r for r in sople if m in r['minerals'].split(' | ')]) for m in cfg['tokens']},'invalid_dates':invalid_dates,'event_rules':[{'code':c,'label':names[c],'state':stage[c],'records':eventcount[c],'justification':{'entrada_disponibilidade':'Entrada ou retorno explícito; exige leitura jurídica do caso.','apta':'Aptidão cadastral registrada; conferir requisitos atuais.','selecionada':'Seleção registrada, não comprovação de pagamento ou outorga.','livre':'Liberação explícita registrada; não converter em oferta disponível.','suspensa':'Suspensão ou bloqueio explícito.','revisao':'Ato cancelado, excluído ou sem efeito; não presumir retorno automático.','oferta':'Inclusão em procedimento, sem decisão final presumida.','recurso_pendente':'Sinal de recurso; protocolo não determina sozinho efeito suspensivo.','recurso_decidido':'Registro de decisão ou desistência; conferir recurso atingido.','desbloqueio':'Registro de desbloqueio, sem certificação integral de aptidão.'}[stage[c]]} for c in sorted(stage,key=int)],'interpretation':'Estoque por eventos é proxy histórica de estados documentados; não certifica disponibilidade jurídica nem aplica automaticamente prazo legal de dois anos.'}
save('stock_results.json',result);csvwrite('stock_event_codebook.csv',result['event_rules']);save('stock_conflicts.json',[r for r in apt if r['apt_conflict']])
print(json.dumps({k:result[k] for k in ['raw_rows','valid_sople_keys','invalid_identifiers','active_phase_stock','sople_apt','event_open_candidates','active_missing_sople']},ensure_ascii=True),flush=True)
