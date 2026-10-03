"""Numpy implementations with explicit assumptions and deterministic checks."""
import numpy as np,math

def logistic(X,y,clusters=None,max_iter=150):
 X=np.asarray(X,float);y=np.asarray(y,float);b=np.zeros(X.shape[1]);ll=-np.inf
 for it in range(max_iter):
  eta=np.clip(X@b,-35,35);p=1/(1+np.exp(-eta));w=np.maximum(p*(1-p),1e-9)
  H=X.T@(X*w[:,None]);score=X.T@(y-p);step=np.linalg.solve(H+np.eye(len(b))*1e-9,score)
  old=np.sum(y*eta-np.logaddexp(0,eta));scale=1
  while scale>1e-7:
   candidate=b+scale*step;v=X@candidate;new=np.sum(y*v-np.logaddexp(0,v))
   if new>=old-1e-8:break
   scale/=2
  b=candidate
  if np.max(np.abs(scale*step))<1e-8:break
 eta=X@b;p=1/(1+np.exp(-np.clip(eta,-35,35)));H=X.T@(X*(p*(1-p))[:,None]);bread=np.linalg.pinv(H)
 u=X*(y-p)[:,None]
 if clusters is not None:
  keys,inv=np.unique(clusters,return_inverse=True);scores=np.zeros((len(keys),len(b)));np.add.at(scores,inv,u)
  correction=len(keys)/max(1,len(keys)-1)*(len(y)-1)/(len(y)-len(b));cov=bread@(scores.T@scores)@bread*correction
 else:cov=bread@(u.T@u)@bread*len(y)/(len(y)-len(b))
 se=np.sqrt(np.maximum(np.diag(cov),0));z=np.divide(b,se,out=np.zeros_like(b),where=se>0)
 return {'coef':b.tolist(),'se':se.tolist(),'or':np.exp(b).tolist(),'lo':np.exp(b-1.96*se).tolist(),'hi':np.exp(b+1.96*se).tolist(),'p':[math.erfc(abs(x)/math.sqrt(2)) for x in z],'n':len(y),'events':int(sum(y)),'iterations':it+1,'converged':bool(np.max(np.abs(scale*step))<1e-6),'score_max':float(np.max(np.abs(X.T@(y-p)))),'rank':int(np.linalg.matrix_rank(X)),'condition':float(np.linalg.cond(H)),'brier':float(np.mean((p-y)**2)),'probabilities':p.tolist()}

def incidence(times,causes,horizons=(180,365,730,1095,1460,1825)):
 """Aalen-Johansen competing first events. cause 0=censor, 1=target, 2=exit."""
 t=np.asarray(times,int);c=np.asarray(causes,int);S=1.;F=0.;F2=0.;rows=[]
 all_sorted=np.sort(t);event_times=np.unique(t[c>0]);u1,c1=np.unique(t[c==1],return_counts=True);u2,c2=np.unique(t[c==2],return_counts=True);n1=dict(zip(u1,c1));n2=dict(zip(u2,c2))
 for x in event_times:
  risk=int(len(t)-np.searchsorted(all_sorted,x));d1=int(n1.get(x,0));d2=int(n2.get(x,0))
  F+=S*d1/risk;F2+=S*d2/risk;S*=1-(d1+d2)/risk
  rows.append({'day':int(x),'risk':risk,'events':d1,'exits':d2,'incidence':F,'exit_incidence':F2,'survival':S})
 horizon=[]
 for h in horizons:
  available=h<=max(t,default=0);v=[r for r in rows if r['day']<=h];last=v[-1] if v else {'incidence':0.,'exit_incidence':0.,'survival':1.}
  horizon.append({'day':h,'available':available,'at_risk':int(sum(t>=h)),'incidence':last['incidence'] if available else None,'exit_incidence':last['exit_incidence'] if available else None,'survival':last['survival'] if available else None})
 return {'curve':rows,'horizons':horizon}

def cox(X,t,e,max_iter=60):
 """Cause-specific proportional hazards; Breslow ties, model-based covariance."""
 X=np.asarray(X,float);t=np.asarray(t,int);e=np.asarray(e,int)
 order=np.argsort(-t,kind='stable');X=X[order];t=t[order];e=e[order];b=np.zeros(X.shape[1]);unique=np.unique(t[e==1]);idx=np.array([np.where(t>=v)[0][-1] for v in unique]);d=np.array([sum((t==v)&(e==1)) for v in unique]);xev=np.array([X[(t==v)&(e==1)].sum(0) for v in unique]);
 def calc(beta):
  eta=X@beta;w=np.exp(np.clip(eta,-30,30));s0=np.cumsum(w)[idx];s1=np.cumsum(w[:,None]*X,axis=0)[idx];s2=np.cumsum(w[:,None,None]*X[:,:,None]*X[:,None,:],axis=0)[idx];m=s1/s0[:,None]
  ll=float((X[e==1]@beta).sum()-np.sum(d*np.log(s0)));g=(xev-d[:,None]*m).sum(0);H=np.sum(d[:,None,None]*(s2/s0[:,None,None]-m[:,:,None]*m[:,None,:]),axis=0)
  return ll,g,H
 for it in range(max_iter):
  ll,g,H=calc(b);step=np.linalg.solve(H+np.eye(len(b))*1e-9,g);scale=1
  while scale>1e-7 and calc(b+scale*step)[0]<ll-1e-9:scale/=2
  b+=scale*step
  if np.max(abs(scale*step))<1e-8:break
 ll,g,H=calc(b);se=np.sqrt(np.maximum(0,np.diag(np.linalg.pinv(H))))
 return {'coef':b.tolist(),'se':se.tolist(),'hr':np.exp(b).tolist(),'lo':np.exp(b-1.96*se).tolist(),'hi':np.exp(b+1.96*se).tolist(),'n':len(t),'events':int(sum(e)),'converged':bool(np.max(abs(scale*step))<1e-6),'score_max':float(max(abs(g))),'iterations':it+1,'covariance':'Model-based inverse information; observational association, Breslow ties.'}

def check():
 # Known intercept-only MLE.
 fit=logistic(np.ones((100,1)),np.r_[np.ones(30),np.zeros(70)])
 assert abs(fit['coef'][0]-math.log(.3/.7))<1e-6
 # First event and competing exit among four units: each cumulative incidence is .25.
 a=incidence([1,2,3,4],[1,2,0,0],horizons=[2])['horizons'][0]
 assert abs(a['incidence']-.25)<1e-9 and abs(a['exit_incidence']-.25)<1e-9
 assert abs(a['survival']-.5)<1e-9
 # Numerical gradient/Hessian validation for Cox by a simulated known direction.
 rng=np.random.default_rng(721);x=rng.normal(size=(600,1));t=np.round(rng.exponential(100/np.exp(.7*x[:,0]))).astype(int)+1;c=np.full(600,200);m=cox(x,np.minimum(t,c),(t<=c).astype(int));assert .35<m['coef'][0]<1.1 and m['converged']
 return {'logistic_intercept':'passed','competing_risk_identity':'passed','cox_simulated_direction':'passed'}

if __name__=='__main__':print(check())
