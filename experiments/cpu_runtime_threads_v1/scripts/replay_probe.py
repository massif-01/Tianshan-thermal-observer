"""Same saved native events through actual Pipeline; pacing is for local CPU only, not field performance."""
import argparse,collections,json,sys,os,time,shutil,hashlib,math,platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--package-root',type=Path);p.add_argument('--candidate-policy',action='store_true');p.add_argument('--seconds',type=float,default=12);p.add_argument('--paced',action='store_true');a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False)
if a.package_root:sys.path.insert(0,str(a.package_root))
policy=None
if a.candidate_policy:
 from tto_field.numeric_policy import initialize
 policy=initialize(out/'thread-policy.json')
import numpy as np,scipy.linalg,psutil
from threadpoolctl import threadpool_info
from tto_field.runtime import Pipeline
from tto_field.support import Clock,Evidence
from tto.engine import engine_for
native=next((a.run/'native').glob('run-*'));manifest=json.loads((native/'manifest.json').read_text());cfg=manifest['config'];raw=[json.loads(x) for x in (native/'observations-0001.jsonl').read_text().splitlines()];saved=[json.loads(x)['state'] for x in (a.run/'states.jsonl').read_text().splitlines()]
first=raw[0]['mono_s'];chosen=[(i,x) for i,x in enumerate(raw) if a.seconds<=0 or x['mono_s']-first<=a.seconds]
(out/'native'/native.name).mkdir(parents=True);shutil.copy2(native/'manifest.json',out/'native'/native.name/'manifest.json')
binding=json.loads((a.run/'launch.json').read_text())['binding'];clock=Clock();ev=Evidence(out);pipe=Pipeline(out,cfg,binding,'diagnose',clock,ev);engine=engine_for(cfg,record_schema=manifest['record_schema']);proc=psutil.Process();before={t.id:t.user_time+t.system_time for t in proc.threads()};ct=proc.cpu_times();w0=time.monotonic();calls=[];maxdiff=0.;checks=0
# Compare every nested scientific/semantic field, not just Tf or one summary score.
ignore=set()
def equal(x,y,path='state'):
 global maxdiff,checks
 if isinstance(x,dict) and isinstance(y,dict):
  assert set(x)==set(y),(path,set(x)^set(y))
  for k in x:equal(x[k],y[k],path+'.'+k)
 elif isinstance(x,list) and isinstance(y,list):
  assert len(x)==len(y),path
  for i,(xx,yy) in enumerate(zip(x,y)):equal(xx,yy,path+f'[{i}]')
 elif type(x) in (int,float) and type(y) in (int,float):
  d=abs(x-y);maxdiff=max(maxdiff,d);assert d<=1e-8,(path,x,y);checks+=1
 else:assert x==y,(path,x,y)
for i,x in chosen:
 if a.paced:
  delay=x['mono_s']-first-(time.monotonic()-w0)
  if delay>0:time.sleep(delay)
 t=time.monotonic();processed=engine.process(x);pipe.on_record(x,processed,engine);calls.append(time.monotonic()-t);equal(pipe.get()['state'],saved[i])
if a.paced:
 delay=a.seconds-(time.monotonic()-w0)
 if delay>0:time.sleep(delay)
wall=time.monotonic()-w0;ct1=proc.cpu_times();cpu=ct1.user+ct1.system-ct.user-ct.system;deltas=[dict(tid=t.id,cpu_s=t.user_time+t.system_time-before.get(t.id,0)) for t in proc.threads()];ev.close()
result=dict(scope='LOCAL saved events, no network/sidecar/devices; NOT N305',events=len(chosen),numeric_fields_checked=checks,max_abs_semantic_numeric_difference=maxdiff,all_semantic_fields_equal=True,phase_validity_revocation_cold_start_included=True,
 process_cpu_s=cpu,wall_s=wall,cpu_single_core_percent=100*cpu/wall,threads=sorted(deltas,key=lambda x:-x['cpu_s']),rss_bytes=proc.memory_info().rss,
 callback_p95_s=sorted(calls)[int(.95*(len(calls)-1))],callback_max_s=max(calls),thread_pools=threadpool_info(),python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,candidate_policy=a.candidate_policy,
 candidate_version=__import__('tto_field').__version__,observer_sha256=hashlib.sha256(Path(__import__('tto_field.research.observer',fromlist=['__file__']).__file__).read_bytes()).hexdigest(),paced=a.paced)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
