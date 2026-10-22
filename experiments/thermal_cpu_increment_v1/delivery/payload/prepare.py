"""Copy a minimal immutable subset; record all sources and freeze one calibration."""
import argparse
import datetime as dt
import statistics
import subprocess
import shutil
from pathlib import Path
from common import ROOT, read, lines, write, sha


def prepare(repo):
    target = ROOT / 'inputs'
    target.mkdir(exist_ok=False)
    old = repo / 'deliverables/TTO-冻结模型与CPU先导补测-GPT6Pro复审交接'
    model = old / 'evidence/modeling'
    field = old / 'evidence/field/remote-result/run'
    sources = {f: model / f for f in [
        'inputs/native/observations-0001.jsonl', 'inputs/native/manifest.json',
        'results/samples-and-causal-states.jsonl', 'results/predictions.jsonl',
        'results/quality-ledger.jsonl', 'results/phases.json',
        'results/A-long-summary.json', 'results/metrics-common.json',
        'spec.json', 'vendor/src/tto_field/research/observer-spec.json',
        'vendor/src/tto_field/research/models/primary.json']}
    sources.update({'field/' + f: field / f for f in [
        'requests.jsonl', 'protocol.jsonl', 'scheduler-events.jsonl', 'summary.json']})
    entries = []
    for rel, src in sources.items():
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        entries.append(dict(local_path=str(dst.relative_to(ROOT)), source_path=str(src),
                            bytes=src.stat().st_size, sha256=sha(src)))
    expected = read(ROOT / 'analysis-spec.json')['immutable']
    for f, key in [('vendor/src/tto_field/research/models/primary.json', 'model_sha256'),
                   ('vendor/src/tto_field/research/observer-spec.json', 'observer_spec_sha256'),
                   ('spec.json', 'comparison_spec_sha256')]:
        assert sha(target / f) == expected[key]
    for e in read(ROOT / 'handoff/SHA256.json')['files']:
        p = ROOT / 'handoff' / e['path']
        assert sha(p) == e['sha256'] and p.stat().st_size == e['bytes']
    write(ROOT / 'sources.json', dict(run_id=read(ROOT/'analysis-spec.json')['run_id'],
        review_archive_sha256='4a5f2897e3f19cc13d873d26da8144308d7b9d6fe0b7f917f8631d804df280f0',
        original_handoff_sha256='74c442362d6ac28ffc9032c15f7ad8276b5e6b20ea8fa24fa0a4ac9e190c46a6',
        sources=entries, private_and_shared_identities='original shared archive identities retained; no raw or archive rewriting',
        data_role='one already-analysed development episode; no new field data'))
    # Snapshot all tracked files plus old research inputs/results/specs and delivered evidence.
    protected = {repo / n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=repo).decode().split('\0') if n}
    for base in [old, repo/'experiments/thermal_fixed_anchors_frozen_v1', repo/'src', repo/'tests']:
        protected.update(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for pattern in ['**/*test-used*', '**/*split*.json', '**/models/*.json']:
        protected.update(p for p in (repo/'experiments').glob(pattern) if p.is_file() and ROOT not in p.parents)
    write(ROOT / 'protected-before.json', [dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
                                          for p in sorted(protected) if p.is_file()])


def calibrate():
    spec = read(ROOT/'analysis-spec.json')
    samples = {a['ref']: a for a in lines(ROOT/'inputs/results/samples-and-causal-states.jsonl') if a['source_valid']}
    phases = read(ROOT/'inputs/results/phases.json')
    bg = next(p for p in phases if p['name'] == '0-background')['start']
    work = next(p for p in phases if p['name'] == '1-work')['start']
    groups = {'idle': [], 'active': []}
    for a in lines(ROOT/'inputs/inputs/native/observations-0001.jsonl'):
        if a['ref'] not in samples:
            continue
        wall = samples[a['ref']]['wall']
        name = 'idle' if bg+60 <= wall <= bg+240 else ('active' if work+60 <= wall <= work+300 else None)
        if name:
            p = a['payload']; c = [v['usage'] for v in p['cpu']['cores']]
            groups[name].append(dict(ref=a['ref'], gpu_pct=p['gpu']['utilization_pct'],
                gpu_W=p['power']['vdd_gpu']['current']/1000,
                cpu_soc_mss_W=p['power']['vdd_cpu_soc_mss']['current']/1000,
                cpu_mean_pct=statistics.mean(c), cpu_max_pct=max(c)))
    features = spec['features']['INPUT-CORE']
    levels = {k:{n:statistics.median(r[n] for r in rows) for n in features} for k,rows in groups.items()}
    assert all(levels['active'][n] > levels['idle'][n] for n in features)
    config = dict(version='CPU-ACTIVITY-1.0.0', deployable=False, levels=levels,
        on=spec['activity_rule']['on'], off=spec['activity_rule']['off'],
        low_confirmation_s=spec['activity_rule']['low_confirmation_s'], relaxation_tau_s=30.,
        variants={k:spec['features'][k] for k in ('INPUT-BASE','INPUT-MEAN','INPUT-CORE')},
        dynamic_spec_path='inputs/vendor/src/tto_field/research/observer-spec.json',
        immutable=spec['immutable'], calibration_refs={k:[r['ref'] for r in v] for k,v in groups.items()},
        attempts=[dict(id=1, method='max-normalized-contrast hysteresis', selected=True,
            reason='single preregistered candidate; amplitude medians only, no temperature or detection scores used')])
    write(ROOT/'candidate.json', config)
    write(ROOT/'freeze.json', dict(frozen_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        spec_sha256=sha(ROOT/'analysis-spec.json'), candidate_sha256=sha(ROOT/'candidate.json'),
        source_manifest_sha256=sha(ROOT/'sources.json'), parameters_selected_before_evaluation=True,
        candidate_attempts=1, theta_fits=0, field_authorized=False))
    print('Frozen one candidate:', config['levels'], flush=True)


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True)
    a=ap.parse_args()
    prepare(a.repo.resolve())
    calibrate()
