"""Escaped, self-contained reports; no external scripts, fonts or telemetry."""
import html
import json
from pathlib import Path
from .dataset import replay
from .evaluation import percentile
from .util import read_json, write_json
from .recorded import recorded_results

STYLE = 'body{font-family:system-ui,sans-serif;max-width:1120px;margin:36px auto;padding:0 22px;color:#223029;background:#f6f8f5;line-height:1.7}h1,h2{line-height:1.3}.notice{padding:18px;background:#fff0c9;border-left:5px solid #b36c05}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #d4ddd6;padding:8px;text-align:left;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0eb;padding:18px}svg{width:100%;height:auto;background:white}.good{color:#146944}details{margin:16px 0}'


def html_page(title, body):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'"><title>' + html.escape(title) + '</title><style>' + STYLE + '</style><body><h1>' + html.escape(title) + '</h1>' + body + '</body></html>'


def table(headers, rows):
    escape = lambda x: html.escape(str(x))
    return '<table><thead><tr>' + ''.join('<th>' + escape(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + escape(x) + '</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table>'


def summarize(run):
    run = Path(run)
    result = replay(run)
    m = result['manifest']
    summary = read_json(run / 'summary.json') if (run / 'summary.json').exists() else {'status': 'incomplete_run_after_interruption'}
    q = result['quality']
    rows = result['rows']
    resource = {}
    for field in ('rss_mib', 'cpu_pct_single_core', 'prediction_ms', 'poll_rtt_ms'):
        a = summary.get(field, [])
        resource[field] = {'count': len(a), 'max': max(a) if a else None, 'p95': percentile(a, .95), 'p99': percentile(a, .99), 'mean': sum(a) / len(a) if a else None}
    fields = sorted({k for r in rows for k in r['features']})
    availability = {field: sum(r['features'].get(field) is not None for r in rows) / len(rows) if rows else None for field in fields}
    normal = sum(r['normal_auto'] for r in rows)
    differences = [{'origin_ref': r['ref'], 't': r['t'], 'fan_ref': r['fan_diagnostics']['ref'], 'fan_age_s': r['fan_diagnostics']['fan_return_age_s'], 'tj_minus_control_c': r['features']['tj'] - r['fan_diagnostics']['control_temperature']} for r in rows if r.get('fan_diagnostics') and isinstance(r['fan_diagnostics'].get('control_temperature'), (int, float))]
    source_usable = q.get('new_samples', 0) > 0
    conclusion = '模拟演示：软件贯通，不代表实机连接或预测收益。' if m['simulated'] else ('软件可用，预测效果待验证。' if source_usable else '数据暂不可用，预测已暂停；核对端点、身份和新鲜度。')
    report = {'schema_version': 1, 'simulated': m['simulated'], 'conclusion': conclusion, 'deployment_status': m['deployment_status'], 'connection_reliable': 'simulation_only' if m['simulated'] else ('needs_review' if any(q.get(k, 0) for k in ('identity_conflict', 'sequence_regression', 'unsupported_schema', 'stale_or_missing_tj')) or summary.get('dropped') else ('observed_samples_only' if source_usable else 'unavailable')), 'quality': q, 'new_samples': q.get('new_samples', 0), 'duplicate_received': q.get('duplicate', 0), 'origin_count': len(rows), 'normal_auto_origins': normal, 'warm_origins': sum(r['history_ready'] for r in rows), 'label_counts': {str(h): sum(str(h) in r['labels'] for r in rows) for h in (15, 45, 90)}, 'episode': m['episode'], 'episode_evidence': m.get('episode_evidence'), 'independent_episode_count': 'unknown_until_operator_groups_complete_processes', 'availability': availability, 'resource': resource, 'host_scope': 'current_host_only_not_N305', 'poll_missed': summary.get('poll_missed'), 'dropped': summary.get('dropped'), 'observation_rate_hz': summary.get('observations', 0) / summary['elapsed_s'] if summary.get('elapsed_s') else None, 'orin_event_rate_hz': summary.get('orin_event_count', 0) / summary['elapsed_s'] if summary.get('elapsed_s') else None, 'business_payload_bytes': {'maximum': summary.get('business_payload_bytes_max'), 'mean': summary.get('business_payload_bytes_sum', 0) / summary['orin_event_count'] if summary.get('orin_event_count') else None}, 'asynchronous_control_temperature_differences': {'count': len(differences), 'max_absolute_c': max(abs(x['tj_minus_control_c']) for x in differences) if differences else None, 'first': differences[0] if differences else None, 'last': differences[-1] if differences else None, 'note': '异步量化与绑定路径有差别；不据此自动判错误或改绑。'}, 'source_status': result['processing'], 'stop_reason': summary.get('stop_reason'), 'next_step': '由用户填写本机端点并运行180秒只读doctor；确认最终部署身份后，记录正常完整热过程。', 'time_axis_note': '接收时间近似；源年龄是下界，不含未测网络在途时间。'}
    recorded, _ = recorded_results(run, m, result['quality_eligibility'])
    shadow = m.get('report_type') == 'shadow' or m.get('model_sha256') is not None or any(v['model_sha256'] is not None for v in recorded['models'].values())
    report['report_type'] = 'shadow' if shadow else 'collect'
    report['recorded_results'] = recorded
    required_missing = recorded['missing_logs'] if rows or recorded['issued_prediction_origins'] else []
    report['missing_required_logs'] = required_missing
    prefix = '模拟旁路：' if m['simulated'] else '本次旁路：'
    if shadow:
        report['known_model_sha256'] = m.get('model_sha256')
        if required_missing or recorded['issues']:
            report['conclusion'] = prefix + '证据缺失或无法关联：' + ', '.join(required_missing or sorted({x['reason'] for x in recorded['issues']})) + '；不能完整评价当时预测。'
            report['next_step'] = '保留现有记录并找回对应日志；不加载新模型回算历史预测。'
        elif not recorded['issued_prediction_origins']:
            report['conclusion'] = prefix + '未产生有效预测记录。'
            report['next_step'] = '核对有效新TJ、正常AUTO资格和预热状态；本次没有模型效果成绩。'
        elif recorded['quality_excluded_method_horizon_records'] and not recorded['scored_method_horizon_records']:
            report['conclusion'] = prefix + '历史评分已保存，但全部被既有质量隔离排除；当前没有可用成绩，误差不可计算。'
            report['next_step'] = '查看隔离原因与原始引用；保留历史记录，不重算预测或改写评分。'
        elif not recorded['scored_method_horizon_records']:
            report['conclusion'] = prefix + '已有已发预测，但尚未能评分；原因和等待状态见实际记录。'
            report['next_step'] = '查看未评分原因；若记录仍在进行，等待本轮未来标签，不改写已发预测。'
        elif not any(any(counts['methods'][method]['issued'] for counts in group['horizons'].values() for method in ('ridge_tj','ridge_full')) for group in recorded['models'].values()):
            report['conclusion'] = prefix + '本次只有基线，尚无可用模型输出；已保存基线评分。'
            report['next_step'] = '检查本地冻结模型与已保存缺项/预热原因；现有基线记录可继续复核。'
        else:
            report['conclusion'] = prefix + '已读取当时保存的模型预测与事后评分；这是该次在线观察，不是新独立留出验证。'
            report['next_step'] = '查看实际误差、覆盖和降级片段，再决定是否保留该冻结模型；不能据此降低PWM。'
        if recorded['quality_excluded_method_horizon_records'] and recorded['scored_method_horizon_records']:
            report['conclusion'] += f" 历史评分中{recorded['quality_excluded_method_horizon_records']}条因质量隔离排除，当前{recorded['scored_method_horizon_records']}条有效；误差和图只使用有效集合。"
        if m['simulated']:
            report['conclusion'] += ' 模拟记录仅验证软件，真实预测效果待数据。'
    else:
        if required_missing:
            report['conclusion'] += ' 预测/评分证据缺失：' + ', '.join(required_missing) + '。'
            report['next_step'] = '保留记录并找回缺失日志；质量回放不代表历史预测已经完整。'
        elif source_usable:
            report['next_step'] = '按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。'
    return report


def shadow_table_rows(recorded):
    rows = []
    for key, group in recorded['models'].items():
        for h, data in group['horizons'].items():
            for method, counts in data['methods'].items():
                if not counts['issued']:
                    continue
                pooled = counts['metrics']['time_pooled']
                val = lambda field: f"{pooled[field]:.4f}" if field in pooled else '未能评分'
                rows.append([key[:12]+'…' if group['model_sha256'] else '无模型基线', h, method, data['issued_origins'], counts['issued'], counts['historical_scored'] if counts['historical_scored'] is not None else '缺评分日志', counts['quality_excluded'] if counts['quality_excluded'] is not None else '未知', counts['scored'] if counts['scored'] is not None else '缺评分日志', f"{counts['coverage_fraction']:.1%}" if counts['coverage_fraction'] is not None else '缺评分证据', val('mae'),val('rmse'),val('abs_error_p95'),val('bias_mean'),val('under_p95'),val('under_max'),val('over_p95'),val('over_max')])
    return rows


def run_report(run, output):
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    r = summarize(run); write_json(out/'report.json',r)
    shadow = r['report_type']=='shadow'
    title = ('TTO 模拟旁路运行报告' if r['simulated'] else 'TTO 实际旁路运行报告') if shadow else ('TTO 模拟采集报告' if r['simulated'] else 'TTO 采集质量报告')
    md = '# '+title+'\n\n'+r['conclusion']+'\n\n下一步：'+r['next_step']+'\n\n'+r['time_axis_note']+'\n\n'
    body = '<p class="notice">'+html.escape(r['conclusion'])+'</p><h2>下一步</h2><p>'+html.escape(r['next_step'])+'</p><p>'+html.escape(r['time_axis_note'])+'</p>'
    connection_labels = {'simulation_only':'仅模拟，未连接设备','needs_review':'有质量缺口，请查看明细','observed_samples_only':'已收到新测量，完整可靠性仍需核对','unavailable':'暂无有效测量'}
    deployment_labels = {'deployment_unverified':'现场部署未核对','user_recorded_not_independently_verified':'用户已登记，尚未独立核对'}
    quality_rows = [('连接',connection_labels.get(r['connection_reliable'],'状态待核对，见明细')),('部署核对',deployment_labels.get(r['deployment_status'],'状态待核对，见明细')),('有效新测量',r['new_samples']),('重复缓存',r['duplicate_received']),('正常AUTO起点',r['normal_auto_origins'])]
    body += '<h2>采集质量</h2>'+table(['项目','结果'],quality_rows)
    md += '## 采集质量\n\n'+markdown_table(['项目','结果'],quality_rows)+'\n'
    if shadow:
        headers = ['当时模型SHA/基线','时距s','实际输出方法','计划起点','已发','历史评分','质量排除','当前有效','有效/计划起点','MAE C','RMSE C','绝对误差P95 C','偏差 C','欠预测P95 C','欠预测最大 C','过预测P95 C','过预测最大 C']
        rows = shadow_table_rows(r['recorded_results'])
        message = '数值来自本run的predictions.jsonl与scores.jsonl，按预测身份/时距/方法/模型关联；未加载当前模型重算。每方法覆盖单列，不拿不同集合的MAE判断优劣。有效评分使用生产质量回放的既有段隔离；覆盖率分子为当前有效评分，分母为当时计划起点（包含隔离段），已发预测分母另见JSON。'
        body += '<h2>当时实际发出的预测与评分</h2><p>'+html.escape(message)+'</p>'+table(headers,rows)
        md += '## 当时实际发出的预测与评分\n\n'+message+'\n\n'+markdown_table(headers,rows)+'\n'
        eligibility_summary = {k:r['recorded_results'][k] for k in ('issued_prediction_origins','terminal_score_records','historical_scored_method_horizon_records','scored_method_horizon_records','quality_excluded_method_horizon_records','log_evidence_complete','quality_isolations')}
        eligibility_text = json.dumps(eligibility_summary,ensure_ascii=False,indent=2)
        body += '<h2>历史记录与当前评价资格</h2><pre>'+html.escape(eligibility_text)+'</pre>'
        md += '## 历史记录与当前评价资格\n\n```json\n'+eligibility_text+'\n```\n'
        fallback = {key: {'model_sha256':g['model_sha256'],'actual_methods':g['actual_methods'],'fallback_origins':g['fallback_origins'],'unavailable_method_reasons':g['unavailable_method_reasons'],'unscored':{h:data['unscored_reasons'] for h,data in g['horizons'].items()}} for key,g in r['recorded_results']['models'].items()}
        body += '<h2>实际方法、降级与未评分原因</h2><pre>'+html.escape(json.dumps(fallback,ensure_ascii=False,indent=2))+'</pre>'+plot_predictions(r['recorded_results']['scored_records'])
        md += '## 实际方法、降级与未评分原因\n\n```json\n'+json.dumps(fallback,ensure_ascii=False,indent=2)+'\n```\n\n模型身份及每次预测/评分/原始观测引用见report.json；图按目标时刻对齐。\n'
    else:
        body += '<h2>模型价值</h2><p>本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。</p>'
        md += '本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。\n'
    body += '<details><summary>完整保存记录统计、原始引用及资源</summary><pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details>'
    (out/'report.html').write_text(html_page(title,body),encoding='utf-8')
    (out/'report.md').write_text(md,encoding='utf-8')
    return r


def plot_predictions(points):
    if not points:
        return '<p>没有可评分片段。</p>'
    # Plot a complete window in one run, with predictions located at target times.
    # A reduction here affects rendering only; full numerical evidence stays in JSONL.
    selected = [p for p in points if p['horizon_s'] == 45]
    if not selected:
        return '<p>45秒时距没有可评分片段。</p>'
    run_id = selected[0]['run_id']
    selected = [p for p in selected if p['run_id'] == run_id]
    lo = min(p['target_t'] for p in selected)
    selected = [p for p in selected if p['target_t'] <= lo + 300]
    hi = max(p['label_t'] for p in selected)
    ymin = min(min(p['prediction'], p['truth']) for p in selected) - 1
    ymax = max(max(p['prediction'], p['truth']) for p in selected) + 1
    sx = lambda t: 65 + 860 * (t - lo) / max(hi - lo, 1)
    sy = lambda t: 280 - 240 * (t - ymin) / max(ymax - ymin, 1)
    colors = {'persist': '#a2875d', 'trend30': '#9b5e98', 'ridge_tj': '#2f7d7b', 'ridge_full': '#183d87'}
    svg = '<svg viewBox="0 0 1000 355" role="img" aria-label="45秒预测按目标时刻对齐"><line x1="65" y1="280" x2="925" y2="280" stroke="#888"/>'
    for name, color in colors.items():
        pts = sorted([p for p in selected if p['method'] == name], key=lambda p: p['target_t'])
        if pts:
            coords = ' '.join(f'{sx(p["target_t"]):.2f},{sy(p["prediction"]):.2f}' for p in pts)
            svg += f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="{coords}"/>'
    truth = sorted({(p['label_t'], p['truth']) for p in selected})
    svg += '<polyline fill="none" stroke="#111" stroke-width="2" points="' + ' '.join(f'{sx(t):.2f},{sy(v):.2f}' for t, v in truth) + '"/>'
    svg += f'<text x="15" y="40">{ymax:.1f}°C</text><text x="15" y="280">{ymin:.1f}°C</text><text x="65" y="310">目标时刻 +0秒</text><text x="820" y="310">+{hi-lo:.0f}秒</text><text x="65" y="340">黑：TJ真值；棕：保持；紫：趋势；青：M0；蓝：M1</text></svg>'
    return svg


def comparison_table_rows(layer):
    rows = []
    for h in ('15', '45', '90'):
        data = layer['horizons'][h]
        for name, m in data['metrics'].items():
            macro = m['episode_equal_macro']
            number = lambda key: f"{macro[key]:.4f}" if key in macro else '未覆盖'
            rows.append([h, name, data['planned_count'], data['matched_count'], f"{data['coverage_fraction']:.1%}" if data['coverage_fraction'] is not None else '未覆盖', number('mae'), number('under_p95'), number('under_max')])
    return rows


def markdown_table(headers, rows):
    escape = lambda x: str(x).replace('|', '\\|').replace('\n', ' ')
    return '|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(escape(x) for x in row)+'|\n' for row in rows)


def evaluation_report(result, points, out):
    out = Path(out)
    title = 'TTO 模拟评估报告' if result['simulated'] else 'TTO 时间隔离评估报告'
    note = '每层内部使用相同起点、相同标签；不同层MAE不能直接比较模型优劣。M1缺项不阻挡M0层。'
    body = '<p class="notice">'+html.escape(result['conclusion'])+'</p><p>'+html.escape(note)+'</p><p>'+html.escape(result['time_axis_note'])+'</p>'
    md = '# '+title+'\n\n'+result['conclusion']+'\n\n'+note+'\n\n'+result['time_axis_note']+'\n\n'
    headers = ['时距s','方法','计划起点','共同评分','覆盖率','episode等权MAE C','欠预测P95 C','欠预测最大宏平均 C']
    for key,label in (('baseline','基线层 B0/B1'),('m0','M0层 B0/B1/M0'),('m1','M1层 B0/B1/M0/M1')):
        rows = comparison_table_rows(result['comparisons'][key])
        message = result['comparison_judgements'][key]['message']
        body += '<h2>'+html.escape(label)+'</h2><p>'+html.escape(message)+'</p>'+table(headers,rows)
        md += '## '+label+'\n\n'+message+'\n\n'+markdown_table(headers,rows)+'\n'
        primary = result['comparisons'][key]['horizons']['45']
        episode_rows = [[ep, method, counts['planned_count'], counts['matched_count'], f"{primary['metrics'][method]['episodes'][ep]['mae']:.4f}" if ep in primary['metrics'][method]['episodes'] else '未覆盖'] for ep,counts in primary['episodes'].items() for method in result['comparisons'][key]['methods']]
        phase_rows = [[phase, method, facts['matched_count'], f"{facts['metrics'][method]['time_pooled']['mae']:.4f}" if facts['metrics'][method]['time_pooled']['n'] else '未覆盖'] for phase,facts in primary['phase_diagnostics'].items() for method in result['comparisons'][key]['methods']]
        body += '<h3>45秒：各过程</h3>'+table(['过程','方法','计划','共同评分','MAE C'],episode_rows)+'<h3>45秒：各阶段</h3>'+table(['阶段','方法','共同评分','MAE C'],phase_rows)
        md += '### 45秒：各过程\n\n'+markdown_table(['过程','方法','计划','共同评分','MAE C'],episode_rows)+'\n### 45秒：各阶段\n\n'+markdown_table(['阶段','方法','共同评分','MAE C'],phase_rows)+'\n'

    body += '<h2>45秒片段：预测按目标时刻对齐</h2>'+plot_predictions(points)+'<p>局部片段只展示预测，正式优劣使用上方分层共同集合。</p><details><summary>过程、阶段、覆盖、缺项与完整证据</summary><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></details><p>预测准确性不证明能够降低PWM；没有控制输出。</p>'
    (out/'report.html').write_text(html_page(title,body),encoding='utf-8')
    md += '每层的过程/阶段明细、全量方法覆盖与不可用原因见evaluation.json；逐次原始引用见predictions.jsonl。固件趋势仅作诊断。相邻行不是独立实验，没有置信百分比或调速结论。\n'
    (out/'report.md').write_text(md,encoding='utf-8')
