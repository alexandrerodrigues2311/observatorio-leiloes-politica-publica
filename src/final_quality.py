from pathlib import Path
import json,csv,hashlib,re,zipfile
import numpy as np
from statistics_pp import logistic,cox
R=Path(__file__).resolve().parents[1];O=R/'data/complete'
# Independent finite-difference score check against a direct partial likelihood.
rng=np.random.default_rng(83);X=rng.normal(size=(140,2));t=rng.integers(1,90,size=140);e=(rng.random(140)>.3).astype(int);fit=cox(X,t,e);beta=np.array(fit['coef'])
def ll(b):
 return sum(float((X[(t==v)&(e==1)]@b).sum())-int(sum((t==v)&(e==1)))*np.log(np.exp(X[t>=v]@b).sum()) for v in np.unique(t[e==1]))
eps=1e-5;gradient=np.array([(ll(beta+np.eye(2)[j]*eps)-ll(beta-np.eye(2)[j]*eps))/(2*eps) for j in range(2)])
assert max(abs(gradient))<1e-5
XX=np.c_[np.ones(140),X];y=(rng.random(140)>.65).astype(int);lf=logistic(XX,y);bb=np.array(lf['coef'])
def logisticll(b):return float((y*(XX@b)-np.logaddexp(0,XX@b)).sum())
lg=np.array([(logisticll(bb+np.eye(3)[j]*eps)-logisticll(bb-np.eye(3)[j]*eps))/(2*eps) for j in range(3)])
assert max(abs(lg))<1e-5
aw=list(csv.DictReader((O/'award_analysis.csv').open(encoding='utf-8-sig'),delimiter=';'));inv=json.loads((R/'site/inventory.json').read_text(encoding='utf8'))
assert all(re.fullmatch(r'\d{3}\.\d{3}/\d{4}',r['origin']) for r in aw)
assert len(inv)==30861 and len({r['process'] for r in inv})==30861
assert sum(r['apt_conflict']=='True' for r in inv)==428
# Published data allowlist excludes taxpayer IDs, holders and free administrative notes.
assert all('winner' not in r and 'holders' not in r for r in json.loads((R/'site/awards.json').read_text(encoding='utf8')))
cases=json.loads((R/'site/cases.json').read_text(encoding='utf8'))
assert all('holders' not in c and all('note' not in e for e in c['events']) for c in cases.values())
report={'cox_independent_finite_difference_score_max':float(max(abs(gradient))),'logit_independent_finite_difference_score_max':float(max(abs(lg))),'public_inventory_unique':len(inv),'conflict_filter':428,'process_format':'passed','public_fields_allowlist':'passed','normalization_collision':{'process':'832.750/2006','rows':2,'status_both':'Não apta para Disponibilidade','rule':'Primeiro valor não vazio por campo. Identificador normalizado; sem alteração dos totais principais.'}}
(O/'final_quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True))
