"""Build the Chinese review report from computed artifacts; no fitting."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'vendor/v1'))
from common import read,write,sha
from scoring import load_jsonl

OUT=ROOT/'runs/main';parts=[]
def add(text=''):parts.append(text+'\n')
def table(headers,rows):
    lines=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    lines.extend('| '+' | '.join(str(x) for x in row)+' |' for row in rows)
    add('\n'.join(lines))
def f(x):return f'{x:.3f}'
def metric_row(tables,scope='all',value='all',h=None,context=None,layer=None):
    return next(t for t in tables if t['scope']==scope and t['value']==value and (h is None or t.get('h')==h) and
                (context is None or t.get('context')==context) and (layer is None or t.get('layer')==layer))

add('# TTO-旧模型新数据检验与第二轮辨识报告')
add('2026-10-14 · TTO-ID-R2-v1.0 · 实际CPU离线研究 · 等待独立复审')
add('已完成M数据登记、九份冻结旧模型的检验与封存，以及第二轮42次有界拟合和三组紧凑Ridge。G1拟合一个等效温度状态；G2拟合快/慢两个潜在温度状态，两者都实际使用GPU功率、CPU/SOC/MSS功率和成功PWM。它们是研究模型，不能解释为已经测到热容或完成在线学习。')
add('**热响应有进展，通用未来预测仍未通过。** 旧主参照LS-fit G2已经能解释M的整段响应，MAE为0.369°C。加入M后，短侧拟合模型推到长任务的整段误差从13.753降到1.680°C；联合模型在M上从0.369降到0.319°C，但S从0.611变为0.631°C，没有全面改善。对真正45秒未来的预测，联合G2 HOLD总体仅从1.012变为1.007°C；短问答仍输给保持当前TJ。')
add('最差仍在负载突变：联合G2的45秒HOLD在正常共同集合内出现约12°C最大欠预测；S02/S03/D01在实测热点时刻仍低估1.93–2.34°C。M持续升温和较晚回落有研究价值，短峰、结束后的前5秒回落以及未知未来任务切换仍有明显缺口。')
add('M的24°C已按用户确认登记，并真正绑定到独立A24再拟合；原日志14份环境null保持原样。A24能解释M，但整体损失升高21.4%，GPU系数贴零边界，暴露出等效边界与高度共线功率输入之间的归因问题，不能据此质疑用户确认的室温。')
add('**唯一推荐下一步：保持G2参数冻结，单独预登记一次“因果未来输入”离线实验。** 用预测起点已经到达的功率变化和请求在途状态，检验明确的未来功率情景是否优于固定HOLD；不读取后续实际结束时刻，不按误差事后选HOLD/RELAX30。本轮只提出这一项，完成交付后停止。')

add('**材料身份与登记结果**')
data=read(OUT/'registered/data.json');coverage=read(OUT/'registered/coverage.json')
table(['资料','run ID','新TJ数','严格当前资格数','严格段数','≥60秒段数','资料角色'],[
    [r,data['runs'][i]['run_id'],coverage[r]['accepted'],coverage[r]['strict_current'],len(coverage[r]['segments']),sum(s['span_s']>=60 for s in coverage[r]['segments']),
     '既有开发资料' if r!='M' else '新增开发过程；现场准入override有记录'] for i,r in enumerate(['L','S','M'])])
durations=[p['actual_s'] for p in data['runs'][-1]['phases'] if p['macro']=='work']
add('共6643份真实新TJ，来自三个热过程；M三个工作块、S十八条请求都不作为独立episode。M实际块长'+'/'.join(f(x) for x in durations)+'秒，工作开始前TJ分别46.281/46.156/46.218°C。客户端协议完成时刻用于事件说明，不能等同GPU内核结束。')
add('M原健康核对的首段完整输入约2336.380秒；本轮由实际accepted端点定义的拟合路径为2335.486秒，恢复段172.037秒。差别来自事件边界与温度采样端点，不是放宽资格。M-00贯穿全部三块及主要回落，M-01只在真实失温/恢复以后建立；不存在工作块重置。首段A-long在过去60秒之后连续自由传播约2275秒。尾部原异常及恢复原样保留。')
add('L/S用首轮归档处理器，M用22份manifest源码SHA全部匹配的0.2.4处理器，均只回放文件。L/S的全部2529/1610份accepted温度、功率、源段、控制资格、序号、接收时间和宏类标签与首轮派生序列逐项相同。私有原件与分享归档的不同SHA单列在source-identity-supplement.json，未把脱敏归档身份当作私有原件身份。')
add('24°C只绑定M run。它来自用户确认，不是逐秒环境传感器序列；仪器、位置、分辨率和准确确认时刻仍未记录。L/S室温保持未知；A24拟合得到的L/S等效E接近24也不能替它们补造室温。现场请求准入override从未用于放宽源质量、训练、PWM有效期或标签。')

add('**冻结、资格和信息预算**')
table(['项目','本轮执行合同'],[
 ['主输入','VDD_GPU、VDD_CPU_SOC_MSS分别以W输入；成功PWM/100；5V/gain/其他温区仅诊断'],
 ['数值','float64精确事件传播；真实接收时刻左持有；按实际有效期截断，不插值、不填零'],
 ['源有效期','绑定实际accepted测量的年龄与截止时刻，不借后续被拒消息延长'],
 ['标签','每个15/45/90秒独立取同源第一份t≥起点+h、偏移≤2秒的合法TJ'],
 ['A-long','每严格段过去60秒初始化后全段自由响应；不再吸收真实TJ'],
 ['A-roll','与B相同过去状态，额外读取名义h内完整真实输入，不读取未来TJ'],
 ['B','每真实新TJ一个起点；只用已到达信息；HOLD主情景、RELAX30独立诊断情景'],
 ['初始化','每run第一个合法60秒前缀估计一次E，此后固定；真实中断后仅重新估计状态'],
 ['状态','G2用过去60秒估慢状态，当前TJ定快状态；参数不在线更新；60秒不代表热平衡'],
 ['RELAX30','30秒指数回落；每rail底值min(当前功率,本模型训练P10)；PWM保持当前'],
 ['新规则','TTO-EVAL-AVAIL-v2.0：未来辅助缺口不销毁B误差；A仍须完整未来输入'],
 ['分层','confirmed_normal / aux_observation_gap / observed_abnormal_or_changed / unclassified_gap；未知不写正常'],
 ['比较','旧/新同规则、同60秒预算、同起点/同标签，记录origin_ref+horizon+label_ref的集合SHA']])
add('本文性能主表采用confirmed_normal共同集合；辅助缺口、已观测异常与未知分别保留成绩和覆盖，不能混成正常结论。旧严格参考也单独计算。R_TJ/B0/B1按自身TJ历史资格报告；G1/G2/R_IO仍要求当前及过去输入完整。标签只因源身份/序号/隔离等真实质量问题或缺少答案而排除，不因没有90秒答案连带删除45秒。')
add('spec与资料角色在首个M旧模型成绩前冻结；stage2-frozen-evaluation.json封存全部旧M逐点结果、规则/输入/模型/指标SHA后，阶段3才开始。D-LM和D-SM全部模型先冻结，再计算目标成绩。M及既有图表已被观察，不能称全盲；后续模型θ使用过L/S/M，联合成绩明确为拟合内。')
add(f'阶段2封存SHA：`{sha(OUT/"stage2-frozen-evaluation.json")}`。复算确认42次拟合全部发生在它以后；旧九份JSON SHA始终一致。')
add('封存覆盖阶段2的状态、A/B逐点、主分层评分和覆盖。事件峰值/回落汇总与文字报告在交付阶段从这些封存轨迹后置派生，未在阶段3之前单独生成文字报告；这是相对于交接要求的流程差异。它们没有参与初值选择、没有改变旧成绩，最终SHA清单另覆盖这些派生产物，交独立复审确认。')

add('**旧模型在M：A热响应**')
rows=[]
for label in ['L-fit','S-fit','LS-fit']:
    dest=OUT/'old-models-on-M'/label;t=metric_row(read(dest/'A-long-metrics.json'))
    for m,v in t['metrics'].items():rows.append([label+('（预定主参照）' if label=='LS-fit' else '（诊断）'),m,v['n'],f(v['mae']),f(v['balanced_mae']),f(v['rmse']),f(v['p95_abs']),f(v['bias']),f(v['underprediction_max'])])
table(['旧参照','结构','n','A-long MAE','宏类均衡MAE','RMSE','绝对P95','偏差','最大欠预测'],rows)
add('单位为°C。原S-fit在M持续升温/回落的整段误差很大，即使滚动状态能拉回部分误差也不能遮掉A-long失败。主参照LS-fit G2优于G1，主要证据是实际三块与回落的自由传播，而不是反复读真实TJ纠偏。')
rows=[]
for label in ['L-fit','S-fit','LS-fit']:
    dest=OUT/'old-models-on-M'/label
    for h in [15,45,90]:
        t=metric_row(read(dest/'A-roll-metrics.json'),h=h,context='confirmed_normal',layer='known_input_only')
        rows.append([label,h,t['metrics']['G2']['n'],f(t['metrics']['G1']['mae']),f(t['metrics']['G2']['mae']),f(t['metrics']['G2']['underprediction_max']),t['cohort_id'][:12]])
table(['旧参照','h秒','共同n','G1 A-roll MAE','G2 A-roll MAE','G2最大欠预测','集合SHA前12位'],rows)
add('A-roll读取未来真实功率/PWM，只说明热响应；它的误差不能替代下一表的真实未来预测。')

add('**旧模型在M：B真实未来预测**')
rows=[]
for label in ['L-fit','S-fit','LS-fit']:
    tables=read(OUT/'old-models-on-M'/label/'B-metrics.json')
    for h in [15,45,90]:
        t=metric_row(tables,h=h,context='confirmed_normal',layer='all_methods');v=t['metrics']
        rows.append([label,h,v['B0']['n'],*[f(v[m]['mae']) for m in ['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']]])
table(['旧参照','h秒','共同n','B0','B1','R_TJ','R_IO','G1 HOLD','G1 RELAX30','G2 HOLD','G2 RELAX30'],rows)
add('表中为时间加权MAE。三组旧参照各自保留原Ridge系数、缩放、λ与P10，没有看M成绩后改选旧胜者。旧主参照G2 HOLD的M工作块45秒MAE为4.278°C，B0为4.371°C；背景0.596°C、回落0.662°C。总体较低不代表任务切换时准确。')
cal=read(OUT/'old-models-on-M/LS-fit/calibrations.json')
add(f'LS-fit G2的M首前缀拟合等效E={cal["G2"]["M-00"]["E"]:.3f}°C、慢初态={cal["G2"]["M-00"]["Ts_initial"]:.3f}°C；恢复段沿用同一个E，只重新估慢状态。原参数θ不变，E没有被改成24°C。该前缀归一化列条件数{cal["G2"]["M-00"]["condition"]:.3f}，未触发继承的弱秩回退；若触发，规则是固定为训练E中位数，再估慢态。')

add('**加入M后的配对比较**')
table(['矩阵','拟合run','目标run','配对旧参照','结论角色'],[
 ['D-LM','L+M','S','L-fit','开发跨任务检查；S此前已被研究'],['D-SM','S+M','L','S-fit','反向压力检查，不是未来时间泛化'],['D-LSM','L+S+M','逐轮L/S/M','LS-fit','联合拟合内；公平重放仍使用过去前缀']])
rows=[]
for eid in ['D-LM','D-SM','D-LSM']:
    p=read(OUT/'evaluation'/f'{eid}-paired.json')
    for r in [t for t in p['A-long'] if t['scope']=='run']:
        ar=metric_row(p['A'],scope='run',value=r['value'],h=45,context='confirmed_normal')
        b=metric_row(p['B'],scope='run',value=r['value'],h=45,context='confirmed_normal')
        rows.append([eid,r['value'],f(r['metrics']['old:G1']['mae'])+'→'+f(r['metrics']['new:G1']['mae']),
                     f(r['metrics']['old:G2']['mae'])+'→'+f(r['metrics']['new:G2']['mae']),
                     f(ar['metrics']['old:G2']['mae'])+'→'+f(ar['metrics']['new:G2']['mae']),
                     f(b['metrics']['old:G2-HOLD']['mae'])+'→'+f(b['metrics']['new:G2-HOLD']['mae']),
                     f(b['metrics']['old:G2-RELAX30']['mae'])+'→'+f(b['metrics']['new:G2-RELAX30']['mae']),
                     f(b['metrics']['new:B0']['mae']),b['metrics']['new:G2-HOLD']['n']])
table(['矩阵','目标','G1 A-long旧→新','G2 A-long旧→新','G2 A-roll45旧→新','G2 HOLD45旧→新','G2 RELAX30旧→新','B0 45','B共同n'],rows)
add('D-SM改善最明显：原短侧θ推到长负载时失真，M补入持续热响应后大幅收敛。但新HOLD45在L仍高于B0；新RELAX30在L明显变坏，因为持续任务中它会假定功率下降。这不是可逐点挑选更好情景解决的评分问题。D-LM在S的已知输入响应略好，仍未胜过简单未来预测基线。联合模型对M的改善是拟合内事实，L/S整段响应没有全面改善。')
add('联合拟合旧→新的三轮共同正常集合总分，同时显示时间总分和run/宏类均衡总分：')
rows=[];p=read(OUT/'evaluation/D-LSM-paired.json')
for h in [15,45,90]:
    t=metric_row(p['B'],h=h,context='confirmed_normal')
    for m in ['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']:
        o=t['metrics']['old:'+m];n=t['metrics']['new:'+m]
        rows.append([h,m,n['n'],f(o['mae'])+'→'+f(n['mae']),f(o['balanced_mae'])+'→'+f(n['balanced_mae']),f(n['rmse']),f(n['p95_abs']),f(n['bias']),f(n['underprediction_p95']),f(n['underprediction_max'])])
table(['h秒','方法','共同n','时间MAE旧→新','均衡MAE旧→新','新RMSE','新绝对P95','新偏差','新欠预测P95','新最大欠预测'],rows)
add('Ridge没有因加入M而统一胜出：R_IO45在L从1.591升到1.847°C，M从1.366降到1.355°C，S从0.388降到0.371°C。每个时距的训练标签独立；标准化、CV和λ选择只用当前拟合侧。训练原点按完整严格段分组，最多3折，λ沿用0.01/0.1/1/10；截距不惩罚，alpha=λΣw，近似同分优先更大λ。所有折run/段/宏类与训练引用保存，CV仅为开发选参，不是独立验证。')
add('**动态与背景分开看**')
rows=[]
for run in ['L','S','M']:
    ts=read(OUT/'evaluation/D-LSM/B-metrics.json')
    for macro in ['work','recovery','background']:
        # Run/macro intersections are computed directly, with full cohort identity in the evidence appendix.
        preds=load_jsonl(OUT/'evaluation/D-LSM/predictions.jsonl')
        group=[r for r in preds if r['run']==run and r['macro']==macro and r['h']==45 and r['control_context']=='confirmed_normal' and r['label'] and all(m in r['B'] for m in ['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30'])]
        from scoring import metrics
        if group:rows.append([run,macro,len(group),*[f(metrics(group,m)['mae']) for m in ['B0','R_TJ','R_IO','G2-HOLD','G2-RELAX30']],f(metrics(group,'G2-HOLD')['underprediction_max'])])
table(['run','宏类','共同n','B0 45','R_TJ 45','R_IO 45','G2 HOLD45','G2 RELAX30 45','HOLD最大欠预测'],rows)
add('回落前5秒的自由响应仍不准确。G2在M20/M60/M180这一窗口的MAE分别2.621/2.526/2.646°C；15–45秒分别0.143/0.087/0.316°C。较晚回落有价值不能抹掉最初快速降温的失败。背景保留参与权重，但M背景内起点可能在45秒内迎来任务启动，所以背景起点误差也不等同静态稳态误差。')

add('**峰值、回落与时间对齐**')
events=read(OUT/'diagnostics/event-metrics.json');rows=[]
for event in [x for x in events if x['evaluation']=='evaluation/D-LSM' and x['run']=='M']:
    old=next(x for x in events if x['evaluation']=='old-models-on-M/LS-fit' and x['event']['id']==event['event']['id'])
    a24=next(x for x in events if x['evaluation']=='evaluation/D-LSM-G2-A24' and x['run']=='M' and x['event']['id']==event['event']['id'])
    m=event['A_peak']['G2'];rows.append([event['event']['id'],f(event['event']['actual_s']),f(event['start_TJ']),f(event['actual_peak']),
             f(old['A_peak']['G2']['peak_error']),f(m['peak_error']),f(a24['A_peak']['G2']['peak_error']),f(m['peak_time_offset_s']),m['n'],f(m['coverage']*100)+'%'])
table(['M工作块','实际秒数','起始TJ','实测峰值','旧G2峰差','新G2峰差','A24峰差','新峰时差秒','峰窗共同n','覆盖'],rows)
add('峰差=模型峰值−实测峰值，按同一有效时刻集合取各自峰；峰时差单列。M均100%覆盖工作块内accepted TJ。短问答继承submit至客户端完成后5秒的峰窗，另记其他请求重叠；以下保留实测峰时刻误差，防止“晚到的较高模型峰”掩盖瞬时欠预测：')
rows=[]
for eid in ['S02','S03','D01']:
    n=next(x for x in events if x['evaluation']=='evaluation/D-LSM' and x['run']=='S' and x['event']['id']==eid)
    o=next(x for x in events if x['evaluation']=='evaluation/LS-fit-on-LSM' and x['run']=='S' and x['event']['id']==eid)
    g=n['A_peak']['G2'];rows.append([eid,f(n['actual_peak']),f(o['A_peak']['G2']['peak_error']),f(g['peak_error']),f(o['A_peak']['G2']['at_observed_peak_error']),f(g['at_observed_peak_error']),f(g['peak_time_offset_s']),g['n'],f(g['coverage']*100)+'%'])
table(['S请求','实测峰TJ','旧峰值差','新峰值差','旧在实测峰时误差','新在实测峰时误差','新峰时差秒','共同n','覆盖'],rows)
add('M三块回落各窗口的A-long G2 MAE（旧LS-fit / 新Efree / A24）：')
rows=[]
for eid in ['M20','M60','M180']:
    evs=[next(x for x in events if x['evaluation']==path and x['run']=='M' and x['event']['id']==eid) for path in ['old-models-on-M/LS-fit','evaluation/D-LSM','evaluation/D-LSM-G2-A24']]
    for i,win in enumerate(evs[0]['cooldown']):rows.append([eid,str(win['window_s']),win['source_TJ_n'],*[f(e['cooldown'][i]['metrics']['G2']['mae']) for e in evs]])
table(['块','完成后秒窗','真实TJ n','旧G2','新G2','A24 G2'],rows)
add('所有L工作阶段、S十八条请求、M三块及五段回落窗均保存于event-metrics.json，包括共同引用、漏掉实测峰的标记、有效秒数及其他任务重叠；无删除不利脉冲。温升面积单位°C·s，仅为温度轨迹描述，不是焦耳。')
add('![M三工作块与回落](runs/main/figures/M-blocks-and-cooldown.png)')
add('![S短峰](runs/main/figures/S-short-peaks.png)')
add('![全部三轮自由响应](runs/main/figures/A-long-all-runs.png)')
add('![B45两种未来情景分别显示](runs/main/figures/B45-HOLD-and-RELAX30.png)')

add('**24°C边界与参数诊断**')
diag=read(OUT/'diagnostics/fit-diagnostics.json');rows=[]
for x in diag:rows.append([x['candidate'],x['selected_seed'],f(x['J']),f'{x["dynamic_count"]}+{x["boundary_free_count"]}+{x["slow_initial_count"]}={x["total_free_count"]}',
                         sum(t['converged'] for t in x['attempts']),','.join(x['near_optimal_seeds']),','.join(next(t['boundary_parameters'] for t in x['attempts'] if t['seed']==x['selected_seed'])) or '无'])
table(['候选','训练择优初值','Huber J','动态+E+慢初态自由度','收敛/6','5%内初值','择优贴边'],rows)
add('42/42实际尝试数值收敛；每组只按对应训练J择优，求解次数和残差调用均未超预算。Huber转折0.3°C不代表验收线。A24真正从优化变量移除E_M，67降为66个自由度，L/S仍各有自由E；没有加偏置、常数热源或环境曲线来抵消约束。每个真实严格段一个慢初态，所以联合模型含58个慢初态，不应只说“六个参数”。许多短段初态信息弱，完整缩放Jacobian存在近零奇异值，不能把收敛当作参数可唯一识别。')
rows=[]
for eid in ['D-LM','D-SM','D-LSM','D-LSM-G2-A24']:
    p=read(OUT/'fits'/f'{eid}-G2/model.json') if 'A24' not in eid else read(OUT/'fits'/eid/'model.json')
    rows.append([eid,*[f(p['dynamic'][k]) for k in ['a','c','d0','d1','b_g','b_c']],*[f(p['parameters'][f'E_{r}']) if f'E_{r}' in p['parameters'] else '—' for r in ['L','S','M']]])
table(['G2候选','a','c','d0','d1','b_g','b_c','训练E_L','训练E_S','训练E_M'],rows)
add('Efree联合E_M=34.976°C，与确认室温24°C相差10.976°C；这是拟合的等效边界，不是环境测量。A24总体J从1.167升到1.417，约+21.4%；因果前缀A-long的L/M/S分别0.950/0.259/0.387°C，而Efree为0.387/0.319/0.631°C。A24使M和S较好、L变差，不能拿单独M胜出取代主矩阵结论。GPU热增益约1.36e-39贴零，而CPU/SOC/MSS吸收了主要热输入贡献。')
add('两rail的Pearson相关L=0.96306、S=0.99036、M=0.99938，M新增了持续时间信息，却几乎没有新增功率比例独立激励。这解释了为何响应可改善、GPU/CPU分担却仍不可靠；不能从贴零推断GPU不发热。闭环PWM与功率/温度相关也限制物理归因，gain只记录诊断，没有作为热输入。')
add('![rail共线](runs/main/figures/rail-collinearity.png)')
add('六初值的J、近优参数范围、逐参数±1%尺度敏感性、缩放Jacobian奇异值、各run残差自相关及局部代数时间尺度/稳态增益均已保存。S+M的a≈3.659，对应快时间尺度约0.269秒；1秒遥测不能证明这种亚秒热常数。潜在慢状态也不是TTP或实测热容。TJ几乎贴近所报温区最高值，M的TJ−最高温区最大绝对差0.375°C；热点近似只是对报告温度的近似。')
add('D-LSM训练初态重建与公平因果评价分别存储。前者使用全段优化E/Ts，只称拟合能力；后者对新旧都使用过去60秒同预算。主参数敏感性是已登记解的代数扰动，没有追加优化、d1=0或180秒窗口重跑。残差保留时间相关与升/降温系统性偏差，不能当作独立随机误差给出置信区间。')

add('**覆盖率与规则变化**')
rows=[]
for x in read(OUT/'evaluation/D-LSM/coverage.json'):
    if x['h']==45 and x['method'] in ['B0','R_TJ','R_IO','G2-HOLD']:
        c=x['contexts'];rows.append([x['run'],x['method'],x['accepted_denominator'],x['emitted'],x['scored'],f(100*x['coverage'])+'%',x['strict_legacy_scored'],c['confirmed_normal'],c['aux_observation_gap'],c['observed_abnormal_or_changed'],c['unclassified_gap']])
table(['run','45秒方法','全accepted分母','可发','可评分','覆盖','旧严格评分','正常','辅助缺口','异常/变更','未知'],rows)
add('例如L的G2/R_IO可评分1813点，其中175点未来辅助缺口、45点已观测异常/变更、49点未知；这些都保留，正常主表只用1544点。S保留174点辅助缺口。M保留跨尾部异常的45点，不称正常。起点使用1秒及新规则产生的覆盖变化单列，不能称模型算法提升。')
rows=[]
for run in ['L','S','M']:
    ts=read(OUT/'evaluation/D-LSM/B-metrics.json')
    for context in ['aux_observation_gap','observed_abnormal_or_changed','unclassified_gap']:
        eligible=[t for t in ts if t['h']==45 and t['scope']=='run' and t['value']==run and t['context']==context and t['layer']=='all_methods']
        if eligible:
            t=eligible[0];v=t['metrics'];rows.append([run,context,v['G2-HOLD']['n'],f(v['B0']['mae']),f(v['G2-HOLD']['mae']),f(v['G2-RELAX30']['mae']),t['cohort_id'][:12]])
table(['run','保留层次','共同n','B0 MAE','G2 HOLD MAE','G2 RELAX30 MAE','集合SHA前12位'],rows)
add('这些层次用于诊断，不能推出原异常状态允许模型控制。逐层集合完整SHA和全部方法指标见B-metrics.json，逐点来源引用见predictions.jsonl。')

add('**验证、资源与可重跑交付**')
receipt=read(OUT/'readback-verification.json')
add(f'新增研究测试18项全部通过，涉及质量/恢复、未来信息、24°C绑定、阶段顺序、六初值账目、Ridge训练侧缩放/时距资格和M不按工作块重置。另独立复算{receipt["metric_tables_recomputed"]}张主/配对评分表，{receipt["model_JSON_roundtrip_prediction_checks"]}次JSON回读抽样预测最大差{receipt["max_prediction_difference_C"]}°C；核对1143份受保护文件和九份旧模型SHA不变。没有重跑产品189项、安装器或全仓防御检查。')
add('成果ZIP另在全新临时目录解压、逐成员核SHA，并用原交接重新准备缓存后独立回放：同样30123张表与4812次预测通过、差值0，未增加任何真实拟合。新增文件patch在空目录git apply --check通过。独立副本只核对模型/成果，不冒称重新访问作者原工作树。')
env=read(OUT/'environment.json');fr=read(OUT/'frozen-resources.json');rr=read(OUT/'refit-resources.json')
add(f'实际CPU研究环境：CPython 3.10.18、NumPy {env["numpy"]}、SciPy {env["scipy"]}、scikit-learn {env["sklearn"]}；BLAS单线程。冻结旧模型检查用时{fr["elapsed_s"]:.2f}秒、子进程峰值RSS{fr["child_peak_RSS_MiB"]:.2f}MiB；第二轮含评价用时{rr["elapsed_s"]:.2f}秒、峰值{rr["child_peak_RSS_MiB"]:.2f}MiB，低于2GiB参考值和2小时软预算。绘图另用现有CPython3.14/Matplotlib环境，没有改生产依赖。')
add('执行中资源监测的系统进程枚举被本机沙箱拒绝，改用仅记录子进程的getrusage；派生事件脚本曾遗漏A-long的wall字段，已按冻结原始ref回连UTC；图表核对后明确补足S的完成后5秒峰窗与实测峰时误差。原始资料、spec、拟合、阶段2封存和主评分均未因此改写；日志和修正说明保留。')
add('证据包含独立研究代码及新增文件patch、冻结spec/角色、阶段2封存、42次尝试、七个新灰箱模型、三份Ridge模型、逐点A/B、训练初态重建、诊断、六组PNG/SVG图、测试/复算与资源。原六个大归档及首轮完整证据只用原交接inputs的SHA引用，不重复递归塞入。独立入口见README-R2.md：bootstrap.py核验原交接并备缓存；research.py的register/frozen/refit/all顺序执行且校验封存；readback.py可只复算现有成果，无须新增拟合。')
table(['最终状态','值'],[['data_registered','completed'],['old_models_evaluated','completed_and_sealed'],['refit_completed','completed_42_attempts'],['response_assessed','completed_with_scene_limits'],['forecast_assessed','completed_no_universal_win'],['online_learning','not_implemented'],['deployed','not_performed'],['control_authorization','none']])
add('**唯一下一步的可证伪检查**')
add('预登记一个未来输入信息实验：保持G2结构、θ和60秒初始化固定，使用当时已经发生的提交/完成/在途记录与当前功率趋势，生成一套明确情景，先在现有资料上离线与固定HOLD同集合比较。至少同时检查45秒工作/回落分层MAE、P95和最大欠预测，不能以待机总体分数替代；若未来功率误差下降而温度预测仍不改善，则把剩余瓶颈定位到热点观测/动态近似。用户本轮不需要做现场操作，先独立复审成果；该建议未在本轮实施。')
add('**原输入SHA索引**')
index=read(ROOT/'handoff/inputs/input-index.json')
table(['输入','SHA-256'],[[x['path'],x['sha256']] for x in index['archives']])
add('规则来源：本轮用户明确授权与24°C确认 → 交接01方案/同版JSON → 已实现TTO-EVAL-AVAIL-v2.0 → 历史首轮规格。旧模型、旧失败、旧spec/split/test-used保留；所有新研究模型deployable=false。完成后停止交回复审，无设备连接、新请求、控制修改、CUDA、在线参数更新、部署、提交、推送或PR。')
path=ROOT/'TTO-旧模型新数据检验与第二轮辨识报告.md';path.write_text('\n'.join(parts));print(path)
