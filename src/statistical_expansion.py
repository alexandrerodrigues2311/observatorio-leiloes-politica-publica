from pathlib import Path
import sys,csv,json,math,collections,hashlib
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.append(str(R.parent/'tmp/science'))
import scipy,statsmodels.api as sm
from scipy.stats import norm,rankdata
from statsmodels.duration.hazard_regression import PHReg
from statistics_pp import incidence
D=R/'data/expansion';D.mkdir(exist_ok=True)
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def csvsave(n,rows):
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
rows=list(csv.DictReader((R/'data/complete/award_analysis.csv').open(encoding='utf-8-sig'),delimiter=';'))
for r in rows:
 for k in ['round','bid','ha','unpaid','strategic','time','cause','followup','cession','cessions']:r[k]=float(r[k])
 r['known']=r['substances'].strip().upper() not in ['','NAO SE APLICA','NÃO SE APLICA','NÃO INFORMADA','NÃO INFORMADO']
regions={'Norte':{'Acre','Amapá','Amazonas','Pará','Rondônia','Roraima','Tocantins'},'Nordeste':{'Alagoas','Bahia','Ceará','Maranhão','Paraíba','Pernambuco','Piauí','Rio Grande do Norte','Sergipe'},'Centro-Oeste':{'Distrito Federal','Goiás','Mato Grosso','Mato Grosso do Sul'},'Sul':{'Paraná','Rio Grande do Sul','Santa Catarina'}}
mr=[r for r in rows if r['round']!=1 and r['ha']>0 and r['known']]
names=['Intercepto','Log do lance','Log da área','Lavra','Proxy estratégica','Rodada 3','Rodada 4','Rodada 5','Rodada 8']+list(regions)
def xrow(r,rounds=True):return [1,math.log1p(r['bid']),math.log1p(r['ha']),int('Lavra' in r['regime']),r['strategic']]+([int(r['round']==k) for k in [3,4,5,8]] if rounds else [])+[int(r['state'] in s) for s in regions.values()]
X=np.array([xrow(r) for r in mr]);y=np.array([r['unpaid'] for r in mr]);groups=np.array([r['origin'] for r in mr]);base=json.loads((R/'data/complete/results.json').read_bytes())
fit=sm.GLM(y,X,family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':groups})
diff=float(max(abs(fit.params-np.array(base['logistic_region_known']['coef']))))
print('independent logit',diff,flush=True)
def metrics(y,p):
 ranks=rankdata(p);n1=sum(y);n0=len(y)-n1;auc=(sum(ranks[y==1])-n1*(n1+1)/2)/(n1*n0) if n1*n0 else None
 return {'n':len(y),'events':int(sum(y)),'observed':float(np.mean(y)),'predicted':float(np.mean(p)),'brier':float(np.mean((y-p)**2)),'auc':float(auc) if auc is not None else None,'log_loss':float(-np.mean(y*np.log(np.clip(p,1e-10,1))+(1-y)*np.log(np.clip(1-p,1e-10,1))))}
# Origin-grouped folds prevent repeated origins leaking into training and testing.
fold=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5 for g in groups]);oof=np.zeros(len(mr));foldmetrics=[]
for k in range(5):
 tr=fold!=k;te=~tr;f=sm.GLM(y[tr],X[tr],family=sm.families.Binomial()).fit();oof[te]=f.predict(X[te]);foldmetrics.append(metrics(y[te],oof[te]))
cal=[]
for ids in np.array_split(np.argsort(oof),10):cal.append({'n':len(ids),'predicted':float(np.mean(oof[ids])),'observed':float(np.mean(y[ids]))})
calfit=sm.GLM(y,sm.add_constant(np.log(np.clip(oof,1e-8,1-1e-8)/(1-np.clip(oof,1e-8,1-1e-8)))),family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':groups})
TR=np.array([r['round']<8 for r in mr]);XT=np.array([xrow(r,False) for r in mr]);f=sm.GLM(y[TR],XT[TR],family=sm.families.Binomial()).fit();temporal=metrics(y[~TR],f.predict(XT[~TR]));temporal['training_n']=int(sum(TR));temporal['note']='Treino rodadas 2–5, teste rodada 8; especificação sem indicadores de rodada. Não mede inadimplência conciliada.'
# Independent Cox/Breslow implementation under the original analysis population.
cr=[r for r in rows if r['round']!=1 and r['ha']>0]
cn=['Log do lance','Log da área','Lavra','Proxy estratégica','Rodada 3','Rodada 4','Rodada 5','Rodada 8']
CX=np.array([[math.log1p(r['bid']),math.log1p(r['ha']),int('Lavra' in r['regime']),r['strategic'],*[int(r['round']==k) for k in [3,4,5,8]]] for r in cr]);tt=np.array([r['time'] for r in cr]);ee=np.array([r['cause']==1 for r in cr]);gg=np.array([r['origin'] for r in cr])
cf=PHReg(tt,CX,status=ee,ties='breslow').fit();cdiff=float(max(abs(cf.params-np.array(base['cox_cession']['coef']))));print('independent Cox',cdiff,flush=True)
interactions=[]
for cutoff in [365,730]:
 xx=[];start=[];end=[];ev=[];cg=[]
 for i,r in enumerate(cr):
  if tt[i]<=0:continue
  xx.append([*CX[i],0,0]);start.append(0);end.append(min(tt[i],cutoff));ev.append(int(ee[i] and tt[i]<=cutoff));cg.append(gg[i])
  if tt[i]>cutoff:
   xx.append([*CX[i],CX[i,0],CX[i,3]]);start.append(cutoff);end.append(tt[i]);ev.append(int(ee[i]));cg.append(gg[i])
 tf=PHReg(np.array(end),np.array(xx),status=np.array(ev),entry=np.array(start),ties='breslow').fit()
 for j,label in [(-2,'Log do lance × período posterior'),(-1,'Proxy estratégica × período posterior')]:
  interactions.append({'cutoff':cutoff,'variable':label,'ratio':float(np.exp(tf.params[j])),'lo':float(np.exp(tf.conf_int()[j,0])),'hi':float(np.exp(tf.conf_int()[j,1])),'p':float(tf.pvalues[j]),'covariance':'Informação do modelo; não robusta por origem. Contraste diagnóstico, não teste causal.'})
# Family-wise Holm adjustment for the four prespecified diagnostic contrasts.
ix=np.argsort([a['p'] for a in interactions]);last=0
for j,k in enumerate(ix):last=max(last,min(1,(len(ix)-j)*interactions[k]['p']));interactions[k]['p_holm']=last
print('time interactions done',flush=True)
# Bootstrap whole origins, including repeated allocations, not individual event rows.
rng=np.random.default_rng(20261004);unique=np.unique([r['origin'] for r in rows]);index={g:[] for g in unique}
for i,r in enumerate(rows):index[r['origin']].append(i)
times=np.array([int(r['time']) for r in rows]);causes=np.array([int(r['cause']) for r in rows]);boot=[]
for b in range(1000):
 ids=np.concatenate([index[g] for g in rng.choice(unique,len(unique),replace=True)]);z=incidence(times[ids],causes[ids],horizons=[365,730]);boot.append([h['incidence'] for h in z['horizons']])
boot=np.array(boot);ci=[{'day':h,'estimate':incidence(times,causes,horizons=[h])['horizons'][0]['incidence'],'lo':float(np.quantile(boot[:,j],.025)),'hi':float(np.quantile(boot[:,j],.975)),'bootstrap_sd':float(np.std(boot[:,j],ddof=1))} for j,h in enumerate([365,730])]
# A prospective, executable audit sample; truths intentionally remain blank.
stock=json.loads((R/'site/inventory.json').read_bytes())
def sample_audit(pop,stratum,key,target,name):
 strata=collections.defaultdict(list)
 for r in pop:strata[stratum(r)].append(r)
 allocations={k:min(len(v),max(8,round(target*len(v)/len(pop)))) for k,v in strata.items()};out=[];summary=[]
 for k,rr in sorted(strata.items()):
  nn=allocations[k];chosen=rng.choice(len(rr),nn,replace=False);summary.append({'stratum':k,'N':len(rr),'n':nn,'weight':len(rr)/nn})
  for i in chosen:
   r=rr[int(i)];out.append({'id':key(r),'stratum':k,'population_stratum':len(rr),'sample_stratum':nn,'weight':len(rr)/nn,'reviewer_1':'','reviewer_2':'','document_url':'','document_date':'','truth':'','decision':'','reason':'','status':'pendente'})
 csvsave(name,out);return {'population':len(pop),'sample':len(out),'strata':summary,'verified':0,'error_rate':None,'status':'Sorteio executado. Revisão documental humana ainda não realizada; nenhuma acurácia presumida.'}
auditstock=sample_audit(stock,lambda r:('estrategico' if r['minerals'] else 'outro')+'|'+('conflito' if r['apt_conflict']=='True' else 'sem_conflito')+'|'+('apto' if r['sople']=='Apta para Disponibilidade' else 'somente_scm'),lambda r:r['process'],400,'audit_stock_sample.csv')
auditcession=sample_audit(rows,lambda r:str(int(r['round']))+'|'+('cessao' if r['cession'] else 'sem_cessao'),lambda r:r['key'],300,'audit_cession_sample.csv')
# Planning calculations, not a field experiment or causal estimate.
power=[]
for p0 in [.05,.10,.17]:
 for rel in [.2,.3]:
  p1=p0*(1-rel);pm=(p0+p1)/2;n=math.ceil(((norm.ppf(.975)*math.sqrt(2*pm*(1-pm))+norm.ppf(.8)*math.sqrt(p0*(1-p0)+p1*(1-p1)))/(p0-p1))**2)
  for rho in [0,.01,.05]:
   de=1+19*rho;power.append({'baseline':p0,'relative_reduction':rel,'p1':p1,'icc':rho,'cluster_size':20,'design_effect':de,'n_per_arm_independent':n,'n_per_arm_cluster_adjusted':math.ceil(n*de),'clusters_per_arm':math.ceil(n*de/20),'alpha':.05,'power':.8})
report={'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'statsmodels':sm.__version__},'independent_logit_max_difference':diff,'independent_cox_max_difference':cdiff,'cross_validation':metrics(y,oof),'folds':foldmetrics,'calibration_deciles':cal,'calibration_intercept':float(calfit.params[0]),'calibration_slope':float(calfit.params[1]),'temporal_validation':temporal,'time_interactions':interactions,'bootstrap_replicates':1000,'bootstrap_origin_ci':ci,'stock_audit_design':auditstock,'cession_audit_design':auditcession,'pilot_power':power,'pilot_status':'Protocolo e dimensionamento executados. Não houve alteração de edital, tratamento de participantes ou experimento de campo.'}
assert diff<1e-5 and cdiff<1e-5
save('statistics_advanced.json',report);print(json.dumps({k:report[k] for k in ['independent_logit_max_difference','independent_cox_max_difference','cross_validation','temporal_validation','time_interactions','bootstrap_origin_ci']},ensure_ascii=True),flush=True)
