"""Offline read-only source summary for #10; no networking or second collector."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'sources/candidate-wheel'))
from tto.engine import engine_for
run=next((R/'sources/Y-raw').rglob('manifest.json')).parent;m=json.loads((run/'manifest.json').read_text());engine=engine_for(m['config'],record_schema=2);lastfan=None;lasttemp=None;lastsource=None;count=0
with (R/'analysis/source-health-Y.jsonl').open('w') as f:
 for line in (run/'observations-0001.jsonl').read_text().splitlines():
  r=json.loads(line);t=r['mono_s'];o=engine.process(r);q=o['quality'];kind=r['kind']
  if q and q['accepted']:
   lastsource={'key':list(q['key']),'ref':r['ref'],'mono_s':t,'values':q['values'],'valid_until_mono_s':t+(r['payload']['telemetry_meta']['freshness_timeout_ms']-q['age_lower_bound_ms'])/1000}
  if kind=='fan' and not r.get('error_class') and (r.get('payload') or {}).get('data',{}).get('fans'):lastfan=r
  if kind=='temp' and not r.get('error_class'):lasttemp=r
  fan=(lastfan['payload']['data']['fans'][0] if lastfan else {});fanage=t-lastfan['mono_s'] if lastfan else None;fresh=bool(lastfan and fanage<=2.5 and engine.fan is not None);tempfresh=bool(lasttemp and t-lasttemp['mono_s']<=7.5 and engine.temp is not None)
  sourcefresh=bool(lastsource and t<lastsource['valid_until_mono_s'] and engine.q.key is not None and list(engine.q.key)==lastsource['key'] and not engine.q.blocked and not engine.q.quarantined)
  node={'identity':{'run_id':m['observer_run_id'],'config_sha256':m['config_sha256'],'model_identity':None,'collector_source_sha256':m['source_identity']['sha256'],'firmware':m.get('firmware_identity'),'spec':'COMM-SOURCE-HEALTH-R2-v1','generated_from':'offline saved stream','observed_through_ref':r['ref'],'observed_through_utc':r['received_at_utc'],'observed_through_mono_s':t},'measurement':{'TJ_and_rails':{'raw_valid':sourcefresh,'source':lastsource},'PWM':{'raw_valid':bool(fresh and fan.get('duty_valid')),'value':fan.get('duty') if fan.get('duty_valid') else None,'ref':lastfan['ref'] if lastfan else None,'received_at_utc':lastfan['received_at_utc'] if lastfan else None,'received_mono_s':lastfan['mono_s'] if lastfan else None,'age_s':fanage,'expires_mono_s':lastfan['mono_s']+2.5 if lastfan else None,'meaning':'last successful observed PWM; value preserved for trace, raw_valid governs use'}},'safety':{'fresh':fresh and tempfresh,'guard':fan.get('guard_active') if fresh else None,'fault':fan.get('fault') if fresh else None,'mode':fan.get('mode') if fresh else None,'binding':lasttemp['payload']['data'].get('bound_variable') if tempfresh else None,'temp_stale':fan.get('temp_stale') if fresh else None},'observer':{'state':'uninitialized','owner':'Issue8; no state/model estimate performed here'},'permission':{'mode':'offline_replay','formal_field_authorized':False},'communication':{'endpoint':kind if kind in ['fan','temp'] else None,'error_class':r.get('error_class'),'timeout_phase':'unknown_historical_no_trace' if r.get('error_class') else None}}
  f.write(json.dumps(node,ensure_ascii=False)+'\n');count+=1
print('source-health snapshots',count)
