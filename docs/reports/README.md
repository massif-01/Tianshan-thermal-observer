# 实机采集报告

报告记录具体设备、软件版本和当轮工况的实测结果，不代表跨设备性能承诺。工况时间的来源、数据异常及统计边界以各报告为准。

| 日期 | 设备与采集 | 报告 | 图表 | 数据与操作记录 |
|---|---|---|---|---|
| 2026-10-13 | RM-01 Thor，第二轮七工况，42分16秒连续采集 | [分析报告](2026-10-13-thor-seven-conditions-round2/analysis-report.md) | [PNG](2026-10-13-thor-seven-conditions-round2/condition-timeline.png) · [SVG](2026-10-13-thor-seven-conditions-round2/condition-timeline.svg) | [完整归档](2026-10-13-thor-seven-conditions-round2/data-and-analysis.zip) · [工况统计CSV](2026-10-13-thor-seven-conditions-round2/phase-summary.csv) · [发布文件校验](2026-10-13-thor-seven-conditions-round2/publication-manifest.json) |
| 2026-10-13 | RM-01 Thor，第二轮补充核对与单路短问答，26分54秒连续采集 | [补充与实测报告](2026-10-13-thor-short-qa/analysis-report.md) | [时间线](2026-10-13-thor-short-qa/analysis/shortqa-timeline.png) · [增益补充](2026-10-13-thor-short-qa/analysis/round2-gain-supplement.png) | [脱敏证据包](2026-10-13-thor-short-qa/evidence.zip) · [逐请求CSV](2026-10-13-thor-short-qa/analysis/request-summary.csv) · [发布校验](2026-10-13-thor-short-qa/publication-manifest.json) |

七工况报告包含4路并发和16路请求两个独立批次。第一轮存在整段采集缺口，未纳入此处。完整归档包括原始采样、操作记录、分析脚本与日志；推理时间来自实际日志，模型拉起和卸载的人工时间边界在报告中明确注明。

短问答报告单独核对旧结果，包含一条预试、6题稀疏与12题连续单路请求。正式请求实际1.54～3.16秒，多数短于目标；失温及其恢复影响保留，未排查根因。两组不是独立因果A/B，曲线文件待合并。
