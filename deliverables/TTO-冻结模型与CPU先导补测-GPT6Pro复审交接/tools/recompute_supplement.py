"""Read-only descriptive supplement from the already sealed run. No fitting or lag search."""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text())


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def lines(p):
    with p.open() as f:
        for s in f:
            if s.strip():yield json.loads(s)


def write(p,d):
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def recompute(root,out):
    model=root/'evidence/modeling'
    native=model/'inputs/native'
    samples=model/'results/samples-and-causal-states.jsonl'
    cohort={a['ref']:a for a in lines(samples) if a['source_valid']}
    raw_path=native/'observations-0001.jsonl'
    rows=[]
    for raw in lines(raw_path):
        if raw['ref'] not in cohort:continue
        a=cohort[raw['ref']];p=raw['payload'];cores=p['cpu']['cores']
        valid=[c for c in cores if isinstance(c.get('usage'),(int,float)) and not isinstance(c.get('usage'),bool)]
        assert valid,raw['ref']
        ram=p['memory']['ram'];assert ram['unit']=='MB'
        peak=max(c['usage'] for c in valid)
        gpu=p['gpu']
        rows.append(dict(ref=raw['ref'],received_at_utc=raw['received_at_utc'],mono_s=raw['mono_s'],
            retrospective_phase=a['phase'],reported_cores=len(cores),numeric_cores=len(valid),
            CPU_mean_pct=statistics.mean(c['usage'] for c in valid),CPU_max_pct=peak,
            CPU_max_core_ids=json.dumps([c['id'] for c in valid if c['usage']==peak]),
            CPU_core_usage_json=json.dumps([dict(id=c['id'],usage=c.get('usage'),freq=c.get('freq')) for c in cores],separators=(',',':')),
            RAM_used_reported_MB=ram['used'],RAM_total_reported_MB=ram['total'],
            GPU_utilization_pct=gpu.get('utilization_pct'),GPU_status=gpu.get('status'),GPU_source=gpu.get('source'),
            GPU_sampled_at_utc=gpu.get('sampled_at_utc'),GPU_age_at_telemetry_receive_ms=gpu.get('age_at_telemetry_receive_ms'),
            source_sample_interval_ms=p['telemetry_meta'].get('source_sample_interval_ms'),
            GPU_sample_interval_ms=gpu.get('sample_interval_ms'),
            model_observer_phase=a['states']['AUGMENTED-KF']['phase']))
    assert len(rows)==len(cohort)==2706
    out.mkdir(parents=True,exist_ok=False)
    with (out/'cpu-per-core-observations.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    stats=[]
    for phase in ['all']+sorted({r['retrospective_phase'] for r in rows}):
        rs=[r for r in rows if phase=='all' or r['retrospective_phase']==phase]
        ages=[r['GPU_age_at_telemetry_receive_ms'] for r in rs if r['GPU_age_at_telemetry_receive_ms'] is not None]
        stats.append(dict(phase=phase,n=len(rs),reported_core_counts=sorted({r['reported_cores'] for r in rs}),
            numeric_core_counts=sorted({r['numeric_cores'] for r in rs}),
            CPU_all_core_mean_time_mean_pct=statistics.mean(r['CPU_mean_pct'] for r in rs),
            CPU_busiest_core_time_median_pct=statistics.median(r['CPU_max_pct'] for r in rs),
            CPU_busiest_core_observed_max_pct=max(r['CPU_max_pct'] for r in rs),
            RAM_used_reported_MB_range=[min(r['RAM_used_reported_MB'] for r in rs),max(r['RAM_used_reported_MB'] for r in rs)],
            GPU_age_at_receive_ms=dict(n=len(ages),min=min(ages),median=statistics.median(ages),max=max(ages)),
            source_period_ms=sorted({r['source_sample_interval_ms'] for r in rs}),
            GPU_recorded_period_ms=sorted({r['GPU_sample_interval_ms'] for r in rs})))
    write(out/'cpu-memory-time-summary.json',dict(role='post-hoc descriptive summary, not prediction or evidence of physical CPU lead',
        same_recorded_episode=True,new_field_runs=0,theta_fits=0,lag_or_threshold_searches=0,
        CPU_max_definition='maximum across numeric cores separately at each sample; not one fixed physical core across time',
        RAM_units='original reported MB; not relabelled MiB/GiB',
        GPU_age_meaning='age of the independent GPU reading at telemetry receive, not measured CPU-to-GPU lag',
        phase_used_as_predictor=False,groups=stats))
    write(out/'source-valid-cohort.json',dict(run_id=read(native/'manifest.json')['observer_run_id'],
        selected_existing_source_valid_TJ=2706,eligibility='unchanged source_valid flag in sealed modeling samples',
        raw_observations_sha256=sha(raw_path),sealed_samples_sha256=sha(samples),
        cohort_SHA256=hashlib.sha256('\n'.join(r['ref'] for r in rows).encode()).hexdigest(),
        original_refs_and_raw_per_core_values_preserved=True,missing_values_filled=False,
        CPU_GPU_subsecond_timing_proven=False,residency_transition_validated=False))
    metrics=read(model/'results/metrics-common.json')
    chosen=[r for r in metrics if r['phase']=='all' and r['qualification']=='all_available' and len(r['branches'])==5]
    boundary=[r for r in read(model/'results/stage-boundary-metrics.json') if r['phase']=='all' and r['h']==45]
    write(out/'existing-outcome-extract.json',dict(origin='exact selections from sealed existing JSON; not newly evaluated scores',
        metrics=chosen,boundary_metrics=boundary,A_long=read(model/'results/A-long-summary.json'),
        state_replay=read(model/'results/state-replay-verification.json'),
        surface=read(model/'results/surface-summary.json')))
    return dict(rows=len(rows),outputs=4,new_field_runs=0,theta_fits=0)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(recompute(args.root.resolve(),args.output.resolve()),ensure_ascii=False))
