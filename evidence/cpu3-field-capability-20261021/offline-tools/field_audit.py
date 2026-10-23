from pathlib import Path
import json,hashlib,shutil,statistics,zipfile
r=Path('evidence/cpu3-field-capability-20261021');run=r/'remote-result/run';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for idx in [run/'files.json',*run.glob('native/*/files.json')]:
 for name,v in json.loads(idx.read_text()).items():
  f=idx.parent/name
  if isinstance(v,dict): assert f.stat().st_size==v['bytes'] and h(f)==v['sha256'],f
  else: assert h(f)==v,f
  checks.append(str(f.relative_to(r)))
s=json.loads((run/'summary.json').read_text());l=json.loads((run/'launch.json').read_text());p=json.loads((run/'thread-policy.json').read_text());assert p['pid']==s['clock_end']['pid']==l['clock_start']['pid']==12283
shutil.copy('evidence/cpu2-capability-20261020/preparation/field-payload/source-config.json',r/'remote-result/payload/source-config.json')
with zipfile.ZipFile('deliverables/TTO-数值线程策略与旁录前资源检查-收尾证据包.zip') as z:(r/'remote-result/payload/cpu_source.py').write_bytes(z.read('source/src/tto_field/cpu_source.py'))
assert h(r/'remote-result/payload/source-config.json')==l['binding']['sidecar']['source_config_sha256']
assert h(r/'remote-result/payload/cpu_source.py')==l['binding']['sidecar']['source_script_sha256']
rows=lambda n:[json.loads(x) for x in (run/n).read_text().splitlines()]
arr=rows('cpu-sidecar-arrivals.jsonl');wire=rows('cpu-sidecar-wire.jsonl');res=rows('resources.jsonl');ev=rows('sidecar-events.jsonl')
start=next(x['mono_s'] for x in ev if x['event']=='started');end=next(x['mono_s'] for x in ev if x['event']=='stop_sidecar_only')
phase=lambda t:'before' if t<start else 'during' if t<end else 'after'
stats={}
for k in ['before','during','after']:
 xs=[x for x in res if phase(x['mono_s'])==k];cpu=[x['cpu_pct_single_core'] for x in xs if x.get('cpu_pct_single_core') is not None];rss=[x['rss_bytes'] for x in xs if x.get('rss_bytes') is not None]
 stats[k]=dict(samples=len(xs),cpu_valid_intervals=len(cpu),cpu_mean_pct=statistics.mean(cpu) if cpu else None,cpu_max_pct=max(cpu) if cpu else None,rss_max_mib=max(rss)/1024**2 if rss else None,cpu_over8_count=sum(x>8 for x in cpu))
src=[x['source'] for x in arr];metrics=dict(packets=len(arr),wire=len(wire),complete_cpu_windows=sum(bool((x.get('cpu')or{}).get('complete_online_set')) for x in src),rss_max_mib=max(x['resources']['rss_bytes'] for x in src)/1024**2,cpu_singlecore_pct_max_after5s=max([x['resources']['cpu_seconds']/x['resources']['elapsed_s']*100 for x in src if x['resources']['elapsed_s']>=5],default=None),source_elapsed_last_s=src[-1]['resources']['elapsed_s'],source_cpu_cumulative_s=src[-1]['resources']['cpu_seconds'],read_max_s=max(x['resources']['read_duration_s'] for x in src),source_stop_reasons=[x['stop_reasons'] for x in src if x['stop_reasons']])
audit=dict(native_run_id=s['native_run_id'],pid=p['pid'],same_pid_verified=True,files_checked=len(checks),all_recorded_SHA_pass=True,elapsed_s=s['elapsed_s'],reason=s['reason'],sidecar_status=s['sidecar_status'],sidecar_interval_s=[start,end],sidecar_duration_s=end-start,resources_by_actual_phase=stats,source=metrics,fan_success_intervals=s['fan_success_intervals'],unique_collector=s['native_run_directories'],unique_observer=s['observer_instances_created'],requesters=s['requester_instances_created'],protocol_requests=s['protocol_requests'],own_async_tasks_remaining=s['own_async_tasks_remaining'])
(r/'field-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print(json.dumps(audit,indent=2))
