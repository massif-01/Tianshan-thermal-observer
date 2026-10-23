"""Offline diagnostic-cache probe. No network, devices, fitting, or source modifications.
Run with the candidate interpreter, or pass --package-root with its installed/source root.
--quality-cap is a REVIEW-ONLY counterfactual, never a production patch.
"""
import argparse,copy,gc,hashlib,json,sys,time
from collections import deque
from datetime import datetime,timedelta,timezone
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--package-root',type=Path);p.add_argument('--native-run',type=Path,required=True)
p.add_argument('--count',type=int,default=86400);p.add_argument('--quality-cap',type=int,default=0)
p.add_argument('--output',type=Path,required=True);p.add_argument('--observe-retention',action='store_true');a=p.parse_args()
if a.package_root:sys.path.insert(0,str(a.package_root.resolve()))
if not 1<=a.count<=86400 or a.quality_cap<0:raise SystemExit('bounded probe: count1..86400; nonnegative cap')
if a.output.exists():raise SystemExit('fresh output required')
from tto_field.numeric_policy import initialize
initialize()
from tto_field.projection import SavedStream
from tto.engine import engine_for
import tto_field,psutil
package=Path(tto_field.__file__).parent
spec=json.loads((package/'research/observer-spec.json').read_text())
m=json.loads((a.native_run/'manifest.json').read_text())
raw=None
for path in sorted(a.native_run.glob('observations-*.jsonl')):
 for line in path.open():
  r=json.loads(line)
  if r['kind']=='orin':raw=r;break
 if raw is not None:break
if raw is None:raise SystemExit('no source observation fixture')
engine=engine_for(m['config'],record_schema=2);projection=SavedStream(m,spec,engine,retain_quality_history=False) if a.observe_retention else SavedStream(m,spec,engine)
if a.quality_cap:projection.quality=deque(maxlen=a.quality_cap)
proc=psutil.Process();gc.collect();base=proc.memory_info().rss;samples=[];start=time.monotonic();epoch=datetime(2026,10,21,tzinfo=timezone.utc)
accepted=0;digest=hashlib.sha256()
for i in range(a.count):
 r=copy.deepcopy(raw);stamp=(epoch+timedelta(seconds=i)).isoformat()
 r.update(mono_s=raw['mono_s']+i,ref=f'{m["observer_run_id"]}/observation:{i+1}',received_at_utc=stamp)
 r['payload']['timestamp']=stamp
 r['payload']['telemetry_meta'].update(sample_seq=i+1,received_at=stamp,sample_age_ms=0.,fresh=True)
 r['payload']['gpu'].update(sampled_at_utc=stamp,age_at_telemetry_receive_ms=0.)
 out=engine.process(r);frame=projection.feed(r,out)
 digest.update(json.dumps(frame,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
 accepted+=bool(out['quality'] and out['quality'].get('accepted'))
 if i==0 or (i+1)%3600==0 or i+1==a.count:
  rss=proc.memory_info().rss
  samples.append(dict(rows=i+1,simulated_1Hz_hours=(i+1)/3600.,cache_items=len(projection.quality),accepted=accepted,rss_MiB=rss/2**20,delta_rss_MiB=(rss-base)/2**20))
import importlib.metadata,os,platform
result=dict(pid=os.getpid(),executable=sys.executable,python=platform.python_version(),platform=platform.platform(),dependencies={n:importlib.metadata.version(n) for n in ['numpy','scipy','psutil','python-socketio','aiohttp','threadpoolctl']},observe_retention_disabled=a.observe_retention,quality_seen=getattr(projection,'quality_seen',None),scope='accelerated offline synthetic-time replay of unchanged engine and projection; not elapsed field hours',candidate_version=tto_field.__version__,source_projection_sha256=hashlib.sha256((package/'projection.py').read_bytes()).hexdigest(),rows=a.count,accepted=accepted,wall_seconds=time.monotonic()-start,quality_cap_review_only=a.quality_cap or None,frame_sequence_sha256=digest.hexdigest(),baseline_RSS_MiB=base/2**20,samples=samples,source_changed=False,devices=0,fits=0)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
