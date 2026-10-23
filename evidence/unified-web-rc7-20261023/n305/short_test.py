"""One bounded, readonly N305 session; no inference, fan writes, or service changes."""
import json,time,subprocess,uuid,datetime,shutil,os,hashlib,traceback
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
import psutil
P=Path('/home/rm01/TTO-unified-rc7-20261024');V=P/'validation';V.mkdir(mode=0o700)
DURATION=180
PYTHON=P/'backend/bin/python';BACKEND=P/'backend/bin/tto-observe';WEB=P/'web/tto-web'
OPEN=build_opener(ProxyHandler({})).open

def api(path):
 with OPEN('http://127.0.0.1:59009/api/v1/'+path,timeout=2) as response:return json.load(response)
def rows(stream):
 return [json.loads(line) for f in sorted((P/'session').glob(stream+'*.jsonl')) for line in f.read_text().splitlines()]
def sizes(stream):return sum(f.stat().st_size for f in (P/'session').glob(stream+'*.jsonl'))
def records():return {r['prediction_id']:r for h in (15,45,90) for r in api('predictions?horizon_s='+str(h))['records']}
def launch_web():
 log=(V/('web-'+str(len(webs))+'.log')).open('w')
 child=subprocess.Popen([str(WEB),'serve','--config',str(P/'web/web.json')],stdout=log,stderr=subprocess.STDOUT)
 webs.append(child);logs.append(log);return child

logs=[];webs=[];observer=None;web=None;subscription=None
result={'scope':'N305 installed real readonly observe + Web, 180s; no inference or control writes','prefix':str(P),'duration_s':DURATION}
try:
 shutil.copy2('/home/rm01/TTO-autoworkday-temp-continue-20261022/config/observer-config.json',V/'observer-config.json')
 reg=json.loads(Path('/home/rm01/TTO-autoworkday-temp-continue-20261022/config/registration.json').read_text())
 reg['session_id']=str(uuid.uuid4());(V/'registration.json').write_text(json.dumps(reg,indent=2)+'\n')
 preview=subprocess.check_output([str(BACKEND),'preview','--config',str(V/'observer-config.json'),'--registration',str(V/'registration.json'),'--duration',str(DURATION)],text=True)
 (V/'preview.json').write_text(preview);grant=json.loads(preview)['grant_template'];now=datetime.datetime.now(datetime.timezone.utc)
 grant.update(explicit_user_start=True,evidence='User authorized new independent N305 install and short readonly test after preserving incomplete old closeout; 2026-10-24 instructed direct login and continuation.',not_before_utc=(now-datetime.timedelta(seconds=30)).isoformat(),expires_at_utc=(now+datetime.timedelta(minutes=10)).isoformat(),session_max_bytes=256*1024**2)
 (V/'grant.json').write_text(json.dumps(grant,indent=2)+'\n')
 for f in V.glob('*.json'):f.chmod(0o600)
 command=[str(BACKEND),'observe','--config',str(V/'observer-config.json'),'--registration',str(V/'registration.json'),'--duration',str(DURATION),'--grant',str(V/'grant.json'),'--output',str(P/'session'),'--allow-network','--publication-descriptor',str(P/'pub/active.json')]
 log=(V/'observe.log').open('w');logs.append(log);observer=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 web=launch_web();observed=psutil.Process(observer.pid);observed.cpu_percent(None);wp=psutil.Process(web.pid);wp.cpu_percent(None)
 started=time.monotonic();restarted=False;restart_at=None;before={};before_epoch=None;web_cpu=[];backend_cpu=[];backend_rss=[];web_rss=[];snapshots=[];ready=False
 while observer.poll() is None:
  elapsed=time.monotonic()-started
  if elapsed>DURATION+25:raise TimeoutError('bounded observe failed to exit')
  if web is not None and web.poll() is not None:raise RuntimeError('Web exited unexpectedly: '+str(web.returncode))
  backend_cpu.append(observed.cpu_percent(None));backend_rss.append(observed.memory_info().rss)
  if web is not None:
   web_cpu.append(wp.cpu_percent(None));web_rss.append(wp.memory_info().rss)
   try:snapshot=api('snapshot')
   except OSError:
    if elapsed>10 and not ready:raise
   else:
    ready=True;snapshots.append({'elapsed_s':elapsed,'model':snapshot['model']['phase'],'forecast':snapshot['forecast']['status'],'epoch':snapshot['source_epoch'],'ids':snapshot['forecast']['latest_prediction_ids'],'run_elapsed_ms':snapshot['run_elapsed_ms']})
    if subscription is None:
     subscription=OPEN('http://127.0.0.1:59009/api/v1/stream',timeout=2)
     while subscription.readline().strip():pass
    if before and restarted and 'restored_same_ids' not in result:
     current=records()
     if set(before).issubset(current):
      fields=('value_C','origin_elapsed_ms','issued_elapsed_ms','target_elapsed_ms','ledger_run_id','model_id','spec_id')
      assert all(all(before[i][k]==current[i][k] for k in fields) for i in before)
      assert snapshot['service_epoch']!=before_epoch
      result['restored_same_ids']=len(before);result['new_web_epoch']=snapshot['service_epoch']
  if elapsed>=45 and not restarted and web is not None:
   before=records();before_epoch=api('snapshot')['service_epoch'];result['pre_restart_records']=len(before)
   old_sizes=(sizes('states'),sizes('predictions'));begin=time.monotonic();web.terminate();assert web.wait(timeout=10)==0
   result['web_stop_with_sse_s']=time.monotonic()-begin;subscription.close();subscription=None;web=None;restart_at=time.monotonic()+10
  if web is None and restart_at is not None and time.monotonic()>=restart_at:
   new_sizes=(sizes('states'),sizes('predictions'));assert new_sizes[0]>old_sizes[0] and new_sizes[1]>old_sizes[1] and observer.poll() is None
   result['recording_grew_without_web']={'before_bytes':old_sizes,'after_bytes':new_sizes}
   web=launch_web();wp=psutil.Process(web.pid);wp.cpu_percent(None);restarted=True;restart_at=None
  if int(elapsed)%15==0:print(json.dumps({'elapsed_s':round(elapsed,1),'observer_alive':True,'web_alive':web is not None,'snapshots':len(snapshots)}),flush=True)
  time.sleep(1)
 result['observer_returncode']=observer.returncode;assert observer.returncode==0
 for _ in range(50):
  snapshot=api('snapshot');views={h:api('predictions?horizon_s='+str(h)) for h in (15,45,90)}
  if all(v['records_complete'] for v in views.values()) and snapshot['forecast']['status']!='available' and json.loads((P/'pub/active.json').read_text())['ended']:break
  time.sleep(.1)
 else:raise AssertionError('terminal scores did not synchronize')
 actual={r['prediction_id']:r for v in views.values() for r in v['records']}
 prediction={r['prediction_id']:r for r in rows('predictions') if r['method']=='G2-HOLD' and r['origin_state_status'] in ('tracking','degraded') and r['source_epoch']==snapshot['source_epoch']}
 scores={r['prediction_id']:r for r in rows('scores') if r['method']=='G2-HOLD'}
 assert actual and set(actual)==set(prediction),(len(actual),len(prediction))
 for i,p in prediction.items():
  r=actual[i];assert r['value_C']==p['value_C'] and r['ledger_run_id']==p['run_id'] and r['model_id']==p['model_sha256'] and r['spec_id']==p['spec_sha256']
  assert r['issued_at_utc']==p['issued_at']['utc']
  if i in scores:
   s=scores[i]
   if s['status']=='scored':assert r['status']=='matched' and r['observed_C']==s['label_value_C'] and r['error_C']==s['error_C']
   else:assert r['reason_code']==s['reason']
 result.update(backend_web_records_equal=len(actual),backend_web_scores_equal=sum(i in scores for i in actual),matched_by_horizon={h:v['summary']['matched_count'] for h,v in views.items()},page_summary_by_horizon={h:v['summary'] for h,v in views.items()},terminal_forecast=snapshot['forecast'],backend_cpu_single_core_mean=sum(backend_cpu)/len(backend_cpu),web_cpu_single_core_mean=sum(web_cpu)/len(web_cpu),backend_peak_rss_bytes=max(backend_rss),web_peak_rss_bytes=max(web_rss),model_phases=sorted({s['model'] for s in snapshots}),available_forecast_samples=sum(s['forecast']=='available' for s in snapshots))
 summary=json.loads((P/'session/summary.json').read_text());result['observe_summary']=summary
 index=json.loads((P/'session/files.json').read_text());mismatches=[]
 for name,meta in index.items():
  f=P/'session'/name;h=hashlib.sha256(f.read_bytes()).hexdigest()
  if f.stat().st_size!=meta['bytes'] or h!=meta['sha256']:mismatches.append(name)
 assert not mismatches;result['session_index_verified_files']=len(index)
 (V/'samples.json').write_text(json.dumps(snapshots,indent=2)+'\n');(V/'api-terminal.json').write_text(json.dumps({'snapshot':snapshot,'views':views},indent=2)+'\n')
 result['passed']=True
except BaseException as exc:
 result.update(passed=False,error=type(exc).__name__,detail=str(exc));traceback.print_exc()
finally:
 if subscription:subscription.close()
 for child in webs:
  if child.poll() is None:child.terminate();child.wait(timeout=10)
 if observer and observer.poll() is None:
  subprocess.run([str(BACKEND),'stop','--session',str(P/'session')],timeout=15,check=False)
 for log in logs:log.close()
 result['owned_web_processes_stopped']=all(c.poll() is not None for c in webs)
 result['owned_observer_stopped']=observer is None or observer.poll() is not None
 (V/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('observe_summary','page_summary_by_horizon')},ensure_ascii=False),flush=True)
