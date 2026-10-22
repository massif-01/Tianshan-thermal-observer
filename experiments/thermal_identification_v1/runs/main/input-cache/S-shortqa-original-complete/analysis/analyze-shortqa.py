from pathlib import Path
from datetime import datetime,timezone
import json,csv,statistics,math,bisect
P=Path(__file__).resolve().parent.parent;O=P/'analysis'
def ts(x):return datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
def summary(a):
 a=[x for x in a if isinstance(x,(float,int)) and math.isfinite(x)]
 return {'n':len(a),'mean':statistics.mean(a),'min':min(a),'max':max(a),'first':a[0],'last':a[-1]} if a else None
run=next(P.glob('run-*'));raw=[json.loads(l) for f in run.glob('observations-*.jsonl') for l in f.read_text().splitlines()]
accepted={r['ref']:r for r in map(json.loads,(run/'events.jsonl').read_text().splitlines()) if r.get('accepted')};rows=[];fans=[];anomalies=[];lastfan=None
for r in raw:
 t=ts(r['received_at_utc']);k=r['kind']
 if r.get('error_class'):anomalies.append(dict(type='http_timeout' if r['error_class']=='TimeoutError' else 'http_error',time=r['received_at_utc'],t=t,ref=r['ref'],channel=k,error=r['error_class']))
 if k=='fan':
  f=next((f for f in r.get('payload',{}).get('data',{}).get('fans',[]) if f['id']==0),None);lastfan=dict(f,t=t,mono=r['mono_s'],time=r['received_at_utc'],ref=r['ref']) if f else None
  if lastfan:
   fans.append(lastfan)
   if f.get('temp_stale'):anomalies.append(dict(type='device_temp_stale',time=r['received_at_utc'],t=t,ref=r['ref'],duty=f.get('duty')))
  continue
 if r['ref'] not in accepted:continue
 e=accepted[r['ref']];v=e['values'];f=lastfan if lastfan and 0<=r['mono_s']-lastfan['mono']<=2.5 and lastfan.get('duty_valid') else None
 d={'t':t,'utc':r['received_at_utc'],'ref':r['ref'],'tj':v['tj'],'gpu':e['gpu']['value'],'gpu_power':v.get('vdd_gpu'),'cpu_power':v.get('vdd_cpu_soc_mss'),'vin_power':v.get('vin_sys_5v0'),'temp_cpu':v.get('temp_cpu'),'temp_gpu':v.get('temp_gpu'),'temp_soc012':v.get('temp_soc012'),'temp_soc345':v.get('temp_soc345'),'cpu_usage_mean':statistics.mean(c['usage'] for c in r['payload']['cpu']['cores']),'duty':f.get('duty') if f else None,'gain':f.get('controller_gain') if f else None,'slope':f.get('slope_c_per_min') if f else None,'predicted':f.get('predicted_temperature') if f else None,'control_temp':f.get('control_temperature') if f else None,'stale':f.get('temp_stale') if f else None,'guard':f.get('guard_active') if f else None,'fault':f.get('fault') if f else None,'fan_mode':f.get('mode') if f else None,'fan_ref':f['ref'] if f else None,'fan_age_s':r['mono_s']-f['mono'] if f else None}
 rows.append(d)
rows.sort(key=lambda x:x['t']);fans.sort(key=lambda x:x['t'])
# Workload logs are normalized separately after observing actual schema.
requests=json.loads((P/'normalized-requests.json').read_text());phases=json.loads((P/'normalized-phases.json').read_text());times=[r['t'] for r in rows];ftimes=[r['t'] for r in fans]
def before(t):
 i=bisect.bisect_right(times,t)-1
 return rows[i] if i>=0 and 0<=t-times[i]<=2.5 else None
def after(t):
 i=bisect.bisect_left(times,t)
 return rows[i] if i<len(rows) and times[i]-t<=1.6 else None
def fan_before(t):
 i=bisect.bisect_right(ftimes,t)-1
 return fans[i] if i>=0 and 0<=t-ftimes[i]<=2.5 else None
out=[]
for i,q in enumerate(requests):
 a=ts(q['submit_utc']);b=ts(q['end_utc']) if q.get('end_utc') else None
 nextq=next((r for r in requests[i+1:] if r['stage']==q['stage']),None)
 window_end=ts(nextq['submit_utc']) if nextq else ts(q['window_end_utc'])
 sample=[r for r in rows if a<=r['t']<window_end];fs=[f for f in fans if a<=f['t']<window_end and f.get('duty_valid')]
 beforefan=fan_before(a);endfan=fan_before(b) if b else None
 peaks={k:max((r for r in sample if r[k] is not None),key=lambda r:r[k],default=None) for k in ['tj','duty','gain']}
 fanpeak=max(fs,key=lambda f:f['duty'],default=None)
 offsets={}
 for sec in [5,15,30,60]:
  t=b+sec if b else None;n=after(t) if t else None;interfering=[r['request_id'] for r in requests[i+1:] if t and ts(r['submit_utc'])<=t]
  offsets[str(sec)]={'sample':n,'next_task_influence':bool(interfering),'intervening_tasks':interfering,'status':'already_after_next_submission' if interfering else 'valid' if n else 'no_valid_sample'}
 out.append(dict(q,start_state=before(a),start_fan=beforefan,end_fan=endfan,window_end=window_end,peaks=peaks,fan_peak=fanpeak,fan_peak_relative_end_s=fanpeak['t']-b if fanpeak and b else None,pwm_increased_after_end=(any(f['t']>=b and f['duty']>endfan['duty'] for f in fs) if endfan and b else None),post_end_offsets=offsets,gain_values=sorted(set(f['controller_gain'] for f in fs if f.get('controller_gain') is not None)),anomalies=[x for x in anomalies if a<=x['t']<window_end]))
metrics=['tj','temp_cpu','temp_gpu','temp_soc012','temp_soc345','gpu','gpu_power','cpu_power','vin_power','duty','gain','slope','predicted']
phase_results=[]
for ph in phases:
 a=ts(ph['start_utc']);b=ts(ph['end_utc']);sample=[r for r in rows if a<=r['t']<b]
 high=0;observed=0
 for i,f in enumerate(fans[:-1]):
  end=min(fans[i+1]['t'],f['t']+2.5,b);start=max(f['t'],a);dt=max(0,end-start)
  if f.get('duty_valid'):observed+=dt;high+=dt if f['duty']>=80 else 0
 phase_results.append(dict(ph,metrics={k:summary([r[k] for r in sample]) for k in metrics},samples=len(sample),pwm_ge80_observed_s=high,fan_observed_hold_s=observed,anomalies=[x for x in anomalies if a<=x['t']<b]))
result={'method':'Accepted new TJ; GPU saved quality; successful fan as-of <=2.5sec. No zero fill or interpolation. UTC same N305 host; task end means protocol/client completion, not GPU kernel exact end. Peak window submission to next same-stage submission; last to group cooldown end. PWM >=80% duration uses successful API state hold capped at2.5sec; descriptive not safety threshold.','requests':out,'phases':phase_results,'anomalies':anomalies,'accepted_samples':len(rows),'raw_records':len(raw),'fan_modes':sorted(set(f['mode'] for f in fans))}
(O/'statistics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (O/'measurements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
with (O/'fan-snapshots.jsonl').open('w') as f:
 for r in fans:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(json.dumps({'accepted':len(rows),'requests':len(out),'phases':len(phases),'anomalies':len(anomalies)}))
