"""Local saved-event Pipeline probe. No sockets, collector run or device access.
Set BLAS environment BEFORE starting this process. Does not modify runtime files.
"""
import argparse,collections,hashlib,json,os,platform,shutil,sys,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--seconds',type=float,default=12);ap.add_argument('--paced',action='store_true');args=ap.parse_args()
r=args.root;out=args.output;out.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(r/'delivered_runtime'))
# Imports deliberately occur only after environment selection by the parent.
import psutil,numpy as np,scipy
from scipy.linalg import expm
from threadpoolctl import threadpool_info
from tto_field.runtime import Pipeline
from tto_field.support import Clock,Evidence
from tto.engine import engine_for
f=r/'field_original/evidence/remote-result/run';native=next((f/'native').glob('run-*'));manifest=json.loads((native/'manifest.json').read_text());cfg=manifest['config']
raw=[json.loads(s) for s in (native/'observations-0001.jsonl').read_text().splitlines()];saved=[json.loads(s)['state'] for s in (f/'states.jsonl').read_text().splitlines()]
t0=raw[0]['mono_s'];chosen=[(i,x) for i,x in enumerate(raw) if args.seconds<=0 or x['mono_s']-t0<=args.seconds]
newnative=out/'native'/native.name;newnative.mkdir(parents=True);shutil.copyfile(native/'manifest.json',newnative/'manifest.json')
binding=json.loads((f/'launch.json').read_text())['binding'];clock=Clock();ev=Evidence(out)
p=Pipeline(out,cfg,binding,'diagnose',clock,ev);engine=engine_for(cfg,record_schema=manifest['record_schema'])
proc=psutil.Process();threads0={x.id:x.user_time+x.system_time for x in proc.threads()};ct0=proc.cpu_times();w0=time.perf_counter();calls=[];maxdiff=0;phaseerr=[];outputs=[]
for i,x in chosen:
 if args.paced:
  sleep=(x['mono_s']-t0)-(time.perf_counter()-w0)
  if sleep>0:time.sleep(sleep)
 t=time.perf_counter();processed=engine.process(x);p.on_record(x,processed,engine);calls.append(time.perf_counter()-t)
 current=p.get()['state'];old=saved[i]
 if current['observer']['phase']!=old['observer']['phase']:phaseerr.append(i)
 for key in ['Tf_C','Ts_C','E_C']:
  a=current['observer'][key];b=old['observer'][key]
  if a is not None and b is not None:maxdiff=max(maxdiff,abs(a-b))
  elif a is not b:raise AssertionError((i,key,a,b))
 a=current['observer']['uncertainty']['covariance_C2'];b=old['observer']['uncertainty']['covariance_C2']
 if a is not None and b is not None:maxdiff=max(maxdiff,float(np.max(np.abs(np.array(a)-np.array(b)))))
 outputs.append(current)
if args.paced:
 wait=args.seconds-(time.perf_counter()-w0)
 if wait>0:time.sleep(wait)
ct1=proc.cpu_times();wall=time.perf_counter()-w0
cpu=ct1.user+ct1.system-ct0.user-ct0.system
thread_delta=[{'tid':x.id,'cpu_s':x.user_time+x.system_time-threads0.get(x.id,0)} for x in proc.threads()]
ev.close()
result={'scope':'independent local saved-event replay, no network/device/sidecar; not N305 performance',
 'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,
 'env':{k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS']},
 'loaded_pools':threadpool_info(),'events':len(chosen),'paced':args.paced,'scheduled_seconds':args.seconds,
 'wall_s':wall,'process_cpu_s':cpu,'process_cpu_pct':100*cpu/wall,'main_thread_id':proc.pid,
 'thread_cpu_deltas':sorted(thread_delta,key=lambda x:-x['cpu_s']),
 'max_abs_state_cov_diff_to_saved':maxdiff,'phase_mismatches':phaseerr,
 'callback_ms_p95':float(np.percentile(calls,95)*1000),'callback_ms_max':max(calls)*1000,
 'phase_counts':dict(collections.Counter(x['observer']['phase'] for x in outputs)),
 'frozen_observer_sha256':hashlib.sha256((r/'delivered_runtime/tto_field/research/observer.py').read_bytes()).hexdigest()}
(out/'probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['events','wall_s','process_cpu_s','process_cpu_pct','max_abs_state_cov_diff_to_saved','phase_mismatches','loaded_pools']}))
