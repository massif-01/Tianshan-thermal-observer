"""Offline capability receipt from the sole native diagnostic and independent source arrivals.
Never authorizes load. Output goes to a fresh file, preserving the run index.
"""
import argparse,json,statistics,hashlib
from pathlib import Path
from tto_field.cpu_pilot import sidecar_identity
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
r=a.run;load=lambda n:json.loads((r/n).read_text());s=load('summary.json');launch=load('launch.json')
if s['mode']!='diagnose' or s['protocol_requests'] or not 59<=s['elapsed_s']<=90:raise SystemExit('not a complete no-load60s diagnostic')
rows=[json.loads(x) for x in (r/'cpu-sidecar-arrivals.jsonl').read_text().splitlines()];sources=[x['source'] for x in rows]
resources=[json.loads(x) for x in (r/'resources.jsonl').read_text().splitlines()]
q=lambda xs:sorted(xs)[min(len(xs)-1,int(.95*(len(xs)-1)))] if xs else None
periods=[b['read_start_mono_s']-a['read_start_mono_s'] for a,b in zip(sources,sources[1:])]
read95=q([x['resources']['read_duration_s'] for x in sources]);jitter95=q([x['resources'].get('deadline_jitter_s',0) for x in sources])
states=[json.loads(x) for x in (r/'states.jsonl').read_text().splitlines()]
lag={'baseline':[],'sidecar':[]}
for x in states:
    c=x['clock'];t=c['observer_input_mono_s']-c['session_origin_mono_s']
    lag['baseline' if t<30 else 'sidecar'].append(c['generated_at_mono_s']-c['observer_input_mono_s'])
lag95={k:q(v) for k,v in lag.items()}
checks=dict(native_delay_budget=all(x is not None for x in lag95.values()) and lag95['sidecar']<=.25 and lag95['sidecar']-lag95['baseline']<=.1,complete_native=s['native_run_directories']==1 and s['observer_instances_created']==1,
            packets=len(rows)>=100,clock_identified=all(x['clock_status']=='source_identified_mapping_unknown' for x in rows),
            cpu_measured=all(x.get('cpu',{}).get('complete_online_set') for x in sources[1:]),
            read_budget=read95 is not None and read95<=.02,jitter_budget=jitter95 is not None and jitter95<=.1,
            no_sidecar_trip=s.get('sidecar_status')=='native_run_ending',
            native_fan_gap=s['fan_success_intervals']['max_s']<=2.5)
# Qualification is software capacity only. Main-question usefulness remains an explicit review/user decision.
receipt=dict(schema='TTO-CPU-CAPABILITY-RECEIPT-v1',candidate_version=launch['version'],config_sha256=launch['config_sha256'],
    sidecar_config_sha256=sidecar_identity(launch['binding']['sidecar']),qualified=all(checks.values()),checks=checks,
    evaluation_scope='arrival_side',automatic_work_authorization=False,resource_check_evidence=dict(native_callback_lag_p95_s=lag95,read_p95_s=read95,jitter_p95_s=jitter95,
      baseline_resource_rows=[x for x in resources if x['mono_s']<30],sidecar_resource_rows=[x for x in resources if x['mono_s']>=30]),
    measured_resolution_evidence=dict(cpu_median_read_period_s=statistics.median(periods) if periods else None,
       GPU_independent_resolution='unknown unless actual source window/generation evidence provided',rail_independent_resolution='unknown; native coarse baseline retained',
       exact_cross_host_source_lead='unknown; receiver receipt order is usable without zero-latency assumption'),
    source_run_id=s['native_run_id'],files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['launch.json','summary.json','resources.jsonl','cpu-sidecar-arrivals.jsonl']})
with a.output.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(qualified=receipt['qualified'],checks=checks,automatic_work_authorization=False),indent=2))
