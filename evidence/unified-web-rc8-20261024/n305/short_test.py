"""Authorized bounded readonly N305 validation, using only the installed package."""
import argparse,datetime,hashlib,json,shutil,subprocess,time,traceback,uuid
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
import psutil
args=argparse.ArgumentParser();args.add_argument('case',choices=['normal','failure']);CASE=args.parse_args().case
P=Path('/home/rm01/TTO-unified-rc8-20261024');V=P/'validation'/CASE;V.mkdir(parents=True,mode=0o700)
SESSION=P/('session-'+CASE);PUB=P/('pub-'+CASE);PUB.mkdir(mode=0o700)
if CASE=='failure':(PUB/'predictions-final.next').mkdir() # Real filesystem fault; installed code untouched.
DURATION=180 if CASE=='normal' else 45
BACKEND=P/'backend/bin/tto-observe';WEB=P/'web/tto-web';OPEN=build_opener(ProxyHandler({})).open
logs=[];webs=[];observer=None;web=None;subscription=None;snapshots=[];resources=[]
result=dict(case=CASE,prefix=str(P),duration_s=DURATION,scope='N305 actual installed readonly observe + Web; no inference or control writes')
def save():
 (V/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (V/'samples.json').write_text(json.dumps(snapshots,indent=2)+'\n')
 (V/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
def api(path):
 with OPEN('http://127.0.0.1:59009/api/v1/'+path,timeout=2) as r:return json.load(r)
def views():return {str(h):api('predictions?horizon_s='+str(h)) for h in (15,45,90)}
def records(v):return {r['prediction_id']:r for value in v.values() for r in value['records']}
def rows(stream):return [json.loads(line) for f in sorted(SESSION.glob(stream+'*.jsonl')) for line in f.read_text().splitlines()]
def sizes():return [sum(f.stat().st_size for f in SESSION.glob(n+'*.jsonl')) for n in ('states','predictions')]
def launch_web():
 log=(V/('web-'+str(len(webs))+'.log')).open('w');logs.append(log)
 child=subprocess.Popen([str(WEB),'serve','--config',str(V/'web.json')],stdout=log,stderr=subprocess.STDOUT);webs.append(child);return child
try:
 old=Path('/home/rm01/TTO-autoworkday-temp-continue-20261022/config')
 shutil.copy2(old/'observer-config.json',V/'observer-config.json')
 reg=json.loads((old/'registration.json').read_text());reg['session_id']=str(uuid.uuid4());(V/'registration.json').write_text(json.dumps(reg))
 wc=json.loads((P/'web/web.json').read_text());wc['source']['active_descriptor']=str(PUB/'active.json');(V/'web.json').write_text(json.dumps(wc))
 preview=subprocess.check_output([str(BACKEND),'preview','--config',str(V/'observer-config.json'),'--registration',str(V/'registration.json'),'--duration',str(DURATION)],text=True)
 (V/'preview.json').write_text(preview);grant=json.loads(preview)['grant_template'];now=datetime.datetime.now(datetime.timezone.utc)
 grant.update(explicit_user_start=True,evidence='User 2026-10-24 authorized PR16 root-cause fixes, new N305 package in independent prefix, normal and failure short tests; preserve old records; no merge.',not_before_utc=(now-datetime.timedelta(seconds=30)).isoformat(),expires_at_utc=(now+datetime.timedelta(minutes=10)).isoformat(),session_max_bytes=256*1024**2)
 (V/'grant.json').write_text(json.dumps(grant))
 for f in V.glob('*.json'):f.chmod(0o600)
 log=(V/'observe.log').open('w');logs.append(log)
 observer=subprocess.Popen([str(BACKEND),'observe','--config',str(V/'observer-config.json'),'--registration',str(V/'registration.json'),'--duration',str(DURATION),'--grant',str(V/'grant.json'),'--output',str(SESSION),'--allow-network','--publication-descriptor',str(PUB/'active.json')],stdout=log,stderr=subprocess.STDOUT)
 web=launch_web();bp=psutil.Process(observer.pid);bp.cpu_percent(None);wp=psutil.Process(web.pid);wp.cpu_percent(None)
 begin=time.monotonic();restarted=False;restart_at=None;before={};before_epoch=None
 while observer.poll() is None:
  elapsed=time.monotonic()-begin
  if elapsed>DURATION+25:raise TimeoutError('observe did not exit')
  if web and web.poll() is not None:raise RuntimeError('Web exited '+str(web.returncode))
  sample=dict(elapsed_s=elapsed,backend_cpu=bp.cpu_percent(None),backend_rss=bp.memory_info().rss)
  if web:
   sample.update(web_cpu=wp.cpu_percent(None),web_rss=wp.memory_info().rss)
   try:s=api('snapshot')
   except OSError:
    if elapsed>10:raise
   else:
    snapshots.append(dict(elapsed_s=elapsed,model=s['model']['phase'],forecast=s['forecast']['status'],epoch=s['source_epoch'],ids=s['forecast']['latest_prediction_ids']))
    if subscription is None:
     subscription=OPEN('http://127.0.0.1:59009/api/v1/stream',timeout=2)
     while subscription.readline().strip():pass
    if before and restarted and 'restored_same_ids' not in result:
     current=records(views())
     if set(before).issubset(current):
      fields=('value_C','origin_elapsed_ms','issued_elapsed_ms','target_elapsed_ms','ledger_run_id','model_id','spec_id')
      assert all(all(before[i][k]==current[i][k] for k in fields) for i in before)
      assert s['service_epoch']!=before_epoch;result['restored_same_ids']=len(before)
  resources.append(sample)
  if CASE=='normal' and elapsed>=45 and not restarted and web:
   before=records(views());before_epoch=api('snapshot')['service_epoch'];result['pre_restart_records']=len(before);old_sizes=sizes()
   t=time.monotonic();web.terminate();assert web.wait(timeout=10)==0;result['web_stop_with_sse_s']=time.monotonic()-t
   subscription.close();subscription=None;web=None;restart_at=time.monotonic()+10
  if web is None and restart_at and time.monotonic()>=restart_at:
   new_sizes=sizes();assert all(a>b for a,b in zip(new_sizes,old_sizes)) and observer.poll() is None
   result['recording_grew_without_web']=dict(before_bytes=old_sizes,after_bytes=new_sizes)
   web=launch_web();wp=psutil.Process(web.pid);wp.cpu_percent(None);restarted=True;restart_at=None
  if int(elapsed)%15==0:print(json.dumps(dict(case=CASE,elapsed_s=round(elapsed,1),observer_alive=True)),flush=True);save()
  time.sleep(1)
 result['observer_returncode']=observer.returncode;assert observer.returncode==0
 for _ in range(60):
  s=api('snapshot');v=views();meta=json.loads((PUB/'active.json').read_text())
  if (CASE=='normal' and s['publication_status']=='ended' and all(x['records_complete'] for x in v.values())) or (CASE=='failure' and s['publication_status']=='failed'):break
  time.sleep(.1)
 else:raise AssertionError('terminal lifecycle did not synchronize')
 if CASE=='normal':
  actual=records(v);identity=s['prediction_history_identity'];assert identity['source_epoch']<s['source_epoch']
  issued={r['prediction_id']:r for r in rows('predictions') if r['method']=='G2-HOLD' and r['origin_state_status'] in ('tracking','degraded') and r['source_epoch']==identity['source_epoch']}
  scores={r['prediction_id']:r for r in rows('scores') if r['method']=='G2-HOLD'}
  assert actual and set(actual)==set(issued),(len(actual),len(issued))
  for i,p in issued.items():
   r=actual[i];assert r['value_C']==p['value_C'] and r['ledger_run_id']==p['run_id'] and r['issued_at_utc']==p['issued_at']['utc']
   assert r['model_id']==p['model_sha256'] and r['spec_id']==p['spec_sha256'] and r['source_epoch']==p['source_epoch']
   score=scores[i]
   if score['status']=='scored':assert r['status']=='matched' and r['observed_C']==score['label_value_C'] and r['error_C']==score['error_C']
   else:assert r['reason_code']==score['reason']
  result.update(backend_web_records_equal=len(actual),backend_web_scores_equal=len(actual),live_source_epoch=s['source_epoch'],history_identity=identity,matched_by_horizon={h:x['summary']['matched_count'] for h,x in v.items()})
 else:
  assert meta['publication_failed'] and not meta['ended'] and meta['prediction_final'] is None
  assert not (PUB/'predictions-final.json').exists() and (PUB/'predictions-final.next').is_dir()
  assert all(not x['records_complete'] and x['sync_status']=='unavailable' for x in v.values())
  assert rows('predictions') and rows('scores');result['failed_descriptor']=meta
 assert not s['forecast']['latest_prediction_ids']
 # Cold restart after observe exit must restore the same terminal result.
 if subscription:subscription.close();subscription=None
 web.terminate();assert web.wait(timeout=10)==0
 web=launch_web()
 for _ in range(60):
  try:cold=api('snapshot');cv=views()
  except OSError:time.sleep(.1);continue
  if cold['publication_status']==s['publication_status'] and (CASE=='failure' or all(x['records_complete'] for x in cv.values())):break
  time.sleep(.1)
 else:raise AssertionError('cold terminal restart did not restore')
 if CASE=='normal':
  assert records(cv)==records(v) and all(cv[h]['summary']==v[h]['summary'] for h in cv)
  assert cold['prediction_history_identity']==s['prediction_history_identity']
 else:assert all(not x['records_complete'] for x in cv.values())
 result['cold_terminal_restart_equal']=True
 (V/'api-terminal.json').write_text(json.dumps(dict(before_restart=dict(snapshot=s,views=v),after_restart=dict(snapshot=cold,views=cv)),indent=2)+'\n')
 summary=json.loads((SESSION/'summary.json').read_text());result['observe_summary']=summary
 index=json.loads((SESSION/'files.json').read_text())
 for name,meta in index.items():
  f=SESSION/name;assert f.stat().st_size==meta['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256'],name
 result['session_index_verified_files']=len(index)
 result['resources']={key:dict(mean=sum(values)/len(values),peak=max(values)) for key in ('backend_cpu','backend_rss','web_cpu','web_rss') if (values:=[r[key] for r in resources if key in r])}
 result['passed']=True;save();(V/'browser-ready').write_text(CASE);print('BROWSER_READY '+CASE,flush=True)
 for _ in range(90):
  if (V/'browser-done').exists():break
  time.sleep(1)
except BaseException as exc:
 result.update(passed=False,error=type(exc).__name__,detail=str(exc));traceback.print_exc()
finally:
 if subscription:subscription.close()
 for child in webs:
  if child.poll() is None:child.terminate();child.wait(timeout=10)
 if observer and observer.poll() is None:subprocess.run([str(BACKEND),'stop','--session',str(SESSION)],timeout=15,check=False);observer.wait(timeout=15)
 for log in logs:log.close()
 result['owned_web_processes_stopped']=all(c.poll() is not None for c in webs)
 result['owned_observer_stopped']=observer is None or observer.poll() is not None
 save();print(json.dumps({k:v for k,v in result.items() if k!='observe_summary'},ensure_ascii=False),flush=True)
