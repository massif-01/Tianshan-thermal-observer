"""Offline verification of the completed single run and its new instrument sidecar."""
import collections,datetime,hashlib,json,statistics
from pathlib import Path
R=Path(__file__).resolve().parent;RUN=R/'remote-result/run'
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def summary(v):return {'n':len(v),'min':min(v),'mean':statistics.mean(v),'median':statistics.median(v),'max':max(v)} if v else {'n':0}
s=read(RUN/'summary.json');launch=read(RUN/'launch.json');rq=rows(RUN/'requests.jsonl');ev=rows(RUN/'scheduler-events.jsonl');ad=rows(RUN/'admission.jsonl');res=rows(RUN/'resources.jsonl');link=read(R/'instrument-sidecar/run-link.json');csv=read(R/'instrument-sidecar/imported/checks/csv-verification.json')
verified={}
for root in [RUN,R/'instrument-sidecar']:
 m=read(root/'files.json')
 for n,x in m.items():assert (root/n).stat().st_size==x['bytes'] and sha(root/n)==x['sha256'],n
 verified[str(root.relative_to(R))]=len(m)
native=next((RUN/'native').glob('run-*'))
for n,h in read(native/'files.json').items():assert sha(native/n)==h,n
assert s['command_id']==launch['command_id']==link['command_id']=='fixed-anchors-20261019-658d6dcc-9a5e-4cbe-ab17-7cf70eda7cf7'
assert s['native_run_id']==link['native_run_id']==link['imported_run_id']=='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3'
assert link['native_files_index_sha256']==sha(RUN/'files.json')
assert len(rq)==len({x['request_id'] for x in rq})==179
assert all(x['status']=='completed' and x['done'] and x['finish_reason'] and x['usage'] for x in rq)
assert s['native_run_directories']==s['observer_instances_created']==s['request_executor_instances_created']==1
assert s['collector_engine_instance_id']==s['I02_shared_engine_instance_id'] and s['native_callbacks']==s['I02_preprocessed_views']
assert s['requester_instances_created']==4 and s['requester_sessions_all_closed'] and s['own_async_tasks_remaining']==0 and s['collector_summary']['polling_health']['end_inflight']==0
assert [x['mono_s'] for x in ev]==sorted(x['mono_s'] for x in ev)
phases=[]
for e in ev:
 if e['event']!='phase_start':continue
 index=e['index'];end=next(x for x in ev if x['event']=='phase_end' and x['index']==index);rr=[x for x in rq if x['stage_index']==index]
 windows=[x for x in ev if x['event']=='work_start_window_closed' and x['index']==index]
 if windows:assert all(x['submit_mono_s']<windows[0]['mono_s'] for x in rr)
 timeline=sorted([(x['submit_mono_s'],1) for x in rr]+[(x['client_end_mono_s'],-1) for x in rr]);n=peak=0
 for _,delta in timeline:n+=delta;peak=max(peak,n)
 assert n==0 and peak<=e['stage'].get('concurrency',1)
 phases.append({'index':index,'stage':e['stage'],'start_recorded_utc':e['recorded_at_utc'],'end_recorded_utc':end['recorded_at_utc'],'start_mono_s':e['mono_s'],'end_mono_s':end['mono_s'],'window_s':e['stage']['seconds'],'actual_stage_including_drain_s':end['mono_s']-e['mono_s'],'requests':len(rr),'observed_client_overlap_peak':peak,'request_duration_s':summary([x['duration_s'] for x in rr])})
assert [p['requests'] for p in phases if p['stage']['kind']=='work']==[23,32,101,23]
assert len({x['payload_sha256'] for x in rq})==1
assert csv['row_count']==2984 and csv['intervals']['count']==2983 and csv['intervals']['different_from_declared_1s']==0 and not csv['error_rows']
records=rows(R/'instrument-sidecar/imported/normalized/records.jsonl');assert len(records)==2984
assert link['original_csv_sha256']==csv['original_sha256']==sha(R/'instrument-sidecar/imported/original-csv/26071081-20261019173740.csv')
for record in records:assert record['time_uncertainty_s'] is None
receipt={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_run_id':s['native_run_id'],'command_id':s['command_id'],'index_verified':verified,'native_index_verified':len(read(native/'files.json')),'run_end_utc':s['clock_end']['utc'],'elapsed_s':s['elapsed_s'],'reason':s['reason'],'requests':179,'request_payload_sha256':rq[0]['payload_sha256'],'phases':phases,'request_duration_s':summary([x['duration_s'] for x in rq]),'all_requests_protocol_complete':True,'unknown_server_completion':False,'measurement_model_context_time_coverage':s['time_coverage'],'work_pause_seconds':s['time_coverage']['work_paused_s'],'resources':{'RSS_MiB':summary([x['rss_bytes']/2**20 for x in res]),'cpu_single_core_pct':summary([x['cpu_pct_single_core'] for x in res if x.get('cpu_pct_single_core') is not None])},'clock_offset_applied_to_CSV':False,'csv_original_sha256':csv['original_sha256'],'csv_rows':csv['row_count'],'recorded_instrument_span':[csv['first_instrument_datetime'],csv['last_instrument_datetime']],'temperature_column':'CH1','unit':'Celsius','interval_s':1,'same_value_adjacent_pairs_preserved':csv['equal_adjacent_temperature_pairs'],'same_run_link_verified':True,'original_run_index_unchanged_after_attachment':True,'own_tasks_and_native_inflight_zero':True,'no_training_or_state_correction':True}
print(json.dumps({k:receipt[k] for k in ['index_verified','native_index_verified','elapsed_s','requests','csv_rows','same_run_link_verified','original_run_index_unchanged_after_attachment']},ensure_ascii=False))
