"""Replays preserved observations through the production causal processor."""
from pathlib import Path
from datetime import datetime, timezone
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
    clock = None
    clock_consistent = True
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
                try:
                    wall = utc_seconds(r['received_at_utc'])
                    if clock is None:
                        clock = {'first_mono_s': r['mono_s'], 'first_utc': r['received_at_utc'], 'last_utc': r['received_at_utc']}
                    elif abs(wall - utc_seconds(clock['first_utc']) - (r['mono_s'] - clock['first_mono_s'])) > 1:
                        clock_consistent = False
                    clock['last_utc'] = r['received_at_utc']
                except (ValueError, TypeError, KeyError):
                    clock_consistent = False
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
    time_evidence = dict(clock, clock_consistent=clock_consistent, basis='observer_receive_utc_with_run_monotonic_anchor') if clock else None
    return {'manifest': manifest, 'time_evidence': time_evidence, 'rows': rows, 'quality': dict(engine.q.counts), 'processing': dict(engine.counts), 'source_files': sources, 'accepted_refs': accepted}


def build_dataset(runs):
    all_rows, sources, manifests = [], {}, []
    periods = set()
    for run in runs:
        result = replay(run)
        m = result['manifest']
        if m['observer_run_id'] in sources:
            raise ValueError('duplicate run')
        sources[m['observer_run_id']] = result['source_files']
        manifests.append(dict({k: m.get(k) for k in ('observer_run_id', 'episode', 'episode_evidence', 'simulated', 'started_at_utc', 'deployment_status', 'source_period_ms')}, time_evidence=result['time_evidence']))
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


def utc_seconds(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('UTC evidence must contain a timezone')
    return stamp.timestamp()


def chronological_runs(d):
    """Use every run's actual receive range, never first-occurrence name order."""
    ordered = []
    for run in d['runs']:
        clock = run.get('time_evidence')
        if not clock:
            raise ValueError(f"时间证据不足：run {run['observer_run_id']} 缺少稳定的接收UTC范围；从原记录在新路径重建，不重置已使用测试记录。")
        if not clock['clock_consistent']:
            raise ValueError(f"时间证据冲突：run {run['observer_run_id']} 接收UTC与单调历时不一致；请核对时钟，不用它证明跨run未来留出。")
        start, end = utc_seconds(clock['first_utc']), utc_seconds(clock['last_utc'])
        if end < start:
            raise ValueError('run receive time range is reversed')
        ordered.append((start, end, run))
    ordered.sort(key=lambda x: (x[0], x[1]))
    episodes, first_run = [], {}
    previous = None
    for start, end, run in ordered:
        ep = run['episode']
        if previous and start <= previous[1]:
            raise ValueError(f"跨run时间范围交错：{previous[2]['observer_run_id']} [{previous[2]['time_evidence']['first_utc']}, {previous[2]['time_evidence']['last_utc']}] 与 {run['observer_run_id']} [{run['time_evidence']['first_utc']}, {run['time_evidence']['last_utc']}]；请确认时间和分组。")
        if not episodes or episodes[-1] != ep:
            if ep in first_run:
                old = first_run[ep]
                raise ValueError(f"非连续过程分组冲突：episode {ep}，run {old['observer_run_id']} [{old['time_evidence']['first_utc']}, {old['time_evidence']['last_utc']}] 后又出现 run {run['observer_run_id']} [{run['time_evidence']['first_utc']}, {run['time_evidence']['last_utc']}]；请确认分组，不自动改名或删段。")
            episodes.append(ep)
            first_run[ep] = run
        previous = (start, end, run)
    return ordered, episodes


def wall_support(row, runs):
    clock = runs[row['run_id']]['time_evidence']
    anchor = utc_seconds(clock['first_utc']) - clock['first_mono_s']
    return anchor + row['support_start'], anchor + row['support_end']


def freeze_split(runs, output, exploratory=False):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    d = build_dataset(runs)
    rows = d['rows']
    episodes = []
    if exploratory and len(d['runs']) == 1:
        ordered, episodes = [], [d['runs'][0]['episode']]
    else:
        ordered, episodes = chronological_runs(d)
    for _, _, m in ordered:
        if not m.get('episode_evidence') and not d['simulated'] and not exploratory:
            raise ValueError('episode independence unknown: provide --episode during recording, or use --exploratory')
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
    if scope == 'chronological_episodes':
        run_map = {r['observer_run_id']: r for r in d['runs']}
        episode_part = {r['episode']: mapping[r['id']] for r in rows}
        cuts = [(previous[1] + following[0]) / 2 for previous, following in zip(ordered, ordered[1:]) if episode_part.get(previous[2]['episode']) != episode_part.get(following[2]['episode'])]
        for r in rows:
            start, end = wall_support(r, run_map)
            if any(start <= cut <= end for cut in cuts):
                mapping.pop(r['id'], None)
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
    # Reconstruct order independently of the supplied (possibly old) split list.
    if s['scope'] == 'same_thermal_process_time_extrapolation':
        if len(d['runs']) != 1:
            raise ValueError('single-process exploratory scope requires exactly one run')
        ordered, order = [], [d['runs'][0]['episode']]
    elif s['scope'] == 'chronological_episodes':
        ordered, order = chronological_runs(d)
    else:
        raise ValueError('unsupported split scope')
    if s['episodes_order'] != order:
        raise ValueError('episode order does not match complete run chronology')
    run_map = {r['observer_run_id']: r for r in d['runs']}
    for r in d['rows']:
        if r['run_id'] not in run_map or r['episode'] != run_map[r['run_id']]['episode']:
            raise ValueError('row episode differs from its run grouping')
    episode_parts = {}
    for part, ids in s['partitions'].items():
        for id_ in ids:
            episode_parts.setdefault(byid[id_]['episode'], set()).add(part)
    if s['scope'] == 'chronological_episodes':
        if any(len(p) != 1 for p in episode_parts.values()):
            raise ValueError('episode split across partitions')
        sequence = [parts.index(next(iter(episode_parts[r['episode']]))) for _, _, r in ordered if r['episode'] in episode_parts]
        if sequence != sorted(sequence):
            raise ValueError('episodes not chronological')
        global_support = {part: [wall_support(byid[id_], run_map) for id_ in s['partitions'][part]] for part in parts}
        for earlier, later in zip(parts, parts[1:]):
            if max(end for _, end in global_support[earlier]) >= min(start for start, _ in global_support[later]):
                raise ValueError('cross-run raw temporal support overlap or nonchronological split')
    return byid
