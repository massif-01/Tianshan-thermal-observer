"""Replays preserved observations through the production causal processor."""
from pathlib import Path
from .config import load_config
from .engine import Engine
from .util import file_hash, read_json, seal, verify_seal, write_json
import json


def replay(run, model=None):
    run = Path(run)
    manifest = read_json(run / 'manifest.json')
    c = load_config(environ={})
    # Public manifests intentionally replace credential paths; they are not executable configs.
    saved = manifest['config']
    for section in ('orin', 'tianshan'):
        saved[section]['headers_file'] = None
        saved[section]['ca_file'] = None
    from .config import merge, validate
    merge(c, saved)
    validate(c)
    engine = Engine(c, model)
    engine.retain_origins = True
    scores, accepted, times = [], [], []
    invalid_segments = set()
    sources = {}
    expected = 0
    for path in sorted(run.glob('observations-*.jsonl')):
        sources[str(path.name)] = file_hash(path)
        with path.open() as f:
            for line in f:
                if len(line.encode()) > 100000:
                    raise ValueError('oversized stored observation')
                r = json.loads(line)
                expected += 1
                if r['ref'] != f"{manifest['observer_run_id']}/observation:{expected}" or r['observer_run_id'] != manifest['observer_run_id']:
                    raise ValueError('observation reference mismatch')
                if times and r['mono_s'] < times[-1]:
                    raise ValueError('run monotonic clock changed: split run required')
                times.append(r['mono_s'])
                out = engine.process(r)
                scores.extend(out['scores'])
                if out['quality'] and out['quality'].get('invalidated_segment') is not None:
                    invalid_segments.add(out['quality']['invalidated_segment'])
                if out['quality'] and out['quality']['accepted']:
                    accepted.append(r['ref'])
    scores.extend(engine.invalidate('run_end'))
    lookup = {(s['prediction_id'], str(s['horizon_s'])): s for s in scores}
    rows = []
    for p in engine.origins:
        row = dict(p['origin'], id=p['id'], labels={}, baseline_values=p['values'], firmware_45s_diagnostic=p['firmware_45s_diagnostic'])
        row['support_start'] = min(row['support_start'], row['t'] - 180)
        row['support_end'] = row['t'] + 90 + engine.tolerance
        row['label_status'] = {}
        if row['segment'] in invalid_segments:
            row['normal_auto'] = False
            row['invalid_segment_reason'] = 'identity_conflict_or_sequence_regression'
        for h in (15, 45, 90):
            s = lookup.get((p['id'], str(h)), {})
            row['label_status'][str(h)] = s.get('status', 'no_future_label')
            if s.get('status') == 'scored' and row['segment'] not in invalid_segments:
                row['labels'][str(h)] = {'value': s['truth'], 'ref': s['label_ref'], 't': s['label_t'], 'offset_s': s['offset_s']}
        rows.append(row)
    return {'manifest': manifest, 'rows': rows, 'quality': dict(engine.q.counts), 'processing': dict(engine.counts), 'source_files': sources, 'accepted_refs': accepted}


def build_dataset(runs):
    all_rows, sources, manifests = [], {}, []
    periods = set()
    for run in runs:
        result = replay(run)
        m = result['manifest']
        if m['observer_run_id'] in sources:
            raise ValueError('duplicate run')
        sources[m['observer_run_id']] = result['source_files']
        manifests.append({k: m.get(k) for k in ('observer_run_id', 'episode', 'episode_evidence', 'simulated', 'started_at_utc', 'deployment_status', 'source_period_ms')})
        periods.add(m['source_period_ms'])
        all_rows.extend(result['rows'])
    if len(periods) != 1 or None in periods:
        raise ValueError('one evidenced source period is required for modeling')
    return seal({'schema_version': 1, 'feature_schema': 1, 'time_axis': 'observer_receive', 'source_period_s': periods.pop() / 1000, 'horizons_s': [15, 45, 90], 'simulated': any(m['simulated'] for m in manifests), 'sources': sources, 'runs': manifests, 'rows': all_rows})


def load_dataset(path):
    d = verify_seal(read_json(path))
    if d.get('schema_version') != 1 or d.get('feature_schema') != 1 or d.get('time_axis') != 'observer_receive' or d.get('horizons_s') != [15, 45, 90]:
        raise ValueError('unsupported dataset contract')
    if len({r['id'] for r in d['rows']}) != len(d['rows']):
        raise ValueError('duplicate origin identity')
    for r in d['rows']:
        if r['available_at'] != r['t'] or r['support_start'] > r['t'] or r['support_end'] < r['t'] + 90:
            raise ValueError('invalid causal support')
    return d


def freeze_split(runs, output, exploratory=False):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    d = build_dataset(runs)
    rows = d['rows']
    episodes = []
    for m in sorted(d['runs'], key=lambda x: x['started_at_utc']):
        if not m.get('episode_evidence') and not d['simulated'] and not exploratory:
            raise ValueError('episode independence unknown: provide --episode during recording, or use --exploratory')
        if m['episode'] not in episodes:
            episodes.append(m['episode'])
    mapping = {}
    scope = 'chronological_episodes'
    if len(episodes) >= 3:
        n = len(episodes)
        # Keep at least two untouched test episodes whenever five or more exist.
        test_n = max(2, n // 5) if n >= 5 else 1
        val_n = max(1, (n - test_n) // 4)
        for i, e in enumerate(episodes):
            part = 'train' if i < n - test_n - val_n else ('validation' if i < n - test_n else 'test')
            for r in rows:
                if r['episode'] == e:
                    mapping[r['id']] = part
    elif exploratory and len(episodes) == 1 and len(d['runs']) == 1 and rows:
        scope = 'same_thermal_process_time_extrapolation'
        first, last = min(r['t'] for r in rows), max(r['t'] for r in rows)
        a, b = first + (last - first) * 0.6, first + (last - first) * 0.8
        for r in rows:
            if r['support_end'] < a:
                mapping[r['id']] = 'train'
            elif r['support_start'] > a and r['support_end'] < b:
                mapping[r['id']] = 'validation'
            elif r['support_start'] > b:
                mapping[r['id']] = 'test'
    else:
        raise ValueError('至少需要三段可分配过程；单过程仅支持显式 --exploratory 时间外推。')
    discarded = [{'id': r['id'], 'reason': 'purge_support_crosses_partition'} for r in rows if r['id'] not in mapping]
    split = seal({'schema_version': 1, 'dataset_sha256': d['sha256'], 'scope': scope, 'simulated': d['simulated'], 'independence': 'simulated' if d['simulated'] else ('operator_named_episodes' if not exploratory else 'unconfirmed'), 'partitions': {p: [r['id'] for r in rows if mapping.get(r['id']) == p] for p in ('train', 'validation', 'test')}, 'discarded': discarded, 'sources': d['sources'], 'episodes_order': episodes, 'reference_contract': 'TTO-PLAN-v1.0', 'test_use_policy': 'one sealed evaluation; any tuning afterwards needs new unused test processes'})
    check_split(d, split)
    write_json(out / 'dataset.json', d)
    write_json(out / 'split.json', split)
    return out


def check_split(d, s):
    verify_seal(s)
    if s.get('schema_version') != 1 or s.get('dataset_sha256') != d['sha256'] or s.get('sources') != d['sources']:
        raise ValueError('split/dataset/source hash mismatch')
    byid = {r['id']: r for r in d['rows']}
    seen = set()
    intervals = {}
    refs = {p: set() for p in s['partitions']}
    for part, ids in s['partitions'].items():
        if part not in ('train', 'validation', 'test') or not ids:
            raise ValueError('nonempty train/validation/test required')
        for id_ in ids:
            if id_ not in byid or id_ in seen:
                raise ValueError('unknown/overlapping origin')
            seen.add(id_)
            r = byid[id_]
            intervals.setdefault(r['run_id'], {}).setdefault(part, []).append((r['support_start'], r['support_end']))
            refs[part].update(r['raw_refs'])
            refs[part].update(label['ref'] for label in r['labels'].values())
    parts = ('train', 'validation', 'test')
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if refs[a] & refs[b]:
                raise ValueError('raw references shared across partitions')
            for groups in intervals.values():
                if a in groups and b in groups and max(x[1] for x in groups[a]) >= min(x[0] for x in groups[b]):
                    raise ValueError('raw temporal support overlap or nonchronological split')
    # Whole episodes must be ordered, not arbitrarily interleaved across runs.
    order = s['episodes_order']
    episode_parts = {}
    for part, ids in s['partitions'].items():
        for id_ in ids:
            episode_parts.setdefault(byid[id_]['episode'], set()).add(part)
    if s['scope'] == 'chronological_episodes':
        if any(len(p) != 1 for p in episode_parts.values()):
            raise ValueError('episode split across partitions')
        sequence = [parts.index(next(iter(episode_parts[e]))) for e in order if e in episode_parts]
        if sequence != sorted(sequence):
            raise ValueError('episodes not chronological')
    return byid
