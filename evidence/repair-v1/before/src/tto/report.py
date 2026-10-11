"""Escaped, self-contained reports; no external scripts, fonts or telemetry."""
import html
import json
from pathlib import Path
from .dataset import replay
from .evaluation import percentile
from .util import read_json, write_json

STYLE = 'body{font-family:system-ui,sans-serif;max-width:1120px;margin:36px auto;padding:0 22px;color:#223029;background:#f6f8f5;line-height:1.7}h1,h2{line-height:1.3}.notice{padding:18px;background:#fff0c9;border-left:5px solid #b36c05}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #d4ddd6;padding:8px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0eb;padding:18px}svg{width:100%;height:auto;background:white}.good{color:#146944}details{margin:16px 0}'


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
    return {'schema_version': 1, 'simulated': m['simulated'], 'conclusion': conclusion, 'deployment_status': m['deployment_status'], 'connection_reliable': 'simulation_only' if m['simulated'] else ('needs_review' if any(q.get(k, 0) for k in ('identity_conflict', 'sequence_regression', 'unsupported_schema', 'stale_or_missing_tj')) or summary.get('dropped') else ('observed_samples_only' if source_usable else 'unavailable')), 'quality': q, 'new_samples': q.get('new_samples', 0), 'duplicate_received': q.get('duplicate', 0), 'origin_count': len(rows), 'normal_auto_origins': normal, 'warm_origins': sum(r['history_ready'] for r in rows), 'label_counts': {str(h): sum(str(h) in r['labels'] for r in rows) for h in (15, 45, 90)}, 'episode': m['episode'], 'episode_evidence': m.get('episode_evidence'), 'independent_episode_count': 'unknown_until_operator_groups_complete_processes', 'availability': availability, 'resource': resource, 'host_scope': 'current_host_only_not_N305', 'poll_missed': summary.get('poll_missed'), 'dropped': summary.get('dropped'), 'observation_rate_hz': summary.get('observations', 0) / summary['elapsed_s'] if summary.get('elapsed_s') else None, 'orin_event_rate_hz': summary.get('orin_event_count', 0) / summary['elapsed_s'] if summary.get('elapsed_s') else None, 'business_payload_bytes': {'maximum': summary.get('business_payload_bytes_max'), 'mean': summary.get('business_payload_bytes_sum', 0) / summary['orin_event_count'] if summary.get('orin_event_count') else None}, 'asynchronous_control_temperature_differences': {'count': len(differences), 'max_absolute_c': max(abs(x['tj_minus_control_c']) for x in differences) if differences else None, 'first': differences[0] if differences else None, 'last': differences[-1] if differences else None, 'note': '异步量化与绑定路径有差别；不据此自动判错误或改绑。'}, 'source_status': result['processing'], 'stop_reason': summary.get('stop_reason'), 'next_step': '由用户填写本机端点并运行180秒只读doctor；确认最终部署身份后，记录正常完整热过程。', 'time_axis_note': '接收时间近似；源年龄是下界，不含未测网络在途时间。'}


def run_report(run, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    r = summarize(run)
    write_json(out / 'report.json', r)
    md = f"# TTO 记录报告\n\n{r['conclusion']}\n\n连接：{r['connection_reliable']}。部署：{r['deployment_status']}。\n\n有效新测量 {r['new_samples']}；重复接收 {r['duplicate_received']}；预测起点 {r['origin_count']}；正常 AUTO 起点 {r['normal_auto_origins']}。\n\n预测效果：待真实时间隔离评估。\n\n下一步：{r['next_step']}\n\n{r['time_axis_note']}\n\n资源只代表当前运行主机，目标 N305 待测。技术明细见 report.json。\n"
    (out / 'report.md').write_text(md, encoding='utf-8')
    body = '<p class="notice">' + html.escape(r['conclusion']) + '</p><h2>连接与数据</h2>' + table(['项目', '结果'], [('连接', r['connection_reliable']), ('部署核对', r['deployment_status']), ('有效新测量', r['new_samples']), ('重复缓存', r['duplicate_received']), ('正常AUTO起点', r['normal_auto_origins'])]) + '<h2>预测效果</h2><p>待真实时间隔离评估。采集成功不代表模型有价值。</p><h2>下一步</h2><p>' + html.escape(r['next_step']) + '</p><details><summary>数据质量、覆盖和资源明细</summary><pre>' + html.escape(json.dumps(r, ensure_ascii=False, indent=2)) + '</pre></details>'
    (out / 'report.html').write_text(html_page('TTO 模拟记录报告' if r['simulated'] else 'TTO 记录报告', body), encoding='utf-8')
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


def evaluation_report(result, points, out):
    out = Path(out)
    rows = []
    for h in ('15', '45', '90'):
        for name, m in result['same_origin_metrics'][h].items():
            macro = m['episode_equal_macro']
            rows.append([h, name, m['time_pooled']['n'], f"{macro.get('mae', float('nan')):.4f}", f"{macro.get('under_p95', float('nan')):.4f}", f"{macro.get('under_max', float('nan')):.4f}"])
    title = 'TTO 模拟评估报告' if result['simulated'] else 'TTO 时间隔离评估报告'
    body = '<p class="notice">' + html.escape(result['conclusion']) + '</p><p>' + html.escape(result['time_axis_note']) + '</p><h2>相同起点、相同标签的比较</h2>' + table(['时距s', '方法', '可评分', 'episode等权MAE°C', '欠预测P95°C', '欠预测最大值宏平均°C'], rows) + '<h2>45秒片段：预测按目标时刻对齐</h2>' + plot_predictions(points) + '<p>这是局部片段；完整数值、覆盖率、最差反例和原始引用在JSON中。</p><details><summary>完整评估证据</summary><pre>' + html.escape(json.dumps(result, ensure_ascii=False, indent=2)) + '</pre></details><p>预测准确性不证明能够降低PWM；没有控制输出。</p>'
    (out / 'report.html').write_text(html_page(title, body), encoding='utf-8')
    md = '# ' + title + '\n\n' + result['conclusion'] + '\n\n' + result['time_axis_note'] + '\n\n|时距s|方法|共同评分数|宏平均MAE C|欠预测P95 C|欠预测最大宏平均 C|\n|---|---|---|---|---|---|\n'
    md += ''.join('|' + '|'.join(map(str, row)) + '|\n' for row in rows)
    md += '\n全量、每过程、相同起点、覆盖率、阶段诊断、成功与最差片段、原始引用见 evaluation.json；逐次预测见 predictions.jsonl。\n\n固件趋势仅作诊断。相邻行不视为独立实验，没有置信百分比，没有降噪或调速结论。\n'
    (out / 'report.md').write_text(md, encoding='utf-8')
