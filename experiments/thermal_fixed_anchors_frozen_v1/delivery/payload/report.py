"""Chinese figures and report from saved frozen comparison results; no model calculation."""
import argparse
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
from prepare import read,write,sha
from run_study import lines,seconds,ROOT

NAMES={'0-background':'背景','1-work':'首次单路','2-recovery':'回落90秒','3-work':'两路',
       '4-recovery':'回落240秒','5-work':'四路','6-recovery':'回落120秒','7-work':'重复单路',
       '8-final_recovery':'最终回落','preparation_or_tail':'准备'}
COLORS={'AUGMENTED-KF':'#136b77','CONDITIONAL-HOLD':'#789299','QS':'#d5a100','LP30':'#9e65ba','LP120':'#4385b6',
        'B0':'#777777','B1':'#c46947'}


def configure():
    candidates=[Path('/System/Library/Fonts/STHeiti Light.ttc'),Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    font=next((p for p in candidates if p.exists()),None)
    if font:
        fontManager.addfont(str(font))
        plt.rcParams['font.family']=FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,'axes.titlesize':12,
                         'figure.facecolor':'#ffffff','axes.spines.top':False,'axes.spines.right':False,
                         'svg.fonttype':'path'})
    return str(font) if font else 'system default; Chinese font must be provided for readable exported figures'


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=170,bbox_inches='tight')
    fig.savefig(out/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def decorate(ax,phases,origin,labels=False):
    for p in phases:
        left=(p['start']-origin)/60;right=(p['end']-origin)/60
        if p['stage']['kind']=='work':
            ax.axvspan(left,right,color='#b8d7dc',alpha=.25,zorder=-5)
        ax.axvline(left,color='#acb5b8',lw=.6,alpha=.7)
        if labels:
            ax.text((left+right)/2,1.025,NAMES[p['name']],transform=ax.get_xaxis_transform(),ha='center',fontsize=8)
    ax.grid(alpha=.17)
    ax.set_xlim(-.15,(phases[-1]['end']-origin)/60+.15)


def figures(out):
    folder=out/'figures';folder.mkdir(exist_ok=True)
    font=configure()
    samples=list(lines(out/'samples-and-causal-states.jsonl'))
    long=list(lines(out/'A-long.jsonl'))
    points=list(lines(out/'predictions.jsonl'))
    signals=list(lines(out/'signal-frames.jsonl'))
    phases=read(out/'phases.json');origin=phases[0]['start']
    x=np.array([(a['wall']-origin)/60 for a in samples]);lx=np.array([(seconds(a['utc'])-origin)/60 for a in long])
    surf=list(lines(out/'surface-diagnostic-points.jsonl'));ss=[p for p in surf if p['scenario_added_seconds']==0]
    sx=np.array([(p['scenario_wall']-origin)/60 for p in ss])
    fig,axes=plt.subplots(4,1,figsize=(14,11),sharex=True,gridspec_kw={'height_ratios':[2,1.7,1.2,.9]})
    axes[0].plot(x,[a['current'] for a in samples],color='#292d32',lw=1.1,label='实测 TJ')
    axes[0].plot(x,[a['states']['AUGMENTED-KF']['Tf_C'] for a in samples],color=COLORS['AUGMENTED-KF'],lw=.9,label='KF Tf（持续吸收过去/当前TJ）')
    axes[0].plot(lx,[a['Tf_C'] for a in long],color='#c76736',lw=1.1,label='A-long Tf（前60秒后不再吸收TJ）')
    axes[0].set_ylabel('TJ / Tf（°C）');axes[0].legend(ncol=3,fontsize=9,loc='upper left')
    axes[0].set_title('图1｜冻结模型能跟随完整冷热过程，但自由响应有偏差；Ts仍是潜在状态',pad=29)
    axes[1].plot(x,[a['states']['AUGMENTED-KF']['Ts_C'] for a in samples],color=COLORS['AUGMENTED-KF'],label='KF Ts')
    axes[1].plot(lx,[a['Ts_C'] for a in long],color='#c76736',lw=1,label='A-long Ts')
    axes[1].plot(x,[a['states']['CONDITIONAL-HOLD']['Ts_C'] for a in samples],color=COLORS['CONDITIONAL-HOLD'],lw=1,label='不校正Ts/E的对照')
    axes[1].plot(sx,[p['CH1_C'] for p in ss],color='black',lw=1.2,label='CH1局部鳍片（未校准时钟）')
    axes[1].set_ylabel('状态 / 局部表面（°C）');axes[1].legend(ncol=4,fontsize=9,loc='upper left')
    axes[2].plot(x,[a['states']['AUGMENTED-KF']['conditional_inputs_rails_W_PWM'][0] for a in samples],lw=.9,label='GPU rail')
    axes[2].plot(x,[a['states']['AUGMENTED-KF']['conditional_inputs_rails_W_PWM'][1] for a in samples],lw=.9,label='CPU/SOC/MSS rail')
    axes[2].set_ylabel('独立功率输入（W）');axes[2].legend(ncol=2,fontsize=9)
    axes[3].plot(x,[a['states']['AUGMENTED-KF']['conditional_inputs_rails_W_PWM'][2]*100 for a in samples],color='#648653',lw=1,label='记录中的成功PWM')
    axes[3].set_ylabel('PWM（%）');axes[3].set_xlabel('相对背景阶段开始的时间（分钟）');axes[3].legend(fontsize=9)
    for i,ax in enumerate(axes):decorate(ax,phases,origin,labels=i==0)
    fig.subplots_adjust(hspace=.13)
    save(fig,folder,'01-全程热状态与输入')

    common=[r for r in points if r['h']==45 and r['label'] and 'B1' in r['baselines'] and len(r['A_roll'])==5 and len(r['B_HOLD'])==5]
    fig,axes=plt.subplots(2,1,figsize=(14,8.5),gridspec_kw={'height_ratios':[1.6,1]})
    px=[(seconds(r['utc'])-origin)/60 for r in common]
    for kind,color,label in [('A_roll',COLORS['AUGMENTED-KF'],'A-roll：实际未来输入'),('B_HOLD','#c76736','B-HOLD：保持当前输入')]:
        axes[0].plot(px,[r[kind]['AUGMENTED-KF']-r['label']['value'] for r in common],lw=.9,color=color,label=label)
    axes[0].axhline(0,color='#333333',lw=.7)
    axes[0].set_ylabel('预测 − 实测TJ（°C）\n负值表示低估');axes[0].set_xlabel('起点时间（分钟）')
    axes[0].legend(ncol=2);decorate(axes[0],phases,origin,True)
    axes[0].set_title('图2｜输入已知时的热响应准确度，与真实未来HOLD预测分开评价',pad=30)
    ms=read(out/'metrics-common.json')
    lookup={(r['kind'],r['h']):r for r in ms if r['phase']=='all' and r['qualification']=='all_available' and len(r['branches'])==5}
    configs=[('A_roll','AUGMENTED-KF','G2 KF · A',COLORS['AUGMENTED-KF']),('B_HOLD','AUGMENTED-KF','G2 KF · B','#c76736'),
             ('B_HOLD','LP30','LP30 · B',COLORS['LP30']),('B_HOLD','LP120','LP120 · B',COLORS['LP120']),('B_HOLD','B0','保持TJ · B',COLORS['B0'])]
    xpos=np.arange(3);width=.15
    for j,(kind,key,label,color) in enumerate(configs):
        vals=[(lookup[(kind,h)]['errors'] if key in lookup[(kind,h)]['errors'] else lookup[(kind,h)]['baselines'])[key]['MAE_C'] for h in (15,45,90)]
        rects=axes[1].bar(xpos+(j-2)*width,vals,width,color=color,label=label)
        axes[1].bar_label(rects,fmt='%.2f',fontsize=8,padding=2)
    axes[1].set_xticks(xpos,['15秒','45秒（主时距）','90秒']);axes[1].set_ylabel('共同集合 MAE（°C）');axes[1].legend(ncol=5,fontsize=9,loc='upper left')
    axes[1].set_ylim(0,5.2);axes[1].grid(axis='y',alpha=.17)
    fig.subplots_adjust(hspace=.43)
    save(fig,folder,'02-热响应与真实未来预测')

    fig,axes=plt.subplots(2,1,figsize=(14,9),sharex=True)
    axes[0].plot(sx,[p['CH1_C'] for p in ss],color='black',lw=1.5,label='CH1局部表面（原始名义时间）')
    for key,label,color in [('KF_Ts','G2 KF Ts',COLORS['AUGMENTED-KF']),('QS','QS（同一因果E）',COLORS['QS']),('LP30','LP30',COLORS['LP30']),('LP120','LP120',COLORS['LP120'])]:
        axes[0].plot(sx,[p['absolute_models'].get(key,np.nan) for p in ss],color=color,lw=1,label=label)
        axes[1].plot(sx,[p['relative_models_C'].get(key,np.nan) for p in ss],color=color,lw=1,label=label)
    for offset,alpha in [(0,1),(-3,.4),(-4,.25)]:
        rows=[p for p in surf if p['scenario_added_seconds']==offset]
        axes[1].plot([(p['scenario_wall']-origin)/60 for p in rows],[p['relative_surface_C'] for p in rows],
                     color='black',alpha=alpha,lw=1.3,label='CH1：0/−3/−4秒假设' if offset==0 else None)
    axes[0].set_ylabel('绝对值（°C）');axes[0].set_title('图3｜局部鳍片的升温较小；潜在Ts不能直接当作实测鳍片或已验证热容',pad=30)
    axes[0].legend(ncol=3,fontsize=9,loc='upper left')
    axes[1].set_ylabel('相对同一背景参照点的变化（°C）');axes[1].set_xlabel('相对背景开始（分钟）')
    axes[1].legend(ncol=5,fontsize=9,loc='upper left')
    axes[1].text(.01,.02,'仅一次基准相减；不缩放、不按阶段平移、不按曲线找时间偏移。3种时间情景不是误差界。',transform=axes[1].transAxes,fontsize=9)
    for i,ax in enumerate(axes):decorate(ax,phases,origin,labels=i==0)
    fig.subplots_adjust(hspace=.18)
    save(fig,folder,'03-局部鳍片与慢态独立对照')

    degraded=next(a for a in samples if a['states']['AUGMENTED-KF']['phase']=='degraded')
    centers=[samples[0]['t'],degraded['t']]
    fig,axes=plt.subplots(2,2,figsize=(13,7.5),sharex='col',gridspec_kw={'height_ratios':[2,1]})
    for col,center in enumerate(centers):
        chosen=[a for a in signals if center-(0 if col==0 else 12)<=a['t']<=center+(30 if col==0 else 18)]
        t=np.array([a['t']-center for a in chosen]);v=np.array([a['values']['KF_Ts'] if a['values']['KF_Ts'] is not None else np.nan for a in chosen]);sd=np.array([a['state_std_C'][1] if a['state_std_C'] else np.nan for a in chosen])
        axes[0,col].plot(t,v,color=COLORS['AUGMENTED-KF'],label='KF Ts')
        axes[0,col].fill_between(t,v-2*sd,v+2*sd,color=COLORS['AUGMENTED-KF'],alpha=.16,label='±2倍内部标准差')
        axes[0,col].set_title('图4a｜仅一次冷启动' if col==0 else '图4b｜四路中的短暂控制上下文未知')
        axes[0,col].set_ylabel('潜在Ts（°C）');axes[0,col].legend(fontsize=9)
        axes[1,col].step(t,[int(a['model_phase']=='tracking') for a in chosen],where='post',label='tracking',color=COLORS['AUGMENTED-KF'])
        axes[1,col].step(t,[int(a['safety']['confirmed_normal_now'])-.04 for a in chosen],where='post',label='上下文已确认',color='#c76736',ls='--')
        axes[1,col].set_yticks([0,1],['否','是']);axes[1,col].set_xlabel('相对该事件的秒数');axes[1,col].legend(ncol=2,fontsize=9,loc='lower right')
        for ax in axes[:,col]:ax.grid(alpha=.17)
    fig.suptitle('状态可计算、tracking和现场准入各有合同；内部标准差未校准，不能解释成95%置信区间',fontsize=11,y=.99)
    fig.tight_layout(rect=[0,0,1,.95])
    save(fig,folder,'04-冷启动与质量边界')
    write(out/'figure-generation.json',dict(font=font,figures=4,formats=['PNG','SVG'],scientific_data_changed=False))


def report(out):
    ms=read(out/'metrics-common.json');al=read(out/'A-long-summary.json');rep=read(out/'state-replay-verification.json')
    surface=read(out/'surface-summary.json');env=read(out/'environment-resource.json');state=read(out/'state-diagnostics.json')
    info=read(ROOT/'inputs/context/completed-run-verification.json')
    def row(kind,h,phase='all'):
        return next(r for r in ms if r['kind']==kind and r['h']==h and r['phase']==phase and r['qualification']=='all_available' and len(r['branches'])==5)
    def n(v):return f'{v:.3f}' if v is not None else '—'
    table=[]
    for h in (15,45,90):
        for kind in ('A_roll','B_HOLD'):
            r=row(kind,h)
            table.append(f"| {h}秒 | {'A-roll' if kind=='A_roll' else 'B-HOLD'} | {r['n']} | "+' | '.join(n(r['errors'][b]['MAE_C']) for b in ('AUGMENTED-KF','CONDITIONAL-HOLD','QS','LP30','LP120'))+' | '+n(r['baselines']['B0']['MAE_C'])+' | '+n(r['baselines']['B1']['MAE_C'])+' |')
    stage=[]
    for p in read(out/'phases.json'):
        r=row('B_HOLD',45,p['name']);ar=row('A_roll',45,p['name'])
        stage.append(f"| {NAMES[p['name']]} | {r['n']} | {n(ar['errors']['AUGMENTED-KF']['MAE_C'])} | {n(r['errors']['AUGMENTED-KF']['MAE_C'])} | {n(r['baselines']['B0']['MAE_C'])} |")
    border=read(out/'stage-boundary-metrics.json')
    strata=[]
    for kind in ('A_roll','B_HOLD'):
        for relation in ('same_stage','crosses_stage'):
            r=next(x for x in border if x['kind']==kind and x['h']==45 and x['phase']=='all' and x['stage_relation']==relation)
            strata.append(f"| {kind} | {'同阶段' if relation=='same_stage' else '跨阶段'} | {r['n']} | {n(r['errors']['AUGMENTED-KF']['MAE_C'])} | {n(r['baselines']['B0']['MAE_C'])} |")
    absolute=read(out/'surface-phase-diagnostics.json')
    shape=[]
    for offset in (0,-3,-4):
        lookup={r['series']:r for r in absolute if r['phase']=='all' and r['scenario_added_seconds']==offset}
        shape.append(f"| {offset}秒 | "+' | '.join(n(lookup[b]['mean_absolute_relative_discrepancy_C']) for b in ('KF_Ts','QS','LP30','LP120'))+' |')
    coverage=read(out/'coverage-own.json');cov=[]
    for h in (15,45,90):
        a=next(r for r in coverage if r['kind']=='A_roll' and r['h']==h and r['branch']=='AUGMENTED-KF')
        b=next(r for r in coverage if r['kind']=='B_HOLD' and r['h']==h and r['branch']=='AUGMENTED-KF')
        cov.append(f"| {h}秒 | {a['all_source_valid_TJ']} | {a['labels']} | {a['scored']} | {b['scored']} | {row('B_HOLD',h)['n']} |")
    text=f'''# TTO-首轮fixed-anchors冻结模型对照报告

本轮已完成离线重放与比较，未重训模型。冻结G2状态接口能复现现场保存的8,677条状态；在2,706个有效TJ起点中，2,696个为tracking、9个冷启动过渡、1个degraded，整个实验仅冷启动一次。

给定真实功率/PWM时，45秒热响应MAE为**0.334°C**；只保持预测时当前输入时，45秒MAE为**1.544°C**，优于保持TJ的**2.230°C**。但跨工作阶段的45秒HOLD MAE为**8.871°C**，比保持TJ的8.183°C还差；最坏低估**12.712°C**。该模型对阶段内热响应有价值，当前HOLD假设不适合承诺任务启停附近的未来温度。

CH1确认记录到局部鳍片40.44—47.96°C；Ts仍是潜在状态，幅度及回落并未与该测点等同。唯一推荐下一步是：**在这份记录上恢复有限的因果未来输入策略对照，优先检验启停不确定性；继续冻结状态模型，先做离线验证。** 本轮没有启动该开发、实测或控制。

## 本轮资料和实现身份

- 唯一run：`5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3`；command：`fixed-anchors-20261019-658d6dcc-9a5e-4cbe-ab17-7cf70eda7cf7`。
- 现场时间为2026-10-19北京时间17:41:14.198—18:26:28.851，共{info['elapsed_s']:.3f}秒；四个工作块实际完成23/32/101/23条请求，共179条，均有DONE、finish_reason和usage。四路指客户端槽位，不证明GPU四路物理并行。
- 主模型SHA：`{read(ROOT/'spec.json')['model_sha256']}`。
- 观察器spec SHA：`{read(ROOT/'spec.json')['observer_spec_sha256']}`。
- 原生源码聚合SHA：`{read(ROOT/'spec.json')['native_source_sha256']}`；模型比较采用完整封存closeout源码中的原生处理器、I02、SavedStream与ThermalObserver，未拿旧原型替代。
- 本轮比较spec SHA：`{sha(ROOT/'spec.json')}`，在重放/评分前冻结，未改。阶段交界的细分是首次得分后的有限描述性诊断，另存`descriptive-diagnostics-spec.json`，不冒充预登记，不选模型或改参数。
- 当前run是一次连续开发热过程。此前θ已用L/M/S拟合，本轮只是新run上的冻结检验，179条请求不是179个独立实验。旧模型、旧结果及test-used未改。

入口199项、native索引7项、仪表sidecar19项均逐项核SHA和字节；这些索引互相有包含关系，不能相加当样本数。原始远端快照SHA为`314822d18ac13b2605c4a66fa586e5be3c9a64012b39885b75190420adf01b59`。证据保留足够独立重放的当前run输入，未递归打包历史ZIP。

## 状态重放、质量和初始化

8,677条原始事件各经过一次原生处理，I02读取同一次处理结果；I02及状态结构/资格逐条与现场保存结果核对。最大状态浮点差为{rep['max_state_float_abs_difference']:.3g}，低于预定1e-8容差。原生日志的6条重复记录保留，没有当作新TJ；结束断连也保留，不能据此抹去整轮。

控制、采样、TTL没有变化。全程以实际独立GPU rail、CPU/SOC/MSS rail及成功PWM为输入；CPU/SOC/MSS不叫纯CPU，没有把5V随意相加或把gain当冷却量。四路阶段约1.012秒`control_context_unready`暂停原样保留。它对应一次有效TJ起点degraded，不被改成正常，不因此重置慢态。现场已有的联合准入时长{info['measurement_model_context_time_coverage']['joint_ready_s']:.3f}秒与这里的逐点tracking是不同口径。HTTP无超时及一次fan跳过只能描述本轮，不能证明旧超时根因已修复。

冷启动采用原L/S先验；E是等效边界而非本轮室温。状态根据已经到达的TJ顺序校正，θ不更新。E在{state['E_range_C'][0]:.3f}—{state['E_range_C'][1]:.3f}°C之间，不能解读成现场环境变化。Ts在{state['Ts_range_C'][0]:.3f}—{state['Ts_range_C'][1]:.3f}°C之间，没有实测Ts真值。本轮没有用旧M的24°C或CH1纠偏。

滤波后的Tf与当前TJ平均相差{state['posterior_Tf_vs_current_TJ']['MAE_C']:.3f}°C，这个数含当前温度反馈，**不是未来预测成绩**。±2倍内部标准差只反映冻结假设下的状态尺度，未涵盖θ、时钟或未来负载误差，未校准成95%置信区间。

## A：已知输入下的热响应

A-long先用过去{al['prefix_s']:.3f}秒得到状态，随后冻结Tf/Ts/E初态，用真实未来功率/PWM连续传播{al['final_free_span_s']:.3f}秒；不再吸收TJ、不再更新E，不在工作块间重置。2,646个有效温度答案的MAE为{al['error']['MAE_C']:.3f}°C，平均误差{al['error']['mean_error_C']:+.3f}°C，最大低估{al['error']['max_underprediction_C']:.3f}°C。持续偏高说明不能用不断吸收TJ的平滑结果掩盖自由响应偏差。60秒初始化没有被称为热平衡。

A-roll在每个起点用相同实测当前TJ、各自因果Ts/E，给定真实未来输入；预测段不吸收未来TJ。只要实际输入路径或原TTL不支持，该A答案即不可用。它是R2物理输入诊断，已观测上下文另列；不是旧严格合同分数的覆盖写入。

## B：只有当时信息的HOLD预测

B使用起点已经到达的两条rail和已知/明确条件保持PWM，不读未来功率、温度、实际任务结束或CH1。沿用本轮R2冻结合同的HOLD，没有事后在未来输入情景间择优。B0保持当前TJ；B1沿用过去30秒端点趋势、最少10秒支持，跨源/长缺口不拼接。

表中数值都是TJ MAE（°C），各行使用共同起点/标签。QS/LP30/LP120复用已冻结公式和30/120秒常数，使用同一因果KF E与当前TJ/PWM，再替代Ts；它们是明确标记的current-E对照，不冒充此前fixed-E旧分数。CONDITIONAL-HOLD保持同一冻结动力学和输入规则，只不以TJ残差校正Ts/E。

| 时距 | 评价 | 共同点 | G2 KF | 无Ts/E残差校正 | QS | LP30 | LP120 | B0 | B1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

G2 KF在15/45秒优于这里的简单慢态对照；90秒HOLD的LP120为3.432°C，优于G2 KF的3.540°C，因此没有“所有时距胜出”的结论。45秒G2 KF的P95低估为{row('B_HOLD',45)['errors']['AUGMENTED-KF']['P95_underprediction_C']:.3f}°C，低估超过2°C的比例为{row('B_HOLD',45)['errors']['AUGMENTED-KF']['fraction_underprediction_gt_2C']*100:.2f}%；这是描述统计，不是安全阈值。

| 时距 | 全部有效TJ | 有效标签 | KF A可评分 | KF B可评分 | 含B1共同集合 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(cov)}

15/45/90秒分别判断，最后一段没有90秒答案不会删掉仍有45秒答案的点。每个共同集合的原始引用和SHA在逐点结果/metrics中；样本时序相关，不提供虚假的独立样本显著性。

## 场景差异和最差情况

以下以起点所在阶段分组，标签可能在下一阶段，所以背景阶段的未来预测误差包含负载突然到来的影响，不能理解为“纯待机误差”。

| 起点阶段 | 45秒共同点 | A-roll KF | B-HOLD KF | B0 |
|---|---:|---:|---:|---:|
{chr(10).join(stage)}

| 45秒评价 | 起点到标签 | 点数 | KF MAE | B0 MAE |
|---|---|---:|---:|---:|
{chr(10).join(strata)}

最坏45秒低估发生在北京时间18:02:39.835，240秒回落即将进入四路工作前：预测46.788°C，实测答案59.500°C，低估12.712°C。这个点没有删除。跨阶段集合含未来实际阶段信息，只用来解释评分，未作为B输入。阶段内HOLD MAE0.392°C、A-roll0.272°C；跨阶段HOLD8.871°C、A-roll0.727°C。同初态只改变未来输入条件便出现大差别，说明这轮的主要预测短板在启停/未来输入假设；A仍存在短峰残差，不能宣称结构已完美。

重复单路的固定+60至+300秒窗口，两条rail平均值分别约26.25/17.85W和26.39/18.01W，TJ均值62.064/63.625°C，Ts均值48.673/49.603°C。历史热状态确有保留；同时实际PWM均值约57.0%/69.2%，它不是严格同输入实验，不能把所有差异归因于已识别的慢热容。整轮只是一条连续轨迹。

## 局部鳍片独立对照与时间限制

原CSV `26071081-20261019173740.csv`，90,818字节，SHA `{surface['actual_original_csv_sha256']}`。逐行核对Date/Time/CH1与原行32—3015，2,984条、全部间隔1秒；1,119对相邻相同温度仍保留。数据处理未改日期、补零、去重或对曲线求时间偏移。

用户确认探头始终固定在出风口附近同一局部鳍片、专用胶带固定，无移动/松脱/仪表时钟重置。CH1是局部表面接触温度，不是出风空气、整个结构平均温度或Ts真值；一秒记录不等于探头响应已标定。原导入记录中的保守安装限制仍保留，新的用户确认作为独立附注，不篡改原归档。

开始/结束照片分别显示仪表比网页名义快约4秒/3秒；网页与Mac OS/N305的绝对一致性、刷新和曝光误差未知。独立Mac—N305时钟括号与NTP记录保留，但不能反过来认证网页。这里仅画0、−3、−4秒三种条件情景：后两种额外假定网页等于原生时钟。它们不是已校准边界，不选最优，也不把一秒差异拟合成漂移。严格绝对时间配对数量仍为0。

相对图只在一个预先按背景时间选定的原始CSV行减去一次参照值；所有情景沿用同一原行，没有按阶段平移、缩放或贴曲线。下表仅描述该条件对齐下相对走势的平均绝对差异，**不是Ts准确度**：

| 加到仪表名义时间的情景 | G2 KF Ts | QS | LP30 | LP120 |
|---|---:|---:|---:|---:|
{chr(10).join(shape)}

名义时间下，局部表面相对同一参照点最高升约7.21°C，G2 KF Ts约10.66°C。简单LP120在本轮局部表面形状差异上更小；这不证明它测准了Ts，也没有足够物理对应或时钟依据排名“哪个真实慢态最准”。实际TJ、模型Tf、潜在Ts和风扇动作始终分开。

## 四张图怎么读

1. [全程热状态与输入](figures/01-全程热状态与输入.png)：最上方比较实测TJ、持续校正Tf和一次初始化后的自由响应；第二行画潜在Ts与独立CH1，保留不同物理含义；下面两行是两条rail和记录PWM。蓝色背景仅表示工作块，不能解读为模型控制风扇。
2. [热响应与真实未来预测](figures/02-热响应与真实未来预测.png)：上图负误差是低估，橙色HOLD在启停附近明显失效；下图在每个时距的同一集合比较MAE，保留90秒LP120胜出的结果。A使用真实未来输入，不能拿它代替B。
3. [局部鳍片与慢态独立对照](figures/03-局部鳍片与慢态独立对照.png)：上图保留绝对幅度差；下图只减同一背景参照，黑线三个时钟情景接近不代表绝对时钟误差已知。Ts偏高不通过重命名或缩放解决。
4. [冷启动与质量边界](figures/04-冷启动与质量边界.png)：左图冷启动内部尺度收敛，右图保留四路中的短暂未知。tracking与上下文资格分别显示，阴影不是95%置信带，也不是现场许可。

## 验证、资源和交付

新增6项有限离线测试覆盖独立数值解、实际路径断档不回填、多分支同输入、逐时距/首答案资格、真实CSV相邻重复保留。另有8,677条现场状态/I02完整回读；最终证据从全新目录重放的回执见`verification/independent-replay.json`。所有数值计算使用CPU单线程，无CUDA、拟合或额外候选搜索。

首次正式运行约{env['wall_s']:.2f}秒，峰值RSS约{env['peak_rss_bytes']/2**20:.1f}MiB；Python {env['python'].split()[0]}，NumPy {env['numpy']}，SciPy {env['scipy']}。环境、测试日志、原始SHA、冻结spec、全部逐点结果和独立重跑入口一并提供。只新增本轮研究目录及共享交接状态，没有修改生产软件、旧研究结果、采集/调度/准入、设备或Git远端。

本轮证明冻结数值接口可复现，显示一定阶段内TJ预测价值，同时保留启停失败和局部表面幅度差。没有实测Ts准确度、控制收益、部署或下一轮现场放行结论。完成后停在离线复审边界。
'''
    (out/'TTO-首轮fixed-anchors冻结模型对照报告.md').write_text(text)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    figures(args.output);report(args.output)
