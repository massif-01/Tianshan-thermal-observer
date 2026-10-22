import math
from collections import Counter
from pathlib import Path
from .dataset import check_split, load_dataset
from .model import HORIZONS, infer, load_model
from .util import finite, read_json, seal, write_json

METHODS = ('persist', 'trend30', 'ridge_tj', 'ridge_full')


def percentile(a, p):
    if not a:
        return None
    a = sorted(a)
    f = (len(a) - 1) * p
    i = int(f)
    return a[i] + (a[min(i + 1, len(a) - 1)] - a[i]) * (f - i)


def metrics(errors):
    if not errors:
        return {'n': 0, 'status': 'not_covered'}
    n = len(errors)
    under, over = [max(-e, 0) for e in errors], [max(e, 0) for e in errors]
    return {'n': n, 'mae': sum(abs(e) for e in errors) / n, 'rmse': math.sqrt(sum(e * e for e in errors) / n), 'abs_error_p95': percentile([abs(e) for e in errors], .95), 'bias_mean': sum(errors) / n, 'under_p95': percentile(under, .95), 'under_max': max(under), 'over_p95': percentile(over, .95), 'over_max': max(over)}


def group_metrics(points):
    by_episode = {}
    for p in points:
        by_episode.setdefault(p['episode'], []).append(p['error'])
    per = {e: metrics(v) for e, v in by_episode.items()}
    keys = ('mae', 'rmse', 'abs_error_p95', 'bias_mean', 'under_p95', 'under_max', 'over_p95', 'over_max')
    macro = {k: sum(v[k] for v in per.values()) / len(per) for k in keys} if per else {'status': 'not_covered'}
    weights = [p.get('time_weight_s', 5) for p in points]
    total = sum(weights)
    weighted = {'mae': sum(abs(p['error']) * w for p, w in zip(points, weights)) / total, 'rmse': math.sqrt(sum(p['error'] ** 2 * w for p, w in zip(points, weights)) / total), 'bias_mean': sum(p['error'] * w for p, w in zip(points, weights)) / total} if total else {'status': 'not_covered'}
    return {'time_pooled': metrics([p['error'] for p in points]), 'time_weighted': weighted, 'episodes': per, 'episode_equal_macro': macro}


def value_conclusion(d, s, rows, common_tables, intersection, points):
    if d['simulated']:
        return '模拟演示：仅验证软件正确性，不代表实机收益。'
    if any(r['deployment_status'] == 'deployment_unverified' for r in d['runs']):
        return '证据不足：最终部署身份未核对；本次只作探索性预测比较。'
    if s['scope'] != 'chronological_episodes' or not intersection['45'] or len({r['episode'] for r in rows}) < 2:
        return '证据不足：缺少足够未使用的独立测试过程或共同可评分起点。'
    active = {m: [p['error'] for p in points['45'][m] if p['common'] and p['phase'] != 'stable'] for m in METHODS}
    if not all(active.values()):
        return '证据不足：共同测试起点尚未覆盖升温或回落，不能用待机成绩证明新增价值。'
    macro = common_tables['45']
    vals = {m: macro[m]['episode_equal_macro']['mae'] for m in METHODS}
    active_mae = {m: metrics(v)['mae'] for m, v in active.items()}
    def wins(name, baselines):
        per = macro[name]['episodes']
        return sum(all(per[e]['mae'] < macro[m]['episodes'][e]['mae'] for m in baselines) for e in per)
    if vals['ridge_full'] < min(vals[m] for m in ('persist', 'trend30', 'ridge_tj')) and wins('ridge_full', ('persist', 'trend30', 'ridge_tj')) >= 2 and active_mae['ridge_full'] < min(active_mae[m] for m in ('persist', 'trend30', 'ridge_tj')):
        return '有初步新增价值；覆盖代价与欠预测风险仍需人工核对。'
    if vals['ridge_tj'] < min(vals[m] for m in ('persist', 'trend30')) and wins('ridge_tj', ('persist', 'trend30')) >= 2 and active_mae['ridge_tj'] < min(active_mae[m] for m in ('persist', 'trend30')):
        return '只证明小模型有初步价值，未证明更多输入有用。'
    return '暂未证明稳定新增价值；保留采集和基线，不自动扩大搜索。'


def evaluate(dataset_path, split_path, model_path, output):
    d, s = load_dataset(dataset_path), read_json(split_path)
    byid = check_split(d, s)
    model = load_model(model_path) if model_path else None
    if model and (model['split_sha256'] != s['sha256'] or model['dataset_sha256'] != d['sha256']):
        raise ValueError('model provenance differs from frozen split/dataset')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    ledger = Path(split_path).parent / 'test-used.json'
    # Reserve test usage before reading outcomes. Failed evaluation cannot silently reuse it.
    write_json(ledger, {'status': 'test_consumed', 'dataset_sha256': d['sha256'], 'split_sha256': s['sha256'], 'model_sha256': model['sha256'] if model else None, 'output': out.name, 'note': 'tuning after this evaluation requires unused test processes'})
    rows = [byid[i] for i in s['partitions']['test']]
    coverage = {str(h): {m: Counter(planned=len(rows)) for m in METHODS} for h in HORIZONS}
    predictions, points = [], {str(h): {m: [] for m in METHODS} for h in HORIZONS}
    intersection = {str(h): [] for h in HORIZONS}
    availability_by_origin = {}
    for r in rows:
        values = dict(r['baseline_values'])
        reasons = {}
        for name in ('ridge_tj', 'ridge_full'):
            if model and r['normal_auto']:
                p, reason, outside = infer(model, name, r['features'])
                if p:
                    values[name] = p
                else:
                    reasons[name] = reason
            else:
                reasons[name] = 'model_or_normal_scope_unavailable'
        availability_by_origin[r['id']] = set(values)
        for h in HORIZONS:
            k = str(h)
            label = r['labels'].get(k)
            common = label is not None and r['normal_auto'] and all(m in values for m in METHODS)
            if common:
                intersection[k].append(r['id'])
            for name in METHODS:
                c = coverage[k][name]
                c['input_available'] += int(r['features'].get('tj') is not None)
                c['normal_auto'] += int(r['normal_auto'])
                c['warming_up'] += int(name.startswith('ridge') and not r['history_ready'])
                c['output'] += int(name in values)
                c['fallback'] += int(name.startswith('ridge') and name not in values and bool(values))
                c['no_future_label'] += int(not label)
                c['cross_segment'] += int(r['label_status'].get(k) == 'cross_segment')
                if name in values and label and r['normal_auto']:
                    c['scorable'] += 1
                    error = values[name][k] - label['value']
                    p = {'id': r['id'], 'episode': r['episode'], 'run_id': r['run_id'], 'segment': r['segment'], 'origin_t': r['t'], 'target_t': r['t'] + h, 'label_t': label['t'], 'label_ref': label['ref'], 'origin_ref': r['ref'], 'raw_refs': r['raw_refs'], 'horizon_s': h, 'method': name, 'prediction': values[name][k], 'truth': label['value'], 'error': error, 'common': common, 'phase': r['phase'], 'high_temperature': r['high_temperature'], 'time_weight_s': 5}
                    points[k][name].append(p)
                    predictions.append(p)
    tables, common_tables, phases, time_groups, episode_coverage = {}, {}, {}, {}, {}
    for h in HORIZONS:
        k = str(h)
        tables[k] = {m: group_metrics(points[k][m]) for m in METHODS}
        common_tables[k] = {m: group_metrics([p for p in points[k][m] if p['common']]) for m in METHODS}
        phases[k] = {m: {phase: metrics([p['error'] for p in points[k][m] if (p['phase'] == phase if phase != 'higher_temperature' else p['high_temperature'])]) for phase in ('stable', 'warming', 'cooling', 'rewarming', 'higher_temperature')} for m in METHODS}
        time_groups[k] = {}
        for m in METHODS:
            bins = {}
            for p in points[k][m]:
                bins.setdefault(f"{p['run_id']}:{int(p['origin_t'] // 300)}", []).append(p['error'])
            time_groups[k][m] = {b: metrics(e) for b, e in bins.items()}
        episode_coverage[k] = {e: {'planned': sum(r['episode'] == e for r in rows), **{m: sum(p['episode'] == e for p in points[k][m]) for m in METHODS}} for e in sorted({r['episode'] for r in rows})}
    def subset_coverage(subset, h, method):
        k = str(h)
        available = lambda r: method in availability_by_origin[r['id']]
        return {'planned': len(subset), 'input_available': sum(r['features'].get('tj') is not None for r in subset), 'normal_auto': sum(r['normal_auto'] for r in subset), 'warming_up': sum(method.startswith('ridge') and not r['history_ready'] for r in subset), 'output': sum(available(r) for r in subset), 'fallback': sum(method.startswith('ridge') and not available(r) for r in subset), 'no_future_label': sum(k not in r['labels'] for r in subset), 'cross_segment': sum(r['label_status'].get(k) == 'cross_segment' for r in subset), 'scorable': sum(available(r) and k in r['labels'] and r['normal_auto'] for r in subset)}
    time_coverage = {}
    for h in HORIZONS:
        k = str(h)
        episode_coverage[k] = {e: {m: subset_coverage([r for r in rows if r['episode'] == e], h, m) for m in METHODS} for e in sorted({r['episode'] for r in rows})}
        grouped = {}
        for r in rows:
            grouped.setdefault(f"{r['run_id']}:{int(r['t'] // 300)}", []).append(r)
        time_coverage[k] = {b: {m: subset_coverage(group, h, m) for m in METHODS} for b, group in grouped.items()}
    ranked = sorted(predictions, key=lambda p: abs(p['error']))
    conclusion = value_conclusion(d, s, rows, common_tables, intersection, points)
    result = seal({'schema_version': 1, 'simulated': d['simulated'], 'conclusion': conclusion, 'time_axis_note': '接收时间近似，不是硬件采样时刻；未测网络延迟不解释为热滞后。', 'dataset_sha256': d['sha256'], 'split_sha256': s['sha256'], 'model_sha256': model['sha256'] if model else None, 'coverage': {k: {m: dict(v) for m, v in group.items()} for k, group in coverage.items()}, 'episode_coverage': episode_coverage, 'time_coverage': time_coverage, 'all_available_metrics': tables, 'same_origin_intersection_count': {k: len(v) for k, v in intersection.items()}, 'same_origin_metrics': common_tables, 'phase_diagnostics': phases, 'time_bin_diagnostics': time_groups, 'success_examples': ranked[:3], 'worst_examples': ranked[-3:], 'abnormal_origins': sum(not r['normal_auto'] for r in rows), 'firmware_trend_note': '45秒固件趋势仅作诊断，不作训练标签，不判断可减少PWM。', 'firmware_45s_diagnostics': [{'id': r['id'], 'origin_ref': r['ref'], 'prediction': r['firmware_45s_diagnostic'], 'truth': r['labels']['45']['value'], 'error': r['firmware_45s_diagnostic'] - r['labels']['45']['value']} for r in rows if r['normal_auto'] and finite(r['firmware_45s_diagnostic']) and '45' in r['labels']], 'deployment_provenance': d['runs'], 'no_confidence_percentage': True})
    write_json(out / 'evaluation.json', result)
    with (out / 'predictions.jsonl').open('x') as f:
        from .util import canonical
        for p in predictions:
            f.write(canonical(p).decode() + '\n')
    from .report import evaluation_report
    evaluation_report(result, predictions, out)
    return result
