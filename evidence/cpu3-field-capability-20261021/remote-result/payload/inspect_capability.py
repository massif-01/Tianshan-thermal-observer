"""Offline cpu.3 receipt; a baseline rejection is an explicit failed capability, not missing success."""
import argparse,json,statistics,hashlib
from pathlib import Path
from tto_field.cpu_pilot import sidecar_identity
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.run
load=lambda n:json.loads((r/n).read_text())
def rows(n):
    f=r/n;return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
s=load('summary.json');launch=load('launch.json');policy=load('thread-policy.json')
if s['mode']!='diagnose' or s['protocol_requests'] or not 59<=s['elapsed_s']<=90:raise SystemExit('not a complete no-load60s diagnostic')
arr=rows('cpu-sidecar-arrivals.jsonl');src=[x['source'] for x in arr];resources=rows('resources.jsonl');events=rows('sidecar-events.jsonl')
starts=[x['mono_s'] for x in events if x['event']=='started'];start=starts[0] if starts else None
stops=[x['mono_s'] for x in events if x['event']=='stop_sidecar_only'];end=stops[0] if stops else s['elapsed_s']
def phase(t):return 'before' if start is None or t<start else 'during' if t<end else 'after'
q=lambda xs:sorted(xs)[int(.95*(len(xs)-1))] if xs else None
periods=[b['read_start_mono_s']-x['read_start_mono_s'] for x,b in zip(src,src[1:])]
read95=q([x['resources']['read_duration_s'] for x in src]);jitter95=q([x['resources'].get('deadline_jitter_s',0) for x in src]);lags={k:[] for k in ('before','during','after')}
for x in rows('states.jsonl'):
    c=x['clock'];t=c['observer_input_mono_s']-c['session_origin_mono_s'];lags[phase(t)].append(c['generated_at_mono_s']-c['observer_input_mono_s'])
lag95={k:q(v) for k,v in lags.items()};baseline=load('baseline-resource-admission.json') if (r/'baseline-resource-admission.json').exists() else None
checks=dict(thread_policy=policy['verified'] and policy['pid']==s['clock_end']['pid'],baseline_resources=bool(baseline and baseline['allowed']),
    native_delay_budget=lag95['before'] is not None and lag95['during'] is not None and lag95['during']<=.25 and lag95['during']-lag95['before']<=.1,
    complete_native=s['native_run_directories']==1 and s['observer_instances_created']==1,packets=len(arr)>=100,
    clock_identified=bool(arr) and all(x['clock_status']=='source_identified_mapping_unknown' for x in arr),
    cpu_measured=len(src)>1 and all((x.get('cpu') or {}).get('complete_online_set') for x in src[1:]),
    read_budget=read95 is not None and read95<=.02,jitter_budget=jitter95 is not None and jitter95<=.1,
    no_sidecar_trip=s.get('sidecar_status')=='native_run_ending',native_fan_gap=s['fan_success_intervals']['max_s'] is not None and s['fan_success_intervals']['max_s']<=2.5)
receipt=dict(schema='TTO-CPU-CAPABILITY-RECEIPT-v2',candidate_version=launch['version'],config_sha256=launch['config_sha256'],
    sidecar_config_sha256=sidecar_identity(launch['binding']['sidecar']),qualified=all(checks.values()),checks=checks,evaluation_scope='arrival_side',automatic_work_authorization=False,
    actual_sidecar_interval=dict(start_mono_s=start,stop_mono_s=end if start is not None else None),baseline_admission=baseline,
    resource_check_evidence=dict(native_callback_lag_p95_s=lag95,read_p95_s=read95,jitter_p95_s=jitter95,resources_by_actual_phase={k:[x for x in resources if phase(x['mono_s'])==k] for k in lags}),
    measured_resolution_evidence=dict(cpu_median_read_period_s=statistics.median(periods) if periods else None,GPU_independent_resolution='unknown unless source window/generation provided',rail_independent_resolution='unknown; native coarse baseline retained',exact_cross_host_source_lead='unknown'),
    source_run_id=s['native_run_id'],files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['launch.json','summary.json','thread-policy.json','resources.jsonl']})
with a.output.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(qualified=receipt['qualified'],checks=checks,actual_sidecar_interval=receipt['actual_sidecar_interval']),indent=2))
