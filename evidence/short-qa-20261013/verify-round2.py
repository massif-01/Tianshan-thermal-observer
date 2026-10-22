from pathlib import Path
import json,hashlib,datetime,statistics,re
P=Path(__file__).parent
R=Path('/Users/massif/Tianshan-thermal-observer/evidence/formal-collection-20261013-round2')
run=next(R.glob('run-*'));idx=json.loads((run/'files.json').read_text());assert all(hashlib.sha256((run/n).read_bytes()).hexdigest()==h for n,h in idx.items())
raw=[json.loads(l) for l in (run/'observations-0001.jsonl').read_text().splitlines()];byref={r['ref']:r for r in raw};fans=[]
def t(s):return datetime.datetime.fromisoformat(s).timestamp()
def snap(r):
 f=r['payload']['data']['fans'][0];return dict(f,time=r['received_at_utc'],ref=r['ref'])
for r in raw:
 if r['kind']=='fan' and r.get('payload',{}).get('data',{}).get('fans'):fans.append(snap(r))
ref=Path('/private/tmp/tto-short-qa-v1-package/reference/independent/results');ext=json.loads((ref/'findings.json').read_text());phases=json.loads((ref/'phase-fan-snapshots.json').read_text());checks=[]
for ph in phases:
 fs=[f for f in fans if t(ph['start'])<=t(f['time'])<t(ph['end'])];prev=[f for f in fans if t(f['time'])<t(ph['start'])]
 own={'previous':prev[-1] if prev else None,'first':fs[0] if fs else None,'peak':max(fs,key=lambda f:f['duty']) if fs else None,'last':fs[-1] if fs else None}
 dif=[]
 for k,expected in ph.items():
  if k not in own or expected is None:continue
  actual=own[k]
  for field,value in expected.items():
   if field=='local':continue
   av=actual.get(field)
   if isinstance(value,float) and isinstance(av,(float,int)):same=abs(value-av)<1e-10
   else:same=value==av
   if not same:dif.append({'snapshot':k,'field':field,'reference':value,'own':av})
 checks.append({'phase':ph['phase'],'status':'一致' if not dif and len(fs)==ph['fan_samples'] else '差异','fan_sample_count':len(fs),'reference_sample_count':ph['fan_samples'],'differences':dif,'snapshots':own,'peak_seconds_since_start':t(own['peak']['time'])-t(ph['start'])})
gain=[];last=None
for f in fans:
 if f.get('controller_gain')!=last:gain.append(f);last=f.get('controller_gain')
assert [f['ref'] for f in gain]==[f['ref'] for f in ext['gain_changes']]
summary=json.loads((R/'workload-logs/concurrent16-summary.json').read_text());w=summary['workers'];counts={'workers':len(w),'attempts':sum(v['requests'] for v in w.values()),'completed':sum(v['completed'] for v in w.values()),'errors':sum(len(v['errors']) for v in w.values()),'workers_ever_output':sum(v['characters']>0 for v in w.values())}
progress=[];previous={}
for line in (R/'workload-logs/concurrent16-run.log').read_text().splitlines():
 if not line.startswith('PROGRESS '):continue
 j=json.loads(line[len('PROGRESS '):]);inc=sorted(int(k) for k,v in j['workers'].items() if v['chunks']>previous.get(k,0));progress.append({'elapsed':j['elapsed'],'workers_with_chunk_increases_since_previous_report':inc});previous={k:v['chunks'] for k,v in j['workers'].items()}
assert progress==ext['concurrent16_progress_counts']
stale=[f for f in fans if f.get('temp_stale')];errors=[r for r in raw if r.get('error_class')]
impact=[]
for f in stale:
 pos=fans.index(f);impact.append({'event':f,'surrounding':fans[max(0,pos-1):pos+6],'interpretation':'设备主动报告失温及25%PWM；恢复窗口单列，不归因，不将后续降档全部解释成正常优化'})
result={'old_run_id':'929742d7-6f4d-4d80-b53e-4436d45ac12c','old_archive_sha256':hashlib.sha256(Path('/Users/massif/Tianshan-thermal-observer/deliverables/TTO-第二轮七工况数据与分析-20261013-929742d7.zip').read_bytes()).hexdigest(),'verified_original_index_files':8,'phase_snapshot_checks':checks,'gain_changes':gain,'concurrent16_counts':counts,'progress_activity_checks':'一致；10秒窗口可确认收到增长，不证明精确同一硬件时刻的GPU并行数','http_errors':errors,'device_stale_impact':impact,'insufficient_evidence':['服务端实际同时活跃数与用户所说8路配置','部署固件SHA、基础曲线与逐周期公式复现','任何stale或HTTP超时根因，包括通讯/手动刷新冲突','累计输出9路并非同一时刻9路；输出增量窗口不是服务端调度证据']}
(P/'round2-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
lines=['# 第二轮独立核对与补充说明','', '核对原run 929742d7-6f4d-4d80-b53e-4436d45ac12c；8项原始索引SHA全部一致。旧报告、原始数据及既有PR均未改动。','', '## 核对一致','', '| 工况 | 首次API峰值 | PWM | API温度 | 斜率 °C/min | gain | 距客户端提交约秒 |','|---|---|---:|---:|---:|---:|---:|']
for c in checks:
 if c['phase'] not in ['4','5a','5b']:continue
 f=c['snapshots']['peak'];lines.append(f"| {c['phase']} | {f['time']} | {f['duty']} | {f['temperature']} | {f['slope_c_per_min']:.1f} | {f['controller_gain']:.6f} | {c['peak_seconds_since_start']:.3f} |")
lines+=['','- 外部10个阶段的previous/first/peak/last原始引用、状态字段及fan样本数逐项核对一致。三个峰值均auto/active、guard=false、stale=false。5b 100%时预测78.1°C，实测API温度64.9°C；不等于保护触发。','- gain变化的6个原始引用一致；分别为1.183859→1.124666→1.293365→1.487370→1.710476→1.967047，属于运行控制状态，不是TTO训练。',f'- 16路批次：{counts}。前130秒10秒输出增量窗口仅worker6/7/9/11有增长；原始progress逐条一致。','- 1次设备stale与3次HTTP超时分别核对一致。失温处77%→25%→37%→47%→49%→51%的实际轨迹保留，影响窗口与后续控制历史单独说明；不调查原因。','', '## 发现差异','', '- 旧报告图表的100%点时间12:13:25.385来自TJ采样时刻上的as-of PWM；独立补充12:13:24.890是首次成功fan API返回。两者时间轴不同，相差约0.495秒，不是原始PWM峰值数值冲突。','- 工况3旧表PWM峰值36%，独立API区间峰值35%。旧表在首个新TJ采样上匹配了区间开始前尚在2.5秒年龄许可内的36%快照；独立分析只选区间内部fan返回。保留旧表口径并说明差异，不覆盖数据。','- 旧报告关于结束温度高1.11°C的“仍有热残留”表述偏强。确认的是结束TJ仍高于初始空载均值，缺少环境温度等证据，不能据此确认剩余储热量或排除环境变化；本补充收窄解释。','', '## 当前证据不足','', '- 服务端同时执行数未知；16路客户端、累计9路输出、10秒窗口4路内容增长、用户所说8路配置不是同一量。','- 首峰约28～30秒是跨主机客户端日志与fan接收时间之差，未有旧轮独立时钟校准；不能据此宣称亚秒物理响应或唯一趋势窗口原因。','- 固件manifest身份与实际基础曲线快照缺失，引用的main公式仅是机制线索，不分摊精确因果贡献。','- 通讯、手动刷新、锁竞争或WS故障均未在本次证明。红叉只保留事件与影响。','- 热容、整体储热是否清空、噪音收益，以及各阶段独立因果效果均不能由这些数据确认。','', '用户曲线文件：待合并。后续短问答按固定方案执行，不为迎合外部分析改变参数。','']
(P/'第二轮核对与补充说明.md').write_text('\n'.join(lines))
print('snapshot checks',[(c['phase'],c['status']) for c in checks]);print(counts)
