"""Estimate stratified error only after all sampled units have adjudicated truth.
Usage: python evaluate_audit.py audit_sample_reviewed.csv
truth: 1 classification confirmed, 0 classification incorrect.
Requires both reviewers, source, reason, final decision and status=concluido.
Incomplete and unresolved documents remain missing, never implicit successes.
"""
import sys,csv,json,math,collections
def evaluate(path):
 rows=list(csv.DictReader(open(path,encoding='utf-8-sig'),delimiter=';'))
 required=['reviewer_1','reviewer_2','document_url','document_date','truth','decision','reason']
 pending=[r['id'] for r in rows if r['status']!='concluido' or r['truth'] not in ['0','1'] or any(not r[k].strip() for k in required)]
 if pending:return {'status':'incomplete','sample':len(rows),'pending':len(pending),'error_rate':None,'interval':None}
 groups=collections.defaultdict(list)
 for r in rows:groups[r['stratum']].append(r)
 N=sum(int(rr[0]['population_stratum']) for rr in groups.values());estimate=variance=0
 for h,rr in groups.items():
  Nh=int(rr[0]['population_stratum']);nh=len(rr);assert nh==int(rr[0]['sample_stratum'])
  errors=[1-int(r['truth']) for r in rr];p=sum(errors)/nh;estimate+=Nh/N*p
  if nh>1:variance+=(Nh/N)**2*(1-nh/Nh)*sum((x-p)**2 for x in errors)/(nh-1)/nh
  elif nh<Nh:raise ValueError('Non-census stratum requires at least two reviewed units')
 se=math.sqrt(variance)
 return {'status':'complete','population':N,'sample':len(rows),'weighted_error':estimate,'standard_error':se,'normal_interval_95':[max(0,estimate-1.96*se),min(1,estimate+1.96*se)],'warning':'Normal approximation may be poor for sparse errors; report stratum counts and consider design-based alternatives. Zero observed errors does not prove zero population error.'}
if __name__=='__main__':print(json.dumps(evaluate(sys.argv[1]),ensure_ascii=False,indent=2))
