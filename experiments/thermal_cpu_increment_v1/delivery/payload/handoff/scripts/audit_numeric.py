"""Independent closed-form two-state propagation, labels, scores and boundary audit.
Does not import author evaluator or call an optimizer. Uses the delivered inputs and predictions.
"""
from pathlib import Path
import json,math,hashlib,bisect,statistics as st
import numpy as np
from functools import lru_cache
R=Path(__file__).resolve().parents[1]; M=R/'original/evidence/modeling'
def jl(p):
 with p.open() as f:
  return [json.loads(l) for l in f if l.strip()]
def js(p):return json.loads(p.read_text())
p=js(M/'vendor/src/tto_field/research/observer-spec.json')['dynamic']
samples=jl(M/'results/samples-and-causal-states.jsonl');preds=jl(M/'results/predictions.jsonl');nodes=jl(M/'results/physical-input-nodes.jsonl');along=jl(M/'results/A-long.jsonl')
sm={s['ref']:s for s in samples}; sample_times=[s['t'] for s in samples]; nt=[n['t'] for n in nodes]
# 2x2 exponential closed form with constant E; independent of scipy.linalg.expm.
@lru_cache(maxsize=100000)
def constants(dt,u):
 a,c=p['a'],p['c'];d=p['d0']+p['d1']*u
 tr=(-a-c-d)/2; delta=math.sqrt(tr*tr-a*d)
 v=math.exp(tr*dt); z=math.sinh(delta*dt)/delta if delta else dt; co=math.cosh(delta*dt)
 F=v*np.array([[co+z*(-a-tr), z*a],[z*c,co+z*(-c-d-tr)]])
 return F,d
def propagate(x,u,dt):
 F,d=constants(float(dt),float(u[2]));x=np.asarray(x,float);q=p['b_g']*u[0]+p['b_c']*u[1]
 # In steady state: Tf-Ts=q/a; c(Tf-Ts)=d(Ts-E).
 steady_s=x[...,2]+p['c']*q/(p['a']*d);steady=np.stack([steady_s+q/p['a'],steady_s],axis=-1)
 y=(x[...,:2]-steady)@F.T+steady
 return np.concatenate([y,x[...,2:3]],axis=-1)
def interval(a,b):
 ix=bisect.bisect_right(nt,a)-1
 if ix<0 or b>nt[-1]:return None
 pieces=[];left=a;epoch=nodes[ix]['epoch']
 while left<b:
  n=nodes[ix];right=min(b,nt[ix+1] if ix+1<len(nt) else b)
  if n['u'] is None or n['until']<right-1e-9 or n['epoch']!=epoch:return None
  pieces.append((right-left,n));left=right;ix+=1
 return pieces
branches=['AUGMENTED-KF','CONDITIONAL-HOLD','QS','LP30','LP120'];hold_n=roll_n=0;max_hold=max_roll=0.;labels_checked=0
# Select deterministic spread plus recorded worst origins for independent A-roll.
select=set(s['ref'] for s in samples[::37]);worst=js(M/'results/worst-underprediction-cases.json');select.update(x['origin_ref'] for x in worst)
for r in preds:
 s=sm[r['ref']];j=bisect.bisect_left(sample_times,s['t']+r['h']);label=r['label']
 valid=j<len(samples) and samples[j]['t']<=s['t']+r['h']+2 and samples[j]['source_valid'] and samples[j]['epoch']==s['epoch'] and samples[j]['source_key']==s['source_key'] and s['source_valid']
 assert bool(label)==bool(valid)
 if label:assert label['ref']==samples[j]['ref'] and label['value']==samples[j]['current'];labels_checked+=1
 xs=[];bs=[]
 for b in branches:
  if b not in r['B_HOLD']:continue
  ob=s['states'].get(b,s['states']['AUGMENTED-KF']);ts=ob['Ts_C'] if b in s['states'] else s['filters'][b]
  x=[s['current'],ts,ob['E_C']];val=propagate(x,ob['conditional_inputs_rails_W_PWM'],r['h'])[0]
  max_hold=max(max_hold,abs(val-r['B_HOLD'][b]));hold_n+=1;xs.append(x);bs.append(b)
 if r['ref'] in select:
  pieces=interval(s['t'],s['t']+r['h'])
  assert (pieces is not None and bool(xs))==bool(r['A_roll'])
  if pieces is not None and xs:
   arr=np.array(xs)
   for h,n in pieces:arr=propagate(arr,n['u'],h)
   for b,vals in zip(bs,arr):max_roll=max(max_roll,abs(vals[0]-r['A_roll'][b]));roll_n+=1
# Recompute entire A-long sequentially, not reading TJ after initialization.
x=np.array(js(M/'results/A-long-summary.json')['frozen_state_C']);t=along[0]['t'];max_long=0.
for r in along:
 if r['t']>t:
  pieces=interval(t,r['t']);assert pieces is not None
  for h,n in pieces:x=propagate(x,n['u'],h)
 max_long=max(max_long,float(np.max(np.abs(x-[r['Tf_C'],r['Ts_C'],r['E_C']]))));t=r['t']
assert max(max_hold,max_roll,max_long)<1e-8
# Score all saved common tables without importing original metric functions.
def score(errors):
 z=np.array(errors);under=np.maximum(-z,0)
 if not len(z):return dict(n=0,MAE_C=None,RMSE_C=None,mean_error_C=None,P95_abs_error_C=None,P95_underprediction_C=None,max_underprediction_C=None,fraction_underprediction_gt_2C=None)
 return dict(n=len(z),MAE_C=float(abs(z).mean()),RMSE_C=float(np.sqrt((z*z).mean())),mean_error_C=float(z.mean()),P95_abs_error_C=float(np.percentile(abs(z),95)),P95_underprediction_C=float(np.percentile(under,95)),max_underprediction_C=float(under.max()),fraction_underprediction_gt_2C=float((under>2).mean()))
count=0
for tab in js(M/'results/metrics-common.json'):
 rr=[r for r in preds if r['h']==tab['h'] and r['label'] and 'B1' in r['baselines'] and all(b in r[tab['kind']] for b in tab['branches']) and (tab['phase']=='all' or r['phase']==tab['phase']) and (tab['qualification']!='KF_tracking' or r['observer_phase']=='tracking')]
 assert len(rr)==tab['n'];digest=hashlib.sha256('\n'.join(f"{r['ref']}|{r['h']}|{r['label']['ref']}" for r in rr).encode()).hexdigest();assert digest==tab['cohort_SHA256']
 for group,names in [(tab['kind'],tab['branches']),('baselines',['B0','B1'])]:
  for name in names:
   got=score([r[group][name]-r['label']['value'] for r in rr]);given=tab['baselines' if group=='baselines' else 'errors'][name]
   for k,v in got.items():assert (v is None and given[k] is None) or (v is not None and abs(v-given[k])<1e-10),(k,v,given[k])
 count+=1
rs=[r for r in preds if r['h']==45 and r['label'] and 'B1' in r['baselines'] and all(b in r['B_HOLD'] for b in branches)]
same=[r for r in rs if r['phase']==r['label']['phase']];cross=[r for r in rs if r['phase']!=r['label']['phase']]
all_abs=sum(abs(r['B_HOLD']['AUGMENTED-KF']-r['label']['value']) for r in rs);cross_abs=sum(abs(r['B_HOLD']['AUGMENTED-KF']-r['label']['value']) for r in cross)
phasekind=lambda r:r.split('-',1)[1] if '-' in r else r
cross_to_work=[r for r in cross if phasekind(r['label']['phase'])=='work']
cross_from_work=[r for r in cross if phasekind(r['phase'])=='work']
onset_error_origins=[]
requests=jl(R/'original/evidence/field/remote-result/run/requests.jsonl')
import datetime as dt
for r in cross_to_work:
 stage=int(r['label']['phase'].split('-')[0]); first=min(q['submitted_at_utc'] for q in requests if q['stage_index']==stage)
 onset_error_origins.append((dt.datetime.fromisoformat(first)-dt.datetime.fromisoformat(r['utc'])).total_seconds())
lat=[r['label']['offset_s'] for r in rs]
rows=[]
for label,rr in [('all',rs),('same',same),('cross',cross),('cross_to_work',cross_to_work),('cross_from_work',cross_from_work)]:
 rows.append(dict(stratum=label,n=len(rr),KF_B=score([r['B_HOLD']['AUGMENTED-KF']-r['label']['value'] for r in rr]),KF_A=score([r['A_roll']['AUGMENTED-KF']-r['label']['value'] for r in rr]),B0=score([r['baselines']['B0']-r['label']['value'] for r in rr])))
res=dict(independent_method='2x2 analytic matrix exponential; independent target lookup/scoring; no optimizer or original evaluation imports',B_values_checked=hold_n,B_max_abs_difference_C=max_hold,A_roll_values_checked=roll_n,A_roll_max_abs_difference_C=max_roll,A_long_points=len(along),A_long_max_state_abs_difference_C=max_long,label_decisions=len(preds),valid_labels=labels_checked,common_tables_checked=count,forecast45_strata=rows,cross_fraction=len(cross)/len(rs),cross_fraction_of_total_absolute_error=cross_abs/all_abs,onset_cross_origins_before_first_submit_s=dict(n=len(onset_error_origins),min=min(onset_error_origins),max=max(onset_error_origins),all_before=all(x>0 for x in onset_error_origins)),label45_offset_s=dict(min=min(lat),median=st.median(lat),max=max(lat)))
(R/'results/numeric-audit.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False,indent=2))
