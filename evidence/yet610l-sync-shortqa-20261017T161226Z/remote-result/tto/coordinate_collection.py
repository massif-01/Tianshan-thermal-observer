"""Experiment-local collector coordinator; never calls inference or writes controls."""
import argparse,asyncio,datetime,hashlib,json,signal,socket,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native_health import TrialHealth
UTC=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
async def execute(root):
 import tto
 from tto.config import load_config,require_live
 from tto.collector import collect
 authorization=json.loads((root/'authorization.json').read_text())
 if authorization.get('explicit_start')!='可以开始本轮' or not authorization.get('probe_fixed') or not authorization.get('instrument_recording'):raise ValueError('Explicit user start and instrument/probe confirmation required')
 if (root/'collector-state.json').exists():raise ValueError('No automatic restart or rerun')
 c=load_config(root/'configuration/collection-config.json',environ={});require_live(c,2400)
 if tto.__version__!='0.2.4':raise ValueError('Unexpected TTO runtime')
 clock_host=socket.gethostname();health=TrialHealth();stop=asyncio.Event();start=time.monotonic();deadline=start+2400
 loop=asyncio.get_running_loop()
 for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
 def observe(record,out,engine):health.observe(record,out,engine)
 task=asyncio.create_task(collect(c,2395,data_root=root/'collection',episode=root.name,run_type='collect',stop_event=stop,on_record=observe))
 state={'status':'running','session_id':root.name,'started_coordinator_utc':UTC(),'clock_host':clock_host,'deadline_mono_s':deadline,'tto_version':tto.__version__,'operator_override':False}
 write(root/'collector-state.json',state);binding_written=False;reason='hard_deadline'
 try:
  while not task.done() and time.monotonic()<deadline-5 and not stop.is_set():
   now=time.monotonic();snap=health.snapshot(now)
   manifests=list((root/'collection').glob('run-*/manifest.json'))
   if len(manifests)>1:raise RuntimeError('Multiple collection runs; refuse ambiguous binding')
   if manifests:
    manifest=json.loads(manifests[0].read_text());run=manifest['observer_run_id']
    state.update(run_id=run,run_path=str(manifests[0].parent),collection_started_at_utc=manifest['started_at_utc'])
    valid_until=snap['latest']['valid_until'] if snap['latest'] else now
    write(root/'native-admission.json',dict(snap,run_id=run,clock_host=clock_host,collection_state='running',valid_until_mono_s=valid_until,operator_override=False))
    if not binding_written:
     actual_start=datetime.datetime.fromisoformat(manifest['started_at_utc'])
     end=min(actual_start+datetime.timedelta(seconds=2400),datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=max(0,deadline-now)))
     write(root/'workload-binding.json',{'authorization':'可以开始本轮','operator_override':False,'run_id':run,'session_id':root.name,'output_directory':str(root/'workload-output'),'collection_started_at_utc':manifest['started_at_utc'],'deadline_utc':end.isoformat(),'clock_host':clock_host,'native_admission_file':str(root/'native-admission.json'),'endpoint':'http://10.10.99.98:58000/v1/chat/completions'})
     binding_written=True
    write(root/'collector-state.json',state)
   if snap['abnormal']:reason='native_abnormal_condition';break
   status_path=root/'workload-output/status.json'
   if status_path.exists():
    s=json.loads(status_path.read_text())
    if s['state'] in ('completed','stopped'):reason='workload_'+s['state'];break
   await asyncio.sleep(.5)
  if stop.is_set():reason='operator_stop'
  elif task.done():reason='collector_finished'
 finally:
  stop.set()
  if binding_written:
   write(root/'native-admission.json',{'run_id':state['run_id'],'clock_host':clock_host,'collection_state':'stopping','current_ready':False,'abnormal':health.snapshot(time.monotonic())['abnormal'],'valid_until_mono_s':time.monotonic(),'operator_override':False})
  try:
   runpath,summary=await asyncio.wait_for(asyncio.shield(task),max(.01,deadline-time.monotonic()))
   state.update(run_path=str(runpath),collector_summary=summary)
  except Exception as e:state['cleanup_error']=repr(e)
  state.update(status='stopped',reason=reason,ended_coordinator_utc=UTC(),elapsed_s=time.monotonic()-start)
  write(root/'collector-state.json',state);write(root/'final-native-health.json',health.snapshot(time.monotonic()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--session',type=Path,required=True);a=p.parse_args()
 if a.execute:asyncio.run(execute(a.session.resolve()))
 else:print('Prepared only; no collection or inference started.')
