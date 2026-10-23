from pathlib import Path
import json,csv,statistics
from datetime import datetime
p=Path(__file__).resolve().parent.parent;j=json.loads((p/'analysis/statistics.json').read_text());state=json.loads((p/'collection-stop-state.json').read_text());w=json.loads((p/'workload/summary.json').read_text());formal=[q for q in j['requests'] if q['stage'] in ['sparse','continuous']]
def fmt(x,n=2):return f'{x:.{n}f}' if isinstance(x,(int,float)) else '未知'
def clock(x):return datetime.fromisoformat(x.replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai')).strftime('%H:%M:%S.%f')[:-3] if x else '未知'
lines=['# TTO-第二轮补充与短问答实测报告','', '计划：TTO-SHORT-QA-v1.0。旧七工况只做原始数据核对，另行执行一轮单路短问答连续采集。未修改生产代码、控制设置、采样频率或部署，未训练、未提交推送，未重跑七工况。','', '## 本轮主要结果','']
for stage,label in [('sparse','稀疏'),('continuous','连续')]:
 qs=[q for q in formal if q['stage']==stage];dur=[q['duration_seconds'] for q in qs];risers=[q['request_id'] for q in qs if q['pwm_increased_after_end']]
 lines.append(f"- {label}组完成{len(qs)}条，实际请求时长{fmt(min(dur)) if dur else '未知'}～{fmt(max(dur)) if dur else '未知'}秒，均值{fmt(statistics.mean(dur)) if dur else '未知'}秒。结束后至下一题前观测到PWM高于结束时快照的请求：{', '.join(risers) or '未观测到'}。这只是对应窗口行为，不分摊单题因果。")
 starts=[q['start_state']['tj'] for q in qs if q['start_state']];gains=[q['start_fan']['controller_gain'] for q in qs if q['start_fan']];duties=[q['start_fan']['duty'] for q in qs if q['start_fan']]
 lines.append(f"- {label}组任务前TJ序列："+' / '.join(fmt(x) for x in starts)+' °C；PWM序列：'+' / '.join(fmt(x,0) for x in duties)+' %；gain序列：'+' / '.join(fmt(x,6) for x in gains)+'。连续组按实际顺序展示是否积热，不称独立因果A/B。')
lines += [f"- 本轮采集 {clock(state['collection_started_at_utc'])}～{clock(state['ended_at_utc'])}（北京时间），负载程序状态{w['status']}；有效新TJ样本{j['accepted_samples']}，原始观察{j['raw_records']}条。",f"- HTTP读取异常{sum(x['type'].startswith('http') for x in j['anomalies'])}个，设备失温快照{sum(x['type']=='device_temp_stale' for x in j['anomalies'])}个；分别标记，未调查原因。",'', '## 第二轮补充核对','', '\n'.join(('###'+l[2:] if l.startswith('## ') else l) for l in (p/'第二轮核对与补充说明.md').read_text().splitlines()[2:]), '', '## 本轮配置与时间口径','', '- TTO现场版本0.2.2，Thor/NVML合同，原1秒TJ/风扇与5秒主板温度轮询保持不变。模型为原RM-01 VLM；API公告的模型root与旧轮一致，未核验权重字节哈希。设备实时报出的固件版本单独保存，不把git短提交当闪存SHA证明。', '- 原模型驻留、AUTO及已有全部控制设置保持；既有gain起点照实记录，没有清零。用户基础曲线文件尚未收到：待合并，与controller_gain时间序列分开。', '- 正式请求每题独立，不累计对话，默认temperature/top_p/template/cache不改。预试一条自然结束3.612秒后冻结max_tokens=64；max_tokens字段已被接口接受，usage生成token逐条保存；未出现单独思考字段，未另行核验隐藏内部过程，不能靠60字要求宣称约束了隐藏思考。', '- TTO与负载在同一N305主机运行，UTC与monotonic均记录；客户端提交和协议完成不是GPU内核精确起止。日志中的first_network_packet实际是首次读到的SSE行时间，不是抓包确认的TCP首包；首模型内容/首可见内容另列。', '- 当前状态/metrics在执行前及逐题前只读检查，未发现此前任务仍运行或请求排队。自然额外负载不能仅靠本轮日志完全排除。', '- 所有wait从上一条client_end的monotonic起算，90秒或10秒等待后加上只读检查与请求准备的少量耗时，实际间隔逐条保存。最长40分钟，没有延长或重跑。采集开头额外记录了约3分钟脚本准备背景，规定180秒背景仍另外完整执行；该额外观察与正式组分开，准备阶段已计入本轮硬截止，属于执行偏差。', '- 峰值窗口为提交到下一条本组提交之前；最后一条到本组300秒回落结束。窗口叠加历史，峰值不归因于单条请求。', '- 新TJ仅使用已保存accepted新样本；PWM仅用成功且as-of年龄≤2.5秒记录，缺失不补0，API与TJ仍异步。独立rail单列、不当整机输入。','', '## 逐请求统计','', '| 请求 | 实际秒 | finish_reason | usage生成token | 起点TJ/PWM/gain | 窗口TJ峰值 | API PWM峰值 | PWM峰值距结束秒 | 结束后继续升高 |','|---|---:|---|---:|---|---:|---:|---:|---|']
flat=[]
for q in formal:
 st=q['start_state'] or {};sf=q['start_fan'] or {};pk=q['peaks']['tj'];fp=q['fan_peak'];u=q.get('usage') or {}
 lines.append(f"| {q['request_id']} | {fmt(q['duration_seconds'])} | {q.get('finish_reason') or '未知'} | {u.get('completion_tokens','未知')} | {fmt(st.get('tj'))}/{fmt(sf.get('duty'),0)}/{fmt(sf.get('controller_gain'),6)} | {fmt(pk.get('tj') if pk else None)} | {fmt(fp.get('duty') if fp else None,0)} | {fmt(q['fan_peak_relative_end_s'])} | {'是' if q['pwm_increased_after_end'] else '未观测到'} |")
 flat.append({'request':q['request_id'],'stage':q['stage'],'duration_seconds':q['duration_seconds'],'finish_reason':q.get('finish_reason'),'prompt_tokens':u.get('prompt_tokens'),'completion_tokens':u.get('completion_tokens'),'start_tj_C':st.get('tj'),'start_pwm_pct':sf.get('duty'),'start_gain':sf.get('controller_gain'),'window_tj_peak_C':pk.get('tj') if pk else None,'window_pwm_peak_pct':fp.get('duty') if fp else None,'pwm_peak_relative_end_seconds':q['fan_peak_relative_end_s'],'pwm_increased_after_end':q['pwm_increased_after_end'],'gain_values':str(q['gain_values']),'anomaly_count':len(q['anomalies'])})
with (p/'analysis/request-summary.csv').open('w',newline='') as f:
 ww=csv.DictWriter(f,fieldnames=list(flat[0]) if flat else ['request'],lineterminator='\n');ww.writeheader();ww.writerows(flat)
lines+=['','表中亚秒时差是日志接收时间之差，受约1秒异步采样限制，不是已识别的物理响应延迟。单题后的高PWM也可能包含历史状态。','', '## 结束后5/15/30/60秒快照','', '每格为 TJ°C / 成功PWM%。括号“后题影响”意味着新题已经提交，不能用于宣称该题独立回落。取目标时刻后的最近新TJ，容许到达偏差≤1.6秒；没有有效样本则写未知。','', '| 请求 | +5秒 | +15秒 | +30秒 | +60秒 |','|---|---|---|---|---|']
for q in formal:
 cells=[]
 for sec in ['5','15','30','60']:
  z=q['post_end_offsets'][sec];r=z['sample'];v=f"{fmt(r['tj'])}/{fmt(r['duty'],0)}" if r else '未知'
  if z['next_task_influence']:v+='（后题影响）'
  cells.append(v)
 lines.append('| '+q['request_id']+' | '+' | '.join(cells)+' |')
lines+=['', '## 组级与回落','', '| 阶段 | TJ首/末°C | TJ均值/峰值°C | PWM均值/峰值% | gain首/末 | 观测PWM≥80%秒 |','|---|---:|---:|---:|---:|']
for ph in j['phases']:
 m=ph['metrics'];tj=m.get('tj') or {};d=m.get('duty') or {};g=m.get('gain') or {}
 lines.append(f"| {ph['phase']} | {fmt(tj.get('first'))}/{fmt(tj.get('last'))} | {fmt(tj.get('mean'))}/{fmt(tj.get('max'))} | {fmt(d.get('mean'))}/{fmt(d.get('max'),0)} | {fmt(g.get('first'),6)}/{fmt(g.get('last'),6)} | {fmt(ph['pwm_ge80_observed_s'])} |")
lines+=['','PWM≥80%只是描述口径，不是安全阈值或多余散热判定；其持续时间按成功API状态持有到下一条、最长2.5秒估计，未跨缺失长空隙延续。TJ下降不证明整体储热已清空；没有TTP/铝体和环境温度、声音记录，不能识别真实热容或宣布降噪。缓存命中字段未取得则未知，不以短时长自行推定缓存。','', '## 异常与解释边界','']
for a in j['anomalies']:lines.append(f"- {clock(a['time'])} {a['type']}，引用{a['ref']}；保持事件与受影响窗口，不归因。")
if not j['anomalies']:lines.append('- 本轮原始采集记录未观测到HTTP错误或设备stale；不据此证明未采到的周期完全无异常。')
lines+=['- 每条请求status、finish_reason、DONE/EOF、usage与异常在原逐请求日志保存。缺失usage写未知；不把字符数/chunks或末条usage当全批tokens。超时若无法确认结束，停止后续调度，保留未知。','- 全量行为与异常窗口都保留，既有质量资格不修改；报告不等同正式预测成绩或控制收益验证。','', '## 图表与后续','', '![短问答连续时间线](analysis/shortqa-timeline.png)','', '![第二轮增益补充](analysis/round2-gain-supplement.png)','', '用户曲线文件：待合并。下一步仅保留待核对问题，不在本轮优化风扇或训练模型。本轮完成后停止。','']
(p/'TTO-第二轮补充与短问答实测报告.md').write_text('\n'.join(lines))
