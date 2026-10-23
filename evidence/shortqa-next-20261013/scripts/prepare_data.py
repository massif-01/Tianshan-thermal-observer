"""Preserved schema2 data -> bounded, offline exploration inputs; no device I/O."""
import collections
import csv
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from tto.config import load_config, merge, validate
from tto.dataset import build_dataset, freeze_split, check_split
from tto.engine import engine_for
from tto.features import TJ_COLUMNS
from tto.model import eligible_scope
from tto.training import eligible
from tto.util import write_json, seal

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]


def json_write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def describe(run, output):
    manifest = json.loads((run / 'manifest.json').read_text())
    c = load_config(environ={})
    merge(c, manifest['config'])
    validate(c)
    engine = engine_for(c, record_schema=2)
    # Every accepted source sample, not just five-second prediction origins.
    accepted, anomalies, refs = [], [], {}
    counts = collections.Counter()
    for line in (run / 'observations-0001.jsonl').open():
        r = json.loads(line)
        counts[r['kind']] += 1
        refs[r['ref']] = r['received_at_utc']
        result = engine.process(r)
        if r.get('error_class') or r['kind'] == 'fan' and any(f.get('temp_stale') or f.get('guard_active') or f.get('fault') for f in r['payload'].get('data', {}).get('fans', [])):
            anomalies.append(dict(ref=r['ref'], utc=r['received_at_utc'], kind=r['kind'],
                                  reason=r.get('error_class') or r.get('reason'), payload=r['payload']))
        q = result['quality']
        if q and q['accepted']:
            s = engine.features.history[-1]
            f = engine.fan['data'] if engine.fan else {}
            accepted.append(dict(utc=r['received_at_utc'], mono_s=r['mono_s'], ref=r['ref'],
                                 sample_seq=r['payload']['telemetry_meta']['sample_seq'], segment=s['segment'],
                                 normal_auto=s['normal_auto'], control_eligible=s['control_eligible'],
                                 values=s['values'], aux_refs=s['aux_refs'],
                                 fan_observation={k:f.get(k) for k in ['successful_duty','controller_gain','control_temperature',
                                                                       'guard_temperature','slope_c_per_min',
                                                                       'predicted_temperature','temp_stale','guard_active','fault']},
                                 fan_return_age_s=r['mono_s']-engine.fan['t'] if engine.fan else None,
                                 gpu=q['gpu']))
    with (output / 'accepted-timeseries.jsonl').open('w') as f:
        for a in accepted:
            f.write(json.dumps(a, ensure_ascii=False, separators=(',', ':')) + '\n')
    segments = []
    group = []
    for a in accepted:
        if group and (a['segment'] != group[-1]['segment'] or a['control_eligible'] != group[-1]['control_eligible']):
            segments.append(group); group=[]
        group.append(a)
    if group:
        segments.append(group)
    continuous = [dict(segment=g[0]['segment'], normal_auto=g[0]['normal_auto'], control_eligible=g[0]['control_eligible'],
                       start_utc=g[0]['utc'], end_utc=g[-1]['utc'], start_mono_s=g[0]['mono_s'], end_mono_s=g[-1]['mono_s'],
                       span_s=g[-1]['mono_s']-g[0]['mono_s'], n=len(g), first_ref=g[0]['ref'],last_ref=g[-1]['ref'],
                       max_receive_step_s=max([b['mono_s']-a['mono_s'] for a,b in zip(g,g[1:])] or [0])) for g in segments]
    d = build_dataset([run])
    write_json(output / 'all-origins-dataset.json', d)
    summary = dict(run_id=manifest['observer_run_id'], episode=manifest['episode'],
                   usage='exploration/development; previously analyzed', record_counts=dict(counts),
                   accepted_count=len(accepted), quality_counts=dict(engine.q.counts),
                   continuous_segments=continuous, anomalies=anomalies,
                   profile=d['feature_profile_id'], input_contract=d['input_contract'],
                   original_source_identity=manifest['source_identity']['sha256'],
                   fields_availability={k:sum(a['values'].get(k) is not None for a in accepted) for k in accepted[0]['values']},
                   source_receive_step_s=dict(min=min(b['mono_s']-a['mono_s'] for a,b in zip(accepted,accepted[1:])),
                                              max=max(b['mono_s']-a['mono_s'] for a,b in zip(accepted,accepted[1:]))),
                   origins=len(d['rows']), history_ready=sum(r['history_ready'] for r in d['rows']),
                   all_label_TJ_eligible=sum(eligible(r,TJ_COLUMNS) for r in d['rows']))
    try:
        frozen = output / 'exploratory-split'
        if not frozen.exists():
            freeze_split([run], frozen, exploratory=True)
        split = json.loads((frozen / 'split.json').read_text())
        check_split(d, split)
        lookup={r['id']:r for r in d['rows']}
        summary['split']=dict(scope=split['scope'], independence=split['independence'],
                               counts={k:len(ids) for k,ids in split['partitions'].items()},
                               eligible_TJ_counts={k:sum(eligible(lookup[i],TJ_COLUMNS) for i in ids) for k,ids in split['partitions'].items()},
                               purged=len(split['discarded']),
                               ranges={k:dict(first_utc=refs[lookup[ids[0]]['ref']],last_utc=refs[lookup[ids[-1]]['ref']]) for k,ids in split['partitions'].items()},
                               semantics='tool test partition is a purged later development window; never an untouched formal test')
    except ValueError as e:
        summary['split_refused']=str(e)
    json_write(output / 'data-qualification.json', summary)
    return summary


def main():
    dest=OUT/'model-exploration'
    environment=dict(python=sys.version, executable=sys.executable, prefix=sys.prefix, system=platform.platform(),
                     tto_source=__import__('tto').__file__, reference_commit='52f571acb128af44f4b06bbba049148e00fd97fb',
                     dependencies={m:importlib.metadata.version(m) for m in ['numpy','scikit-learn','psutil','threadpoolctl']},
                     selection='Choose short-QA for one bounded Ridge fit because it is the focus of this task, before inspecting scores; both runs for qualification/B0/B1 descriptions.',
                     bounds=dict(ridge_lambda_grid=[0.001,0.01,0.1,1.0], thread_limit=1, timeout_s=600, rss_mib=2048))
    json_write(OUT/'identity/offline-runtime.json',environment)
    runs=[];results=[]
    for name,label in [('formal-collection-20261013-round2','seven-conditions'),('short-qa-20261013','short-qa')]:
        run=next((ROOT/'evidence'/name).glob('run-*'));runs.append(run)
        output=dest/label;output.mkdir(exist_ok=True)
        summary=describe(run,output);results.append(summary)
        print(label, summary['accepted_count'], summary.get('split',summary.get('split_refused')),flush=True)
    if (dest/'two-run-split-decision.json').exists():
        combined=json.loads((dest/'two-run-split-decision.json').read_text())
    else:
        try:
            freeze_split(runs,dest/'two-runs-not-supported',exploratory=True)
            combined=dict(refused=False)
        except ValueError as e:
            combined=dict(refused=True,reason=str(e),decision='No code change or invented third episode to bypass the tool.')
    json_write(dest/'two-run-split-decision.json',combined)
    json_write(OUT/'results/data-qualification-summary.json',results)


if __name__=='__main__':
    main()
