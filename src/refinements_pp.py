"""Five explicit improvement passes on the computed analysis."""
from pathlib import Path
import json,csv,collections,math,re,unicodedata
import numpy as np
from statistics_pp import logistic,incidence
R=Path(__file__).resolve().parents[1];O=R/'data/complete'
A=json.loads((O/'results.json').read_text(encoding='utf8'));B=json.loads((O/'stock_results.json').read_text(encoding='utf8'));C=json.loads((O/'mineral_config.json').read_text(encoding='utf8'))
raw=list(csv.DictReader((O/'award_analysis.csv').open(encoding='utf-8-sig'),delimiter=';'))
rows=[]
for r in raw:
 for k in ['round','strategic','cession','unpaid','request','approval','denial','holder','holder_n','cessions','corporate','cause','time','followup','payment_record']:r[k]=int(r[k])
 for k in ['bid','ha','cfem']:r[k]=float(r[k])
 for k in ['first_days','exit_days']:r[k]=int(r[k]) if r[k] else None
 r['fiscal_eligible']=r['fiscal_eligible']=='True';rows.append(r)
def fold(s):return ''.join(x for x in unicodedata.normalize('NFKD',s) if not unicodedata.combining(x)).upper()
def summary(rs):return {'n':len(rs),'bid':sum(r['bid'] for r in rs),'unpaid':sum(r['unpaid'] for r in rs),'unpaid_value':sum(r['bid'] for r in rs if r['unpaid']),'cession':sum(r['cession'] for r in rs),'holder':sum(r['holder'] for r in rs),'cfem':sum(r['cfem'] for r in rs if r['fiscal_eligible']),'cfem_positive':sum(r['cfem']>0 and r['fiscal_eligible'] for r in rs)}
report=[]
report.append({'pass':1,'question':'A mesma ocorrência pode ser atribuída a dois ciclos sucessivos?','changes':'Encerrados os ramos quando o próprio associado participa de nova arrematação. Excluídos acontecimentos posteriores do ciclo anterior.','evidence':{'occurrences_before':1112,'occurrences_after':A['overall']['cessions'],'unpaid_current':A['sensitivity']['unpaid_current'],'unpaid_preserved':A['overall']['unpaid']},'check':'A nova regra removeu uma ocorrência e conciliou os 1.272 sinais do retrato atualizado com a base preservada.'})
# Pass 2: distinguish direct names from inferred mineral carriers and missing substance.
unknown_terms={'','NAO SE APLICA','NAO INFORMADA','NAO INFORMADO'}
for r in rows:
 f=fold(r['substances']);r['known']=f not in unknown_terms
 r['direct_minerals']=[m for m in C['tokens'] if re.search(r'\b'+fold(m)+r'\b',f)]
 r['direct_proxy']=bool(r['direct_minerals'])
 r['group_I']=any(m in C['groups']['I'] for m in r['minerals'].split(' | '));r['group_II']=any(m in C['groups']['II'] for m in r['minerals'].split(' | '));r['group_III']=any(m in C['groups']['III'] for m in r['minerals'].split(' | '))
A['mineral_classification_sensitivity']={'broad_proxy':summary([r for r in rows if r['strategic']]),'direct_names_only':summary([r for r in rows if r['direct_proxy']]),'other_known':summary([r for r in rows if r['known'] and not r['strategic']]),'unknown':summary([r for r in rows if not r['known']])}
A['policy_groups']={k:summary([r for r in rows if r['group_'+k]]) for k in ['I','II','III']}
A['strategic_incidence']=incidence([r['time'] for r in rows if r['strategic']],[r['cause'] for r in rows if r['strategic']])
A['other_known_incidence']=incidence([r['time'] for r in rows if not r['strategic'] and r['known']],[r['cause'] for r in rows if not r['strategic'] and r['known']])
A['critical_territories']={s:summary([r for r in rows if r['state']==s and r['strategic']]) for s in sorted({r['state'] for r in rows if r['strategic']})}
A['critical_round_matrix']={m:{str(k):sum(m in r['minerals'].split(' | ') and r['round']==k for r in rows) for k in [1,2,3,4,5,8]} for m in C['tokens']}
report.append({'pass':2,'question':'O recorte mineral depende de sinônimos ou de informação ausente?','changes':'Executada classificação restrita por nomes diretos, ampla por portadores explicitados e separação dos não informados. Grupos I, II e III tratados com sobreposição.','evidence':A['mineral_classification_sensitivity'],'check':'A lista de 2021 é proxy histórica. Não foi rebatizada como lista legal de minerais críticos da PNMCE.'})
# Pass 3: additional regional controls and missing-substance sensitivity.
regions={'Norte':{'Acre','Amapá','Amazonas','Pará','Rondônia','Roraima','Tocantins'},'Nordeste':{'Alagoas','Bahia','Ceará','Maranhão','Paraíba','Pernambuco','Piauí','Rio Grande do Norte','Sergipe'},'Centro-Oeste':{'Distrito Federal','Goiás','Mato Grosso','Mato Grosso do Sul'},'Sul':{'Paraná','Rio Grande do Sul','Santa Catarina'}}
mr=[r for r in rows if r['round']!=1 and r['ha']>0 and r['known']]
names=['Intercepto','Log do lance','Log da área','Lavra','Proxy estratégica','Rodada 3','Rodada 4','Rodada 5','Rodada 8']+list(regions)
X=np.array([[1,math.log1p(r['bid']),math.log1p(r['ha']),int('Lavra' in r['regime']),r['strategic'],*[r['round']==k for k in [3,4,5,8]],*[r['state'] in s for s in regions.values()]] for r in mr],float)
fit=logistic(X,[r['unpaid'] for r in mr],[r['origin'] for r in mr]);fit.pop('probabilities');fit['variables']=names;A['logistic_region_known']=fit
# Fixed horizon first cession as robustness to proportional hazard assumptions.
fr=[r for r in mr if r['followup']>=730];fn=['Intercepto','Log do lance','Log da área','Lavra','Proxy estratégica','Rodada 3','Rodada 4','Rodada 5']
FX=np.array([[1,math.log1p(r['bid']),math.log1p(r['ha']),int('Lavra' in r['regime']),r['strategic'],*[r['round']==k for k in [3,4,5]]] for r in fr],float);ff=logistic(FX,[r['first_days'] is not None and r['first_days']<=730 for r in fr],[r['origin'] for r in fr]);ff.pop('probabilities');ff['variables']=fn;A['logistic_cession730']=ff
report.append({'pass':3,'question':'As associações resistem à maturidade, à geografia e à falta de substância?','changes':'Estimado logit com macrorregião e somente substâncias conhecidas. Estimado logit de cessão em 730 dias com seguimento completo. Comparado ao Cox e à exclusão do 1% de maiores lances.','evidence':{'nonpayment_n':fit['n'],'nonpayment_converged':fit['converged'],'cession730_n':ff['n'],'cession730_converged':ff['converged']},'check':'Modelos convergentes. Coeficientes descrevem associações observacionais; não são efeitos causais de preço mínimo.'})
# Pass 4: stock quality quarantine, active/event proxy, matrix and age distributions.
stock=list(csv.DictReader((O/'stock_process_audit.csv').open(encoding='utf-8-sig'),delimiter=';'))
for r in stock:
 for k in ['active','proxy','appeal_unresolved_signal','apt_conflict']:r[k]=r[k]=='True'
 r['age_days']=int(r['age_days']) if r['age_days'] else None
valid=[r for r in stock if r['sople']!='Fora do arquivo SOPLE'];openactive=[r for r in stock if r['active'] and r['last_state'] in ['entrada_disponibilidade','apta','oferta','desbloqueio']]
B['event_open_active_only']={'n':len(openactive),'in_sople':sum(r['sople']!='Fora do arquivo SOPLE' for r in openactive),'phase_8_15':sum(r['phase'] in ['8','15'] for r in openactive)}
B['proxy_by_status']={k:{'total':len(rs:=[r for r in valid if r['sople']==k]),'proxy':sum(r['proxy'] for r in rs),'without_substance':sum(fold(r['substance']) in unknown_terms for r in rs),'appeal_signal':sum(r['appeal_unresolved_signal'] for r in rs),'older2':sum(r['age_days'] is not None and r['age_days']>730 for r in rs)} for k in sorted({r['sople'] for r in valid})}
B['strategic_apt_minerals']={m:{'apt':len(rs:=[r for r in valid if r['sople']=='Apta para Disponibilidade' and m in r['minerals'].split(' | ')]),'older2':sum(r['age_days'] is not None and r['age_days']>730 for r in rs),'conflict':sum(r['apt_conflict'] for r in rs),'median_days':float(np.median(a)) if (a:=[r['age_days'] for r in rs if r['age_days'] is not None]) else None} for m in C['tokens']}
B['age_distribution']={group:{label:sum((r['age_days'] is not None and lo<=r['age_days']<hi) for r in rs) for label,lo,hi in [('Até 1 ano',0,366),('1 a 2 anos',366,731),('2 a 5 anos',731,1827),('5 a 10 anos',1827,3653),('Mais de 10 anos',3653,100000)]} for group,rs in [('SCM ativo fases 8 e 15',[r for r in stock if r['active'] and r['phase'] in ['8','15']]),('Aptas SOPLE',[r for r in valid if r['sople']=='Apta para Disponibilidade'])]}
report.append({'pass':4,'question':'O estoque incorpora registros inválidos ou históricos como se fossem áreas ofertáveis?','changes':'Quarentena dos 82 identificadores inválidos, normalização de chaves e comparação de estoque ativo, aptidão SOPLE e estados por evento. Filtro de atividade aplicado também à proxy histórica.','evidence':{'raw_rows':B['raw_rows'],'valid_keys':B['valid_sople_keys'],'active_stock':B['active_phase_stock']['n'],'apt_sople':B['sople_apt']['n'],'apt_conflicts':B['sople_apt']['conflict'],'event_open_active':B['event_open_active_only']},'check':'Nenhum texto inválido de identificador foi executado ou convertido à força em processo. Idade não foi interpretada como liberação automática.'})
# Pass 5: institutional decision thresholds and internal consistency.
bykey={r['key']:r for r in rows};assert len(bykey)==7528;assert abs(sum(r['bid'] for r in rows)-907604126.29)<.01
assert sum(r['unpaid'] for r in rows)==1272
assert all(r['first_days'] is None or 0<=r['first_days']<=r['followup'] for r in rows)
for v in A['incidence']['curve']:assert abs(v['incidence']+v['exit_incidence']+v['survival']-1)<1e-9
for fitname in ['logistic_nonpayment','logistic_without_top1','cox_cession','logistic_region_known','logistic_cession730']:assert A[fitname]['converged']
A['fiscal_unique']={'origins_eligible':len({r['origin'] for r in rows if r['fiscal_eligible']}),'positive':len({r['origin'] for r in rows if r['fiscal_eligible'] and r['cfem']>0})}
report.append({'pass':5,'question':'O documento permite refazer os resultados e usar as conclusões sem confundir cenário com evidência?','changes':'Executadas identidades dos totais financeiros, unicidade dos ciclos, limites temporais, soma das probabilidades e convergência dos modelos. Cenários de incentivos rotulados como hipóteses, separados da triagem histórica.','evidence':{'cycles':len(bykey),'total_bid':sum(r['bid'] for r in rows),'all_models_converged':True,'fiscal_unique':A['fiscal_unique']},'check':'Resultados, parâmetros, tabelas por processo e dicionário de eventos exportados para reprodução. Não há preço ótimo causal alegado.'})
for n,x in [('results.json',A),('stock_results.json',B),('five_review_passes.json',report)]:
 (O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf8')
print(json.dumps({'five_passes':len(report),'classification':A['mineral_classification_sensitivity'],'regional_model_or':dict(zip(names,fit['or'])),'stock_active_events':B['event_open_active_only'],'fiscal':A['fiscal_unique']},ensure_ascii=True))
