"""Offline accounting of the single authorized run. Never contacts a device."""
import json,hashlib,collections,statistics,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
R=ROOT/'diagnostic'/'run'
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def stats(v):
 v=sorted(x for x in v if isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x))
 return dict(n=len(v),min=min(v),mean=statistics.mean(v),p50=statistics.median(v),p95=v[math.ceil(.95*len(v))-1],p99=v[math.ceil(.99*len(v))-1],max=max(v)) if v else dict(n=0)
s=read(R/'summary.json');adm=rows(R/'admission.jsonl');resources=rows(R/'resources.jsonl')
obs=[x for p in (R/'native').rglob('observations-*.jsonl') for x in rows(p)]
checks=[]
for name,identity in read(R/'files.json').items():
 p=R/name
 assert p.stat().st_size==identity['bytes'],name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==identity['sha256'],name
 checks.append(name)
assert s['native_run_directories']==s['observer_instances_created']==1
assert s['collector_engine_instance_id']==s['I02_shared_engine_instance_id']
assert s['requester_instances_created']==s['request_executor_instances_created']==s['protocol_requests']==0
assert (R/'requests.jsonl').stat().st_size==0
assert all(not x['start_allowed'] for x in adm)
assert s['native_callbacks']==s['I02_preprocessed_views']
assert s['own_async_tasks_remaining']==0
assert s['reason']=='diagnostic_duration'
intervals={}
for key in ['collection_available','model_available','field_safety_available']:
 spans=[]
 for a,b in zip(adm,adm[1:]):
  if not a[key]:
   if spans and spans[-1]['end_s']==a['scheduler_mono_s']:spans[-1]['end_s']=b['scheduler_mono_s']
   else:spans.append(dict(start_s=a['scheduler_mono_s'],end_s=b['scheduler_mono_s']))
 for x in spans:x['duration_s']=x['end_s']-x['start_s']
 intervals[key]=dict(first_usable_s=next((a['scheduler_mono_s'] for a in adm if a[key]),None),unavailable_spans=spans,longest_unavailable_s=max((x['duration_s'] for x in spans),default=0),total_unavailable_s=sum(x['duration_s'] for x in spans))
http={}
for kind in ['fan','temp']:
 rr=[x for x in obs if x['kind']==kind];ok=[x for x in rr if x.get('payload') is not None and not x.get('error')];bad=[x for x in rr if x not in ok]
 gaps=[b['mono_s']-a['mono_s'] for a,b in zip(ok,ok[1:])]
 phases=collections.Counter(x.get('poll_diagnostics',{}).get('last_phase','unknown') for x in rr)
 http[kind]=dict(records=len(rr),successful=len(ok),errors=len(bad),last_phase=dict(phases),rtt_ms=stats([x.get('round_trip_ms') for x in rr]),success_gap_s=stats(gaps),error_records=bad)
fan=[x['payload']['data']['fans'][0] for x in obs if x['kind']=='fan' and x.get('payload') and x['payload'].get('data',{}).get('fans')]
orins=[x['payload'] for x in obs if x['kind']=='orin' and x.get('payload')]
rails={k:stats([x['power'].get(k,{}).get('current') for x in orins]) for k in sorted({k for x in orins for k in x.get('power',{})})}
ct=[r for r in resources if r.get('cpu_pct_single_core') is not None]
endbytes=sum(p.stat().st_size for p in R.rglob('*') if p.is_file())
out=dict(native_run_id=s['native_run_id'],mode=s['mode'],reason=s['reason'],file_index_verified=len(checks),
 time_basis='relative seconds in actual host monotonic domain; unavailable spans use preceding gate until next ~0.1s evaluation, not exact source transition times',
 layer_unavailability=intervals,http=http,boundaries=[x for x in obs if x['kind']=='boundary'],
 source_period_metadata_counts=dict(collections.Counter(x.get('telemetry_meta',{}).get('source_sample_interval_ms') for x in orins)),
 platforms=[json.loads(x) for x in sorted({json.dumps(o.get('platform',{}),sort_keys=True) for o in orins})],
 telemetry=dict(orin_records=len(orins),tj_C=stats([x.get('temperature',{}).get('tj') for x in orins]),gpu_utilization_pct=stats([x.get('gpu',{}).get('utilization_pct') for x in orins]),independent_rail_current_mW=rails,pwm_percent=stats([x.get('duty') for x in fan if x.get('duty_valid')]),gain=stats([x.get('controller_gain') for x in fan]),mode_counts=dict(collections.Counter(x.get('mode') for x in fan)),fault_true=sum(x.get('fault') is True for x in fan),guard_true=sum(x.get('guard_active') is True for x in fan),temp_stale_true=sum(x.get('temp_stale') is True for x in fan)),
 resources=dict(samples=len(resources),rss_MiB=stats([r['rss_bytes']/2**20 for r in resources]),cpu_single_core_pct=stats([r['cpu_pct_single_core'] for r in ct]),cpu_time_average_pct=100*((resources[-1]['cpu_times']['user']+resources[-1]['cpu_times']['system'])-(resources[0]['cpu_times']['user']+resources[0]['cpu_times']['system']))/(resources[-1]['mono_s']-resources[0]['mono_s']),final_run_files_bytes=endbytes),
 invariant_checks=dict(one_native_run=True,shared_quality_engine=True,requester_and_inference_zero=True,all_start_allowed_false_expected=True,own_tasks_remaining_zero=True))
out['terminal_evaluation']=adm[-1]
out['last_joint_ready_evaluation']=next((x for x in reversed(adm) if x['collection_available'] and x['model_available'] and x['field_safety_available']),None)
out['terminal_boundary_note']='Native collection ended at configured duration; closing Socket.IO emitted observation:961. Last gate at 300.0866s withdrew current eligibility under I-02. Coverage integrates preceding gate; no interval after final gate is inferred.'
native_index=next((R/'native').rglob('files.json'));native_files=read(native_index)
for name,h in native_files.items():assert hashlib.sha256((native_index.parent/name).read_bytes()).hexdigest()==h,name
out['native_index_verified']=len(native_files)
(ROOT/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['native_run_id','file_index_verified','layer_unavailability','resources']},ensure_ascii=False,indent=2))
