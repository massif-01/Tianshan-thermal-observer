import math
from collections import Counter
from pathlib import Path
from .dataset import check_split, load_dataset
from .model import HORIZONS, infer, load_model, eligible_scope, model_dataset_match
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


LAYERS = {'baseline': ('persist', 'trend30'), 'm0': ('persist', 'trend30', 'ridge_tj'), 'm1': METHODS}
PHASES = ('stable', 'warming', 'cooling', 'rewarming', 'higher_temperature')


def comparison_layers(rows, points):
    """Three nested same-origin, same-label cohorts; never compare across cohorts."""
    layers = {}
    for layer_name, methods in LAYERS.items():
        horizons = {}
        for h in HORIZONS:
            key = str(h)
            sets = [{p['id'] for p in points[key][m]} for m in methods]
            ids = set.intersection(*sets)
            selected = {m: [p for p in points[key][m] if p['id'] in ids] for m in methods}
            for m in methods:
                for p in selected[m]:
                    p.setdefault('comparison_layers', []).append(layer_name)
            phase_metrics = {}
            for phase in PHASES:
                subset = {m: [p for p in selected[m] if p['high_temperature']] for m in methods} if phase == 'higher_temperature' else {m: [p for p in selected[m] if p['phase'] == phase] for m in methods}
                phase_metrics[phase] = {'matched_count': len(subset[methods[0]]), 'metrics': {m: group_metrics(v) for m,v in subset.items()}}
            horizons[key] = {'planned_count': len(rows), 'matched_count': len(ids), 'coverage_fraction': len(ids)/len(rows) if rows else None, 'origin_ids': sorted(ids), 'metrics': {m: group_metrics(v) for m,v in selected.items()}, 'active_metrics': {m: group_metrics([p for p in v if p['phase'] != 'stable']) for m,v in selected.items()}, 'phase_diagnostics': phase_metrics, 'episodes': {e: {'planned_count': sum(r['episode']==e for r in rows), 'matched_count': sum(p['episode']==e for p in selected[methods[0]])} for e in sorted({r['episode'] for r in rows})}}
        layers[layer_name] = {'methods': list(methods), 'horizons': horizons}
    return layers


def layer_judgements(d, s, rows, comparisons):
    precondition = None
    if d['simulated']:
        precondition = '模拟演示：本层只验证计算，真实价值待数据。'
    elif any(r['deployment_status'] == 'deployment_unverified' for r in d['runs']):
        precondition = '证据不足：最终部署身份未核对。'
    elif s['scope'] != 'chronological_episodes' or len({r['episode'] for r in rows}) < 2:
        precondition = '证据不足：缺少足够未使用的独立测试过程。'
    out = {'baseline': {'status': 'descriptive', 'message': '基线层使用B0/B1共同起点；只在本层内比较。'}}
    for layer, target, baselines in (('m0','ridge_tj',('persist','trend30')),('m1','ridge_full',('persist','trend30','ridge_tj'))):
        data = comparisons[layer]['horizons']['45']
        metrics_ = data['metrics']
        if precondition:
            out[layer] = {'status': 'simulation' if d['simulated'] else 'evidence_insufficient', 'message': precondition}
            continue
        if data['matched_count'] == 0 or len(metrics_[target]['episodes']) < 2:
            out[layer] = {'status': 'evidence_insufficient', 'message': f'证据不足：{layer.upper()}层缺少共同可评分起点或两个独立测试过程。'}
            continue
        active = data['active_metrics']
        if any(active[m]['time_pooled']['n'] == 0 for m in (target, *baselines)):
            out[layer] = {'status': 'evidence_insufficient', 'message': f'证据不足：{layer.upper()}层未覆盖升温或回落，不能以待机证明新增价值。'}
            continue
        mae = {m: metrics_[m]['episode_equal_macro']['mae'] for m in (target,*baselines)}
        wins = sum(all(ep['mae'] < metrics_[m]['episodes'][e]['mae'] for m in baselines) for e,ep in metrics_[target]['episodes'].items())
        better = mae[target] < min(mae[m] for m in baselines) and wins >= 2 and active[target]['time_pooled']['mae'] < min(active[m]['time_pooled']['mae'] for m in baselines)
        out[layer] = {'status': 'initial_value' if better else 'not_proven', 'message': f'{layer.upper()}在本层有初步新增价值；覆盖代价与欠预测风险仍需核对。' if better else f'暂未证明{layer.upper()}在本层稳定增加价值；不自动扩大搜索。'}
    return out


def value_conclusion(d, s, rows, comparisons):
    if d['simulated']:
        return '模拟演示：仅验证软件正确性，不代表实机收益。'
    judgements = layer_judgements(d,s,rows,comparisons)
    if judgements['m1']['status'] == 'initial_value':
        return '有初步新增价值：M1层内比较胜出；覆盖代价与欠预测风险仍需人工核对。'
    if judgements['m0']['status'] == 'initial_value':
        return '小模型M0有初步价值（M0层内对照）；M1尚未证明更多输入有用：' + judgements['m1']['message']
    if judgements['m0']['status'] == 'not_proven':
        return judgements['m0']['message'] + ' ' + judgements['m1']['message']
    baseline = comparisons['baseline']['horizons']['45']['matched_count']
    return ('基线层已有可读结果；' if baseline else '') + judgements['m0']['message'] + ' ' + judgements['m1']['message']


def evaluate(dataset_path, split_path, model_path, output):
    d, s = load_dataset(dataset_path), read_json(split_path)
    byid = check_split(d, s)
    model = load_model(model_path) if model_path else None
    if model:
        model_dataset_match(model, d)
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
    unavailable = {}
    for r in rows:
        values = dict(r['baseline_values'])
        reasons = {}
        for name in ('ridge_tj', 'ridge_full'):
            if model and eligible_scope(r):
                if d['schema_version'] == 2:
                    from .profiles import compatible_contract
                    if not compatible_contract(model['input_contract'], r.get('input_contract'), 'gpu_busy' in model['methods'][name]['columns']):
                        reasons[name] = 'model_input_contract_mismatch'
                        continue
                p, reason, outside = infer(model, name, r['features'])
                if p:
                    values[name] = p
                else:
                    reasons[name] = reason
            else:
                reasons[name] = 'model_or_normal_scope_unavailable'
        availability_by_origin[r['id']] = set(values)
        unavailable[r['id']] = {'ref': r['ref'], 'method_reasons': reasons}
        for h in HORIZONS:
            k = str(h)
            label = r['labels'].get(k)
            common = label is not None and eligible_scope(r) and all(m in values for m in METHODS)
            if common:
                intersection[k].append(r['id'])
            for name in METHODS:
                c = coverage[k][name]
                c['input_available'] += int(r['features'].get('tj') is not None)
                c['normal_auto'] += int(r['normal_auto'])
                if d['schema_version'] == 2:
                    c['control_eligible'] += int(eligible_scope(r))
                c['warming_up'] += int(name.startswith('ridge') and not r['history_ready'])
                c['output'] += int(name in values)
                c['fallback'] += int(name.startswith('ridge') and name not in values and bool(values))
                c['no_future_label'] += int(not label)
                c['cross_segment'] += int(r['label_status'].get(k) == 'cross_segment')
                if name in values and label and eligible_scope(r):
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
        return {'planned': len(subset), 'input_available': sum(r['features'].get('tj') is not None for r in subset), 'normal_auto': sum(eligible_scope(r) for r in subset), 'warming_up': sum(method.startswith('ridge') and not r['history_ready'] for r in subset), 'output': sum(available(r) for r in subset), 'fallback': sum(method.startswith('ridge') and not available(r) for r in subset), 'no_future_label': sum(k not in r['labels'] for r in subset), 'cross_segment': sum(r['label_status'].get(k) == 'cross_segment' for r in subset), 'scorable': sum(available(r) and k in r['labels'] and eligible_scope(r) for r in subset)}
    time_coverage = {}
    for h in HORIZONS:
        k = str(h)
        episode_coverage[k] = {e: {m: subset_coverage([r for r in rows if r['episode'] == e], h, m) for m in METHODS} for e in sorted({r['episode'] for r in rows})}
        grouped = {}
        for r in rows:
            grouped.setdefault(f"{r['run_id']}:{int(r['t'] // 300)}", []).append(r)
        time_coverage[k] = {b: {m: subset_coverage(group, h, m) for m in METHODS} for b, group in grouped.items()}
    ranked = sorted(predictions, key=lambda p: abs(p['error']))
    comparisons = comparison_layers(rows, points)
    judgements = layer_judgements(d, s, rows, comparisons)
    conclusion = value_conclusion(d, s, rows, comparisons)
    result = seal({'schema_version': d['schema_version'], 'feature_profile_id': d.get('feature_profile_id'), 'control_scope': d.get('control_scope'), 'report_type': 'holdout_evaluation', 'comparison_contract': 'TTO-REPAIR-v1.0-layered-v1', 'comparisons': comparisons, 'comparison_judgements': judgements, 'unavailable_methods': unavailable, 'simulated': d['simulated'], 'conclusion': conclusion, 'time_axis_note': '接收时间近似，不是硬件采样时刻；未测网络延迟不解释为热滞后。', 'dataset_sha256': d['sha256'], 'split_sha256': s['sha256'], 'model_sha256': model['sha256'] if model else None, 'coverage': {k: {m: dict(v) for m, v in group.items()} for k, group in coverage.items()}, 'episode_coverage': episode_coverage, 'time_coverage': time_coverage, 'all_available_metrics': tables, 'same_origin_intersection_count': {k: len(v) for k, v in intersection.items()}, 'same_origin_metrics': common_tables, 'phase_diagnostics': phases, 'time_bin_diagnostics': time_groups, 'success_examples': ranked[:3], 'worst_examples': ranked[-3:], 'abnormal_origins': sum(not eligible_scope(r) for r in rows), 'firmware_trend_note': '45秒固件趋势仅作诊断，不作训练标签，不判断可减少PWM。', 'firmware_45s_diagnostics': [{'id': r['id'], 'origin_ref': r['ref'], 'prediction': r['firmware_45s_diagnostic'], 'truth': r['labels']['45']['value'], 'error': r['firmware_45s_diagnostic'] - r['labels']['45']['value']} for r in rows if eligible_scope(r) and finite(r['firmware_45s_diagnostic']) and '45' in r['labels']], 'deployment_provenance': d['runs'], 'no_confidence_percentage': True})
    write_json(out / 'evaluation.json', result)
    with (out / 'predictions.jsonl').open('x') as f:
        from .util import canonical
        for p in predictions:
            f.write(canonical(p).decode() + '\n')
    from .report import evaluation_report
    evaluation_report(result, predictions, out)
    return result
