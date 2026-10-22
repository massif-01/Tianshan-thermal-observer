from pathlib import Path
import json, hashlib, math, statistics, sys
import numpy as np
from scipy.integrate import solve_ivp
R=Path('/mnt/data/tto_cpu_prep_independent_review_20261020'); M=R/'original/model'; D=R/'deliverable/results'
def load(p): return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
# Semantic rerun comparison: exact nonnumeric structures; record real floating differences.
stats={'numeric_leaves':0,'max_abs':0.,'structural_errors':[],'files':[]}
def compare(a,b,path):
 if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
  stats['numeric_leaves']+=1; d=abs(a-b);stats['max_abs']=max(stats['max_abs'],d)
  if not math.isfinite(d) or d>1e-9:stats['structural_errors'].append([path,a,b])
 elif type(a)!=type(b):stats['structural_errors'].append([path,'type',str(a)[:120],str(b)[:120]])
 elif isinstance(a,dict):
  if set(a)!=set(b): stats['structural_errors'].append([path,'keys']);return
  for k in a:compare(a[k],b[k],path+'/'+k)
 elif isinstance(a,list):
  if len(a)!=len(b):stats['structural_errors'].append([path,'length']);return
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif a!=b:stats['structural_errors'].append([path,a,b])
for p in sorted((M/'runs/final-v2').glob('*')):
 if p.name=='environment-resource.json':continue
 q=R/'work/model_recomputed_2/results'/p.name
 compare(lines(p) if p.suffix=='.jsonl' else load(p), lines(q) if q.suffix=='.jsonl' else load(q),p.name)
 stats['files'].append({'name':p.name,'byte_identical':p.read_bytes()==q.read_bytes()})
(D/'scientific-rerun-semantic.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
assert not stats['structural_errors'],stats['structural_errors'][:5]
frames=lines(M/'runs/final-v2/feature-frames.jsonl'); outputs=lines(M/'runs/final-v2/activity-and-candidate-predictions.jsonl'); conf=load(M/'candidate.json')
raws={x['ref']:x for x in lines(M/'inputs/inputs/native/observations-0001.jsonl')}
# Source feature values independently checked, including per-frame (not fixed best core) maximum.
feature_count=0
for f in frames:
 r=raws[f['native_ref']]['payload'];u=[c['usage'] for c in r['cpu']['cores']]
 expected={'gpu_pct':r['gpu']['utilization_pct'],'gpu_W':r['power']['vdd_gpu']['current']/1000,'cpu_soc_mss_W':r['power']['vdd_cpu_soc_mss']['current']/1000,'cpu_mean_pct':sum(u)/len(u),'cpu_max_pct':max(u)}
 for k,v in expected.items():
  assert abs(f['features'][k]['value']-v)<1e-12
  feature_count+=1
# All historical accepted rows carry new rail sequence; verify before independent simple hysteresis.
detector={};nd=0
for variant,names in conf['variants'].items():
 state='UNKNOWN';low=None;until=None;prev_ids=None;epoch=None;seqout=[]
 for f,o in zip(frames,outputs):
  t=f['arrival_mono_s'];identity=(f['epoch'],f['arrival_clock_id'])
  if identity!=epoch or (until is not None and t>=until):state='UNKNOWN';low=None
  epoch=identity
  fs=[f['features'][n] for n in names]
  valid=not f['source_only'] and f['arrival_clock_id'] and all(x['valid'] and x['available_at_mono_s']<=t<x['valid_until_mono_s'] for x in fs)
  ids=tuple(x['update_id'] for x in fs)
  if not valid:state='UNKNOWN';low=None;until=None
  else:
   assert ids!=prev_ids,'independent old-data simplification requires at least one new feature'
   z=max((f['features'][n]['value']-conf['levels']['idle'][n])/(conf['levels']['active'][n]-conf['levels']['idle'][n]) for n in names)
   if z>=conf['on']:state='ACTIVE';low=None
   elif z<=conf['off']:
    if state=='UNKNOWN':state='IDLE'
    if state=='ACTIVE':
     if low is None:low=t
     if t-low>=conf['low_confirmation_s']:state='IDLE';low=None
   else:low=None
   until=min(x['valid_until_mono_s'] for x in fs)
  prev_ids=ids;seqout.append(state)
  assert state==o['variants'][variant]['activity']['state'],(variant,t,state)
  nd+=1
 detector[variant]=seqout
# Independent integration of actual G2 differential equations, not author augmented operator.
p=load(M/'inputs/vendor/src/tto_field/research/observer-spec.json')['dynamic'];solve_max=0.;n_solve=0
for i in range(0,len(frames),67):
 f=frames[i]; thermal=f['thermal']
 if not thermal['available']:continue
 u=thermal['conditional_inputs_rails_W_PWM'];E=thermal['E_C']
 for variant in conf['variants']:
  mode=outputs[i]['variants'][variant]['activity']['state']
  if mode=='UNKNOWN':continue
  def rhs(t,x):
   if mode=='ACTIVE':powers=[max(u[j],conf['levels']['active'][n]) for j,n in enumerate(['gpu_W','cpu_soc_mss_W'])]
   else:powers=[conf['levels']['idle'][n]+(u[j]-conf['levels']['idle'][n])*np.exp(-t/conf['relaxation_tau_s']) for j,n in enumerate(['gpu_W','cpu_soc_mss_W'])]
   return [-p['a']*(x[0]-x[1])+p['b_g']*powers[0]+p['b_c']*powers[1],p['c']*(x[0]-x[1])-(p['d0']+p['d1']*u[2])*(x[1]-E)]
  y=solve_ivp(rhs,[0,90],[thermal['current_TJ_C'],thermal['Ts_C']],method='DOP853',rtol=1e-12,atol=1e-12,t_eval=[15,45,90]).y[0]
  for h,v in zip([15,45,90],y):
   pred=outputs[i]['variants'][variant]['temperature_C'][str(h)]
   solve_max=max(solve_max,abs(v-pred));n_solve+=1
points=lines(M/'runs/final-v2/temperature-points.jsonl');tables=load(M/'runs/final-v2/temperature-common.json');table_cnt=0;metric_cnt=0;metric_max=0.
for tab in tables:
 rows=[r for r in points if r['h']==tab['h'] and r['old_common'] and (tab['posthoc_stratum']=='all' or r['posthoc_stratum']==tab['posthoc_stratum'])]
 assert len(rows)==tab['n']
 for method,m in tab['errors'].items():
  e=np.asarray([r['prediction'][method]-r['label']['value'] for r in rows]);un=np.maximum(-e,0)
  vals=dict(n=len(e),MAE_C=np.abs(e).mean(),P95_absolute_C=np.percentile(abs(e),95),P95_under_C=np.percentile(un,95),max_under_C=un.max(),bias_C=e.mean(),fraction_under_gt2C=np.mean(un>2)) if len(e) else m
  for k,v in vals.items():
   if v is not None:metric_max=max(metric_max,abs(v-m[k]));metric_cnt+=1
 table_cnt+=1
summary={'raw_features_checked':feature_count,'activity_states_rebuilt':nd,'max_vs_mean_different_states':sum(a!=b for a,b in zip(detector['INPUT-CORE'],detector['INPUT-MEAN'])),'independent_ODE_values_checked':n_solve,'independent_ODE_max_abs_C':float(solve_max),'temperature_tables_checked':table_cnt,'metric_values_checked':metric_cnt,'max_metric_difference':float(metric_max),'semantic_rerun_files':len(stats['files']),'max_semantic_rerun_abs':stats['max_abs'],'heat_theta_refits':0,'field_connections':0}
(D/'science-independent-check.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
