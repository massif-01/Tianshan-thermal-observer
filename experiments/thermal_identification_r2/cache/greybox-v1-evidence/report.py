"""Render the research report from saved results; does not fit or select models."""
import argparse
from pathlib import Path
import numpy as np
from common import read,write,sha
from evaluation import load_jsonl

TITLE='TTO-首轮灰箱实际辨识与对照实验报告'
METHODS=['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x) for x in r)+' |' for r in rows])+'\n'


def fmt(x):return f'{x:.3f}'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();run=args.run
    assert not args.output.exists()
    data=read(run/'data.json');coverage=read(run/'coverage.json');params=read(run/'diagnostics/parameters.json');env=read(run/'environment.json')
    parts=[f'''# {TITLE}

执行编号：**TTO-GREYBOX-ID-v1.0** · 2026-10-13 · 离线开发研究 · 交回复审

**G1、G2 已实际拟合，36 次主拟合全部收敛。G2 值得保留为热响应研究候选，但本轮不支持把它作为已验证的 45 秒预测器。** 两者都使用独立的 GPU、CPU/SOC/MSS 功率及成功 PWM；G1 拟合一个等效温度状态，G2 拟合快／慢两个等效状态，并处理未知边界和慢初态。它们不是实测热容。

- **热响应：**两轮合并后，G2 在初始化后不再读取 TJ 反馈的自由响应 MAE 为 **0.284°C**，G1 为 **0.911°C**。这是拟合内表达能力。长→短迁移的 G2 自由响应 MAE 为 **0.877°C**；短→长反向压力检查为 **13.753°C**，出现明显过热预测。
- **真实未来预测：**相同起点／标签的 45 秒比较中，长→短 G2-HOLD 为 **0.610°C**，保持当前 TJ 的 B0 为 **0.375°C**；短→长分别为 **6.941°C / 1.627°C**。两个方向都没有整体胜出。RELAX30 不能在长持续负载与短脉冲间通用，也未建立自动选择器。
- **有价值与无价值的场景：**合并拟合的 G2-HOLD 对长负载升温、持续段有表达优势；RELAX30 对孤立脉冲有拟合内价值。安静背景仍应尊重 B0。连续短问答的共同 45 秒起点仅 **6 个**，不足以判断整组任务效果；所有原始点和未评分原因均保留。
- **最值得推进：**先补一个包含中等持续时间负载与完整回落、记录环境温度和热前史的完整过程，区分“短脉冲侧辨识出的热增益不可迁移”与“未知边界／慢状态”两个解释。不是继续扩大数值搜索。本轮只设计补测，未执行。

全部资料已被项目分析过；F-SL 是反向工况压力诊断，F-POOL 是拟合内描述。本轮没有独立新过程验证，没有风扇控制收益或现场放行结论。状态估计不是在线参数学习。

## 1. 执行与来源

仅新增 `experiments/thermal_identification_v1/`。保留原工作树和当前分支，没有提交、推送或创建 PR。没有连接设备、live doctor、新负载、PWM／风扇／WS／采样更改、刷机、部署、重启、CUDA 或在线参数更新。红叉只影响资格；未追查其根因、旧错误曲线归属或实施短任务退档原型。

输入取交接包中的分享归档，逐包 CRC、原文件清单、run 索引和固定质量处理源码均核验。重放后逐条比对 accepted 序列的时间、序号、段、控制资格及全部 `values`；GPU/CPU/5V 的原始 mW→W 另作断言。两轮仍然只是两个 episode，18 条正式短请求没有被改称 18 个独立热过程。
''']
    sources=read(run/'source-archives.json')
    parts.append(table(['原包','字节','核验文件数','SHA-256'],[[s['original_attachment_name'],s['bytes'],s['verified_entries'],f'`{s["sha256"]}`'] for s in sources]))
    parts.append('''本轮使用分享字节的身份；旧 accepted 派生产物的私有来源身份不被改写。例如 S 的分享 manifest SHA 为 `2c5c6c3593b70dab6b3bdf2c1ea5425c49dc08d556235ceb2e211221720e8c3f`，私有 manifest 为 `51cd77db0f8748c3f6fb002a964a170208ddc783177f711a271d7c7f10402bfa`；其 observations 字节相同，不表示 manifest 或 ZIP 身份相同。原脱敏回执、私有索引和分享索引由输入原包及 `data.json` 并列引用。

旧 Ridge、旧 split、旧 test-used、失败成绩保持原样，仍是原 85/5 实验，不是本轮紧凑 Ridge。其后段 45 秒共同 20 点，B0 / B1 / 旧 TJ Ridge / 旧 full Ridge MAE 分别为 0.089050 / 0.116615 / 0.505719 / 0.230872°C；不与本轮不同分母的全段成绩直接排位。

## 2. 覆盖、时间与冻结合同

使用全部 4139 个约 1 秒 accepted 新 TJ，未用旧 5 秒预测起点表替代。应用固定 `engine_for` 的源质量、段隔离、平台／采样合同和控制资格；GPU 利用率并非灰箱必需输入。成功 PWM 的有效期为 2.5 秒，控制温度状态 7.5 秒，源功率按 5000 ms 减已有源年龄；重复包提高年龄的证据也保留。所有区间内实际到达的 fan/temp/source/tick 事件均检查，真实 fan 更新按到达时间插入传播，不能把下一点 PWM 倒填。

因此“两个温度点都有效”仍可能不构成连续可用区间。L 有 12 个区间内 TTL 到期记录，S 有 27 个；这些间隙不做插值。实际未知时不使用目标 PWM、模型 PWM 或 0。每个有效段单独估初态；短段仍进入自由响应拟合，只有具备 60 秒历史后才进入主 G2/Ridge 比较。
''')
    covrows=[]
    for r in data['runs']:
        ss=[s for s in coverage if s['run']==r['run']];pred=read(run/'evaluation'/('F-SL' if r['run']=='L' else 'F-LS')/'method-coverage.json')
        m=next(p for p in pred if p['h']==45 and p['method']=='G2-HOLD')
        covrows.append([r['run'],r['accepted'],r['accepted']-len(r['rejections']),len(ss),fmt(sum(s['span_s'] for s in ss)),sum(s['span_s']>=60 for s in ss),m['scored'],f'{100*m["scored"]/r["accepted"]:.1f}%'])
    parts.append(table(['run','accepted','当前资格有效','连续段','连续有效秒','≥60秒段','共同45秒点','占全部accepted'],covrows))
    parts.append('''拟合权重为 run 等权，再按负载／脉冲相关、回落、背景三个实际存在的宏类等权，类内按真实有效时间；末点无后续有效时长，时间权重为 0。短请求到结束后最多 30 秒／下次提交前归负载；既有回落标签优先于背景。长负载最初 60 秒另标升温，仅用于分层。人工秒级阶段边界不升级为精确事件边界。

约 1 秒采样不能确定亚秒热延迟。所有输入仍是接收时间近似，不是精确芯片功率积分或机械风速。数据、覆盖、角色及 spec 在首次真实拟合前哈希冻结；双方全部 G1/G2/Ridge 先冻结，才计算目标成绩。证据顺序见 `freeze.json`、`directions-frozen.json`、各 `evaluation-identity.json` 和 `readback-verification.json`。

![输入与严格连续覆盖](runs/main/charts/01-inputs-and-coverage.png)

各段起止、秒数、样本、原引用、宏类时长、60 秒初始化和可评价点见 [coverage.json](runs/main/coverage.json)。逐条异常资格与区间内 TTL 排除记录在 [data.json](runs/main/data.json) 的 `runs`；其 `segments.timeline` 保存输入年龄、引用与有效截止。模型拉起段保留在拟合与数据图中，但严格共同 45 秒集合没有该阶段覆盖，不能给它补一个模型胜负结论。

## 3. 实际模型与拟合

```text
G1: dT/dt = -(k0+k1*u)*(T-E_r) + b_g*P_g + b_c*P_c
G2: dTf/dt = -a*(Tf-Ts) + b_g*P_g + b_c*P_c
    dTs/dt = c*(Tf-Ts) - (d0+d1*u)*(Ts-E_r)
    yhat = Tf
```

u=成功 PWM/100。5V、gain、NVML 和其他温区只用于诊断；不相加 rail，不把 gain 当物理冷却输入，不补造环境或 TTP 温度。E 是等效边界参数；Ts 是未测潜在状态，允许高于 Tf。60 秒前缀不表示热平衡。

六组初值、参数边界、Huber 0.3°C 转折和预算完全使用冻结正文规范。目标是每段完整自由响应，不吸收后续真实 TJ；权重乘在 Huber rho 和导数外，保持物理转折一致。float64、真实 Δt、G1 解析解与 G2 稳定精确离散化；不求病态 A 逆，不使用显式 Euler。编译的 C 内核只加速等价传播，求解仍为 SciPy TRF。动态列数值差分，E/Ts 列使用精确仿射灵敏度；实际残差调用包含数值 Jacobian。
''')
    fitrows=[];parrows=[];initrows=[];total_s=0
    for eid in ('F-LS','F-SL','F-POOL'):
        for model in ('G1','G2'):
            a=read(run/'fits'/f'{eid}-{model}/model.json');trials=[read(run/'fits'/f'{eid}-{model}/N{k}.json') for k in range(1,7)]
            fitrows.append([eid,model,a['selected_seed'],a['parameter_count']]+[f'{t["J"]:.6f}' for t in trials])
            total_s+=sum(t['seconds'] for t in trials)
            parrows.append([eid,model,'; '.join(f'{k}={v:.7g}' for k,v in a['dynamic'].items()),'; '.join(f'{k}={v:.4f}' for k,v in a['parameters'].items() if k.startswith('E_'))])
            ts=[v for k,v in a['parameters'].items() if k.startswith('Ts_')]
            initrows.append([eid,model,len(ts),'—' if not ts else f'{min(ts):.3f}～{max(ts):.3f}',','.join(trials[int(a['selected_seed'][1:])-1]['boundary_parameters']) or '无',max(t['actual_residual_calls'] for t in trials)])
    parts.append(table(['实验','模型','选中','总参数数','N1 J','N2 J','N3 J','N4 J','N5 J','N6 J'],fitrows))
    parts.append('全部 36 次主拟合均有限且收敛。选中初值只由对应训练 J 决定，未按目标成绩选种子；没有扩边界、加模型族或无限扩搜索。各初值／终值、逐调用 J 轨迹、收敛码、nfev、实际调用、时间和贴边记录均在 `fits/*/N*.json`。\n\n')
    parts.append(table(['实验','模型','动态系数','训练侧等效边界°C'],parrows))
    parts.append(table(['实验','模型','慢初态个数','慢初态范围°C','选中解贴边项','六次最大残差调用'],initrows))
    parts.append('''每个训练 run 一个 E，每个独立有效段一个 Ts；不能把短段初态当独立热实验。完整逐段数值在模型 JSON 中。S-only G1 的 CPU 系数贴 0 不表示 CPU 不发热；S-only G2 的 a 贴 4 s⁻¹，不能扩大边界追成绩。

目标 E 只由首个 60 秒过去前缀校准，之后全 run 固定：F-LS 的 G1/G2 为 40.9405/43.1168°C；F-SL 为 29.0277/30.9228°C。这些不是测得室温。G2 两个首前缀的归一化奇异值比分别约 0.272/0.276，未触发预登记的 <1e-6 弱前缀降级；满秩不等于有物理准确度。新质量段只估状态，不重估 E。

Ridge 的 9/15 列、ΔTJ 标签、未惩罚截距及 alpha=λΣw 均按正文实现。均值／方差与 λ 只在拟合侧计算。完整有效段按时间排序轮流分至最多三折，段不跨两侧；近 0.01°C 平分时选择更强正则。各 h 单独建立标签、训练和选参；没有依赖 90 秒资格删除 45 秒答案。
''')
    ridge_rows=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        d=read(run/'fits'/f'{eid}-ridge.json')
        for name in ('R_TJ','R_IO'):
            for h,head in d['methods'][name].items():ridge_rows.append([eid,name,h,head['n'],len(head['groups']),head['lambda_']])
    parts.append(table(['实验','Ridge','秒','拟合起点','有效段组','λ'],ridge_rows))
    parts.append('''## 4. A：给定真实输入的热响应

**A-long** 在因果前缀结束后不再读取 TJ 修正状态；输入为该段已记录的实际功率／PWM。F-POOL 的动态参数、E 及段初态均曾用完整训练段拟合，所以只说明表达能力，不是因果前缀留出。没有拿每秒更新 TJ 的 B0 当整段自由仿真参照，也没有把 Ridge 递归伪造为热响应。
''')
    along=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        d=read(run/'evaluation'/eid/'A-long-metrics.json')['summary']
        along.append([eid,d['G2']['n'],fmt(d['G2']['seconds']),fmt(d['G1']['mae']),fmt(d['G2']['mae']),fmt(d['G1']['rmse']),fmt(d['G2']['rmse']),fmt(d['G2']['balanced_mae'])])
    parts.append(table(['实验','点','计权秒','G1 MAE','G2 MAE','G1 RMSE','G2 RMSE','G2均衡MAE'],along))
    parts.append('''单位°C。主 MAE/RMSE 按原始有效时间计权，均衡 MAE 按 run／宏类等权。F-SL 的 G2 自由响应偏差约 +13.638°C，不能靠滚动锚定当前 TJ 把这个结构／参数迁移问题藏起来。F-LS 的 G2 自由响应偏差约 +0.817°C，存在有方向性的漂移，不是仅随机噪声。

![不吸收后续TJ的自由响应](runs/main/charts/02-free-response.png)

**A-roll** 与 B 使用同一过去状态，只额外提供名义未来 15/45/90 秒内的记录输入。它只定位动态，不参加 B 的实时预测胜负榜。
''')
    ar=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        for r in read(run/'evaluation'/eid/'A-roll-metrics.json'):
            if r['scope']=='all':ar.append([eid,r['h'],r['metrics']['G1']['n'],fmt(r['metrics']['G1']['mae']),fmt(r['metrics']['G2']['mae']),fmt(r['metrics']['G2']['underprediction_max'])])
    parts.append(table(['实验','秒','共同点','G1 MAE','G2 MAE','G2最大欠预测'],ar))
    parts.append('''## 5. B：只用当时信息的未来预测

HOLD 固定当前两 rail 和成功 PWM；RELAX30 固定 PWM，功率各自以 30 秒时间常数衰减到 min(当前功率, 拟合侧 P10)。本轮各拟合集 P10 恰为 GPU 1.984W、CPU/SOC/MSS 5.952W；这个值来自拟合侧，不读取目标未来低负载。RELAX30 用增加指数输入状态的矩阵指数计算，并通过 0.1/0.05 秒步长减半核验。两策略独立报告，不逐点选优；不使用真实任务结束、未来输入或未来 TJ。

每 h 取同段 t+h 后第一份有效 TJ，容差 2 秒；所有方法按名义 h 预测，标签偏移一致。下表是最严格的八方法共同起点集合；B0/B1、加入 R_TJ、再加入 R_IO 的较宽集合另在逐层指标中完整保存。没有用不同分母的 MAE 排名。
''')
    for eid in ('F-LS','F-SL','F-POOL'):
        parts.append(f'### {eid}：'+('同机长→短开发迁移' if eid=='F-LS' else '时间反向工况压力检查' if eid=='F-SL' else '拟合内表达检查')+'\n\n')
        rr=[r for r in read(run/'evaluation'/eid/'B-metrics.json') if r['scope']=='all' and r['layer']=='all_methods']
        parts.append(table(['秒','共同点']+METHODS,[[r['h'],r['metrics']['B0']['n']]+[fmt(r['metrics'][m]['mae']) for m in METHODS] for r in rr]))
    parts.append('''### 45秒的场景差异与风险

以下场景仍使用各行相同集合；不能将行间当独立实验或事后选策略。时间均衡总分另列，防止长持续段或背景掩盖其他阶段。
''')
    regimes=[];risk=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        for r in read(run/'evaluation'/eid/'B-metrics.json'):
            if r['h']!=45 or r['layer']!='all_methods':continue
            if r['scope']=='regime':regimes.append([eid,r['value'],r['metrics']['B0']['n']]+[fmt(r['metrics'][m]['mae']) for m in ['B0','R_TJ','R_IO','G2-HOLD','G2-RELAX30']])
            if r['scope']=='all':
                for m in METHODS:risk.append([eid,m,fmt(r['metrics'][m]['balanced_mae']),fmt(r['metrics'][m]['p95_abs']),fmt(r['metrics'][m]['bias']),fmt(r['metrics'][m]['underprediction_p95']),fmt(r['metrics'][m]['underprediction_max'])])
    parts.append(table(['实验','场景','点','B0','R_TJ','R_IO','G2-HOLD','G2-RELAX30'],regimes))
    parts.append('''`isolated_pulse` 含预试与稀疏短题及规定尾窗；`continuous_short` 含连续题规定窗口；`long_rise` 是每个长任务起始 60 秒。初始空载与模型退出后的背景并未删除。

合并 G2-HOLD 45 秒时间 MAE 0.918°C，B0 1.133°C；run/宏类均衡后为 0.996°C 与 1.080°C，优势收窄。这个合并参数使用了两轮全记录；不能冒充未见验证。它在 idle 0.246°C，劣于 B0 的 0.194°C。RELAX30 对合并孤立脉冲 0.357°C，但长持续段 7.841°C，说明固定“很快结束”假设有明确代价。

长→短的 A-roll45 仍为 0.560°C，并未因提供未来输入自动变好到足以胜过 B0；反向 A-roll45 6.455°C 与 HOLD 6.941°C 都差。因此跨工况问题不能仅归因于不知道下一题何时结束。合并 A-roll45 0.290°C、HOLD 0.918°C 的差距则说明在动态表达较好的条件下，未来输入仍是重要限制。

![B类未来预测共同集合比较](runs/main/charts/03-causal-forecast-comparison.png)
''')
    parts.append(table(['实验','方法','均衡MAE','绝对误差P95','偏差','欠预测P95','最大欠预测'],risk))
    parts.append('''P95 为逐点经验分位，MAE/RMSE/偏差为有效时间权重；欠预测=max(真实−预测,0)，未截断原始误差。重叠预测高度相关，不提供伪精确置信区间。固件45秒参考仅对存在可信原值的同起点另作诊断，见 `diagnostics/firmware-reference.json`；其 API 时间仍与 TJ 时间不同，不能叫控制收益。

### 请求窗口和覆盖

每题前15秒、执行中、结束后0–15/15–45/45–90秒，各自的 raw accepted、正常起点、共同标签、误差与其他请求重叠标记均在 `evaluation/*/request-windows.json`。18 条正式请求执行区间都有约1秒源测量；但只有 S02/S03/S04/S05/D01 的执行中起点进入全部方法共同45秒评分，另有 P01 预试。其余不隐去，也不据此声称漏采或模型成功。

![每题共同45秒覆盖分子和原始分母](runs/main/charts/05-request-coverage.png)

连续问答只有 6 个主共同起点，起点层计分也包含其未来45秒内发生的其他题，不能归因到单题热量。扩成1秒起点未取消60秒历史、真实质量断点及未来标签约束；当前覆盖不足的具体来源已列明，不恢复失效输入凑数。

## 6. 辨识、初态与数值诊断

**局部优化不是主要失败解释。** 双向24个有限近优候选都落在训练 J 的5%范围内；相对动态参数差异最大约0.55%，同目标45秒 HOLD 预测相对选中解的最大差约0.0037°C。六初值没有展示一个被漏掉的明显更优盆地；仍不证明全局最优或物理唯一。
''')
    specrows=[]
    for r in params:
        specrows.append([r['experiment'],r['model'],f'{r["weighted_raw_residual_full"]["condition"]:.3g}',r['weighted_raw_residual_full']['numerical_rank'],f'{r["projected_dynamic"]["condition"]:.3g}',r['projected_dynamic']['numerical_rank']])
    parts.append(table(['实验','模型','含nuisance条件数','全矩阵数值秩','投影后动态条件数','动态秩'],specrows))
    parts.append('''灵敏度来自加权原始摄氏残差，未用 Huber 改写 Jacobian。动态参数按冻结尺度归一化，E/Ts 使用20°C尺度；投影掉 nuisance 列空间后单列动态 SVD。完整参数方向、奇异值与尺度保存在 `diagnostics/parameters.json`。S/POOL 的全矩阵极病态，部分极短段慢初态缺乏带时间权重的动态观测支持；动态投影满秩也不是热参数真实可辨识的证明。

G2 的 L-only 快时间尺度约6.8秒、慢尺度随 u 约86–194秒；S-only 快尺度约0.24秒，小于约1秒采样，慢尺度在实际PWM范围约303–685秒；POOL 快尺度约13秒，慢尺度在实际PWM范围约105–266秒。S-only 的快尺度没有被充分分辨，不能把 a=4 当已测到的热常数。u=0 的外推更慢，也没有成为现场数据支持的观测。

**状态窗口变长没有修好迁移。** 在同一 ≥180 秒起点集合上，G2-HOLD45 的普通逐点 MAE：F-LS 60秒/180秒为0.735/1.000°C（n=530），F-SL 为8.664/13.394°C（n=792）。E 与动态参数都保持60秒主版本冻结值；没有按点选窗口。说明更长历史不能补偿错误的等效动态／边界假设，并可能累积其偏差。没有做可选的180秒重新校准E副本，也没有据结果改主方案。

![参数灵敏度与固定初态窗口检查](runs/main/charts/04-identifiability-and-state.png)

**输入分离能力有限。** L 的 GPU/CPU rail 相关0.963，S为0.990；CPU与5V相关0.9988/0.9942。标准化 GPU/CPU/5V/PWM 矩阵条件数约57/33。各 rail 仍分别保留，不能永久宣称某一路无热贡献。闭环 PWM 与温度／任务历史纠缠，gain只作背景线索。

**残差有结构。** G2自由响应残差45秒自相关在 F-LS/F-SL 约0.685/0.970，POOL约−0.033。合并降低了长时间残差相关，但短→长持续高估说明短脉冲侧的稳态热增益／散热动态无法迁移；它不是靠当前TJ锚定能解决的问题。各阶段残差、5V/gain/温区相关、峰温和尾段误差均保存，相关性不被解释为积灰、材料老化或已确定的散热效率。

**TJ≈快状态只是局部近似。** 有效样本中 L 的已报告分区最高值以GPU占2441/2508，34次主导温区切换；S为1605/1606，1次切换。TJ与这些已报告分区最大值的绝对差最大0.844/0.250°C。因此既不能把所有TJ误差归到同一固定GPU温区，也未将真值换成GPU以改善成绩；详见逐点 `hotspots.jsonl` 与按热点残差。

**一次预登记的风扇嵌套诊断已完成。** F-POOL G2固定 d1=0，从主最优解单次重拟合，其 J 从1.128863升至1.507627（+33.55%），且收敛。当前PWM项确实改善该模型对现有闭环记录的拟合，但这不能识别独立风量因果效应，更不能推出调低PWM仍安全。

## 7. 验证、资源与实现偏差

新增研究测试 **12/12通过**；复用链相关离线回归 **11/11通过**。覆盖单位和原引用、G1/G2精确传播／近重根／小Δt、温度平移、非平衡热初态、充分激励合成拟合、弱激励不同系数的同响应、未来TJ/输入/结束时刻反例、独立时距标签、真实质量断点与恢复、Huber权重、Ridge标准化／alpha、仿射 nuisance 灵敏度。没有重跑全仓189项或现场故障矩阵。

保存结果另以 SciPy 增广矩阵指数独立复算 **1766** 个 HOLD 传播实例，最大差 **4.30e−11°C**；全部共同集合ID、标签、B各层指标和冻结参数哈希重新核对。三个实验视图中保留 **990** 条有45秒而无90秒答案的记录（POOL会重复引用同一原点，因此不是990个独立样本）。

评价启动曾发现 G1 后续段固定E、无待估参数时的空矩阵分支错误；已加专门回归修复。发生在目标成绩产生前，未重新训练或改变已冻结双向参数。`finish-attempt-01.log` 和 `implementation-repair-01.json` 保留。另修正绘图对缺PWM字段的显示，仍画缺口；没有补回数据。没有单位修正、范围扩张或追加主模型搜索。
''')
    resources=[read(run/f'resource-{stage}.json') for stage in ['directions','finish']]
    parts.append(f'执行环境：{env["machine"]}，{env["platform"]}，Python {env["python"].split()[0]}；'+', '.join(f'{k} {v}' for k,v in env['dependencies'].items())+'。\n\n')
    parts.append(f'核心数据准备／双向拟合和评价／合并／诊断两阶段合计 **{sum(r["wall_s"] for r in resources):.2f}秒**，其中36次主拟合的求解记录合计 **{total_s:.2f}秒**；记录峰值RSS **{max(r["ru_maxrss_native"] for r in resources)/1024**2:.1f}MiB**，BLAS 1线程。首次完整L残差约0.00057秒。以上不含交互实现、阅读、测试、绘图与打包时间，属于本机CPU结果，**不是N305成绩**。绘图使用已有独立环境，版本单列；未安装或升级生产依赖。\n\n')
    parts.append('''## 8. 最多三项有目标的下一轮补测建议（本轮未执行）

### 1）补上中等时长，区分短脉冲热增益与持续响应

- **缺口／可证伪解释：**短→长即使给真实输入也失败，而短侧 a 贴边；现有近2秒脉冲与数百秒持续负载之间缺少辨识信息。若同一冻结候选在中等负载持续中系统高估、结束后又系统偏离，即推翻“只有未知结束时刻导致B差”的解释。
- **改变／保持：**改变任务持续时间为约20/60/180秒，顺序事先固定并保留完整回落；保持同设备、模型、客户端任务类别、AUTO控制与已有配置，不要求功率恰为常数，实测两rail作输入。
- **记录／时间：**完整约1秒TJ、独立rail、成功PWM及其源年龄/引用、控制资格、原请求起止；增加同期进风附近环境温度和此前10分钟热前史。单个完整过程约35–45分钟，包含首尾各5–10分钟背景，回落不冒称达到平衡。
- **保护／停止／回退：**保留原AUTO与保护；若保护/失温/故障触发，停止当前测试请求并保存原日志，等待原系统正常恢复。若出现持续热告警或异常升温，停止整个负载流程，不手调PWM、不改保护。回退仅回到原日常空闲/AUTO状态。
- **用户只需做什么：**下一轮另行授权后确认可用时段及相同任务条件，按一张预先固定的20/60/180秒操作卡启动／停止任务，放置并记录环境温度。无需修改风扇设置或拆模组。

### 2）相同任务、不同热前史，区分边界与未观测慢初态

- **缺口／可证伪解释：**60→180秒窗口反而变差，E与慢态均非实测；当前难分“热前史改变”与“固定等效边界不适用”。若相同输入附近的残差随已记录环境或前史稳定改变，且冻结参数／过去窗口无法重现，则推翻一套固定边界即可迁移的假设。
- **改变／保持：**对同一个约60–90秒任务，分别在较长空闲后和一次正常负载回落早期启动；保持任务、设备、AUTO及环境布置相同，仅改变起始热前史。不能把空闲若干分钟直接命名为冷机平衡。
- **记录／时间：**每种前史保留至少10分钟先行记录、任务和5–10分钟后续，合计约40–50分钟；环境温度必录。可选在不拆模组、不扰动TIM的外部可接近位置记录散热体表面温度，明确不是内部TTP。
- **保护／停止／回退：**同第1项的既有AUTO保护与停止负载规则；若第二次启动前仍有热告警/资格异常，则取消该次，不绕过保护凑成对照。恢复日常空闲/AUTO，无配置回滚动作。
- **用户只需做什么：**另行授权并按两种前史的固定操作卡执行；若加外部测点，只放置安全、可移除的外部探头并记录位置，不接入设备控制。

### 3）保留一个全新的完整过程，只用于确认

- **缺口／可证伪解释：**本轮两过程及合并参数都已用于研究，不能给独立确认。若提前冻结的候选在新过程的共同45秒集合、动态和背景分层仍不如B0，或欠预测尾部恶化，则否定推进该候选的预测收益主张；不能用新过程继续选初值后又称它未见。
- **改变／保持：**新完整过程包含待机、中等持续任务、孤立短题、连续短问答与最终回落；保持设备／记录合同及AUTO。候选、输入情景、过去窗口、评分口径和成功条件先冻结。
- **记录／时间：**完整原始记录、请求元数据、输入年龄与环境／热前史，约30–40分钟。连续题的有效传播／标签覆盖不足时应报告“未完成确认”，不得取消资格规则。
- **保护／停止／回退：**沿用原保护，异常时停止请求、留存日志、恢复日常空闲。确认只做旁路预测和观察，没有调PWM权限。
- **用户只需做什么：**在前两项结论复审、候选再次冻结后，另行批准这一个确认过程；运行前不向预测器透露实际未来结束时间，不人工补写遗漏样本。

当前不建议直接开展受控PWM改动。d1=0损失表明PWM项有观测拟合价值，但尚未把风扇因果作用与闭环／任务结束分开；不能切MANUAL并假定AUTO保护仍在。

## 9. 复审入口与停止状态

- [研究入口和复跑说明](README.md)、[冻结规格](experiment-spec.json)、`research-code.patch`。
- `runs/main/fits/`：36次主尝试、6个灰箱模型、3套Ridge、唯一d1=0；全部模型 `deployable=false`。
- `runs/main/evaluation/`：A-long、A-roll、B的逐点预测、状态证据、分层指标、共同集合ID、方法覆盖、请求周边和初态敏感性。
- `runs/main/diagnostics/`：输入相关、参数与初态SVD、时间尺度、近优多解、原始残差、热点、标签偏移及固件数值参考。
- `runs/main/charts/`：5幅PNG/SVG；所有误差单位°C，输入rail分开。
- `*-tests-*.log`、`related-regression.log`、`readback.log`、失败日志、环境／资源、`protected-after.json` 和 ZIP 内 `SHA256.json`。

原三大ZIP只通过SHA引用，不递归收入新证据包；独立重跑者从原交接包 `inputs/` 取得。新运行必须使用新目录。保存模型重放不等于可以交给生产加载器或现场部署。

状态：implementation / numeric_fit / response_evaluation 已完成；causal_forecast 为开发回放已完成；**target_validation=not_performed，control_authorization=none**。完成本轮实际拟合、报告与证据后停止，交回复审。

## 附：逐有效段A-long结果

下表的 first_ref/last_ref 均可在逐点JSONL回到原始记录；所有实际初始化范围和秩在各实验 `calibrations.json`，每个滚动起点则见 `states.jsonl`。峰温误差是预测峰值−实测峰值，尾部偏差取段末60秒内，均未反馈校正状态。
''')
    ar=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        for s in read(run/'evaluation'/eid/'A-long-metrics.json')['segments']:
            ar.append([eid,s['segment'],s['n'],fmt(s['seconds']),fmt(s['metrics']['G1']['mae']),fmt(s['metrics']['G2']['mae']),fmt(s['metrics']['G2']['rmse']),fmt(s['peak_error']['G2']),fmt(s['tail_bias']['G2']),s['first_ref'].split('/')[-1]+' → '+s['last_ref'].split('/')[-1]])
    parts.append(table(['实验','段','点','自由传播秒','G1 MAE','G2 MAE','G2 RMSE','G2峰差','G2尾偏','原始引用'],ar))
    args.output.write_text('\n'.join(parts))
    print(args.output)


if __name__=='__main__':main()
