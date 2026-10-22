"""Chinese scientific figures and bounded interpretation of this actual archived run."""
from pathlib import Path
import json,sys,datetime as dt
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager,FontProperties
ROOT=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'vendor'))
from common import read,write,sha
from compare_surface import load_lines,stats

LABEL={'resident-baseline':'驻模背景','sparse':'稀疏6题','between-groups':'组间回落','continuous':'连续12题','final-cooldown':'最终回落','outside_phases':'阶段外'}
COLORS=['#a8b9c7','#d88d49','#a7c5b8','#cb6972','#b8c5db']


def make(data,out):
    out=Path(out);summary=read(out/'comparison-summary.json');points=load_lines(out/'surface-comparison-points.jsonl')
    nominal=[p for p in points if p['scenario_offset_s']==0]
    start=data['nodes'][0]['wall'];phase=data['phases']
    for p in ['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/System/Library/Fonts/STHeiti Medium.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if Path(p).exists():fontManager.addfont(p);plt.rcParams['font.family']=FontProperties(fname=p).get_name();break
    plt.rcParams['axes.unicode_minus']=False
    def decorate(ax):
        for color,p in zip(COLORS,phase):
            ax.axvspan((p['start']-start)/60,(p['end']-start)/60,color=color,alpha=.18)
        ax.grid(alpha=.2);ax.set_xlim(0,(data['nodes'][-1]['wall']-start)/60)
    fig,axes=plt.subplots(3,1,figsize=(13,10),sharex=True)
    a=data['samples'];x=np.array([(r['wall']-start)/60 for r in a]);y=np.array([r['values']['tj'] for r in a])
    axes[0].plot(x,y,color='#273342',lw=1,label='本轮原生accepted TJ')
    axes[0].set_ylabel('实测TJ（°C）');axes[0].legend(loc='upper left')
    axes[1].plot([(p['nominal_wall']-start)/60 for p in nominal],[p['temperature_C'] for p in nominal],color='#257f8a',lw=1,label='实际CH1局部鳍片表面（未校时）')
    axes[1].set_ylabel('局部表面（°C）');axes[1].legend(loc='upper left')
    axes[2].plot(x,[r['values']['vdd_gpu'] for r in a],label='VDD_GPU（独立rail）',color='#b15d42')
    axes[2].plot(x,[r['values']['vdd_cpu_soc_mss'] for r in a],label='VDD_CPU_SOC_MSS（独立rail）',color='#4d718d')
    axes[2].set_ylabel('原功率（W）');axes[2].set_xlabel('距TTO开始（分钟）；CH1按用户设定UTC+8作近似对应')
    axes[2].legend(loc='upper left')
    for ax in axes:decorate(ax)
    for p in phase:axes[0].text((p['start']+p['end']-2*start)/120,axes[0].get_ylim()[1],LABEL[p['name']],ha='center',va='bottom',fontsize=9)
    fig.suptitle('本轮两种真实温度｜局部表面不是TJ、空气或已测得Ts',fontsize=15)
    fig.tight_layout(rect=(0,.02,1,.95));fig.savefig(out/'图1-真实温度与输入.png',dpi=150);fig.savefig(out/'图1-真实温度与输入.svg');plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(13,10))
    nodes=data['nodes'];nx=[(n['wall']-start)/60 for n in nodes]
    axes[0].step(nx,[int(n['complete']) for n in nodes],where='post',lw=.7,label='原生控制/输入当前资格（非模型已初始化）')
    axes[0].set_ylabel('当前资格0/1');axes[0].legend(loc='upper right');decorate(axes[0])
    spans=[s['span_s'] for s in data['segments']]
    axes[1].hist(spans,bins=[0,1,2,3,4,5,10,20,30,60,65],color='#7194a7',edgecolor='white')
    axes[1].axvline(60,color='#b95e47',ls='--',label='冻结初始化需要60秒')
    axes[1].set_xlabel('原生合格片段长度（秒）');axes[1].set_ylabel('片段数');axes[1].legend();axes[1].grid(alpha=.2)
    cov=read(out/'model-coverage.json');cov=[r for r in cov if r['phase']!='all'];idx=np.arange(len(cov))
    axes[2].bar(idx-.18,[r['accepted_TJ'] for r in cov],.36,label='原生accepted TJ',color='#677f94')
    axes[2].bar(idx+.18,[r['model_state_origins'] for r in cov],.36,label='完成60秒初始化的模型状态：均为0',color='#bd715d')
    axes[2].set_xticks(idx,[LABEL[r['phase']] for r in cov]);axes[2].set_ylabel('记录点数');axes[2].legend();axes[2].grid(axis='y',alpha=.2)
    fig.suptitle('资格影响｜1843条TJ并不等于有连续热模型状态；不跨缺口拼接',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'图2-原生资格与初始化覆盖.png',dpi=150);fig.savefig(out/'图2-原生资格与初始化覆盖.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(14,5.5))
    sens=read(out/'surface-phase-sensitivity.json');offsets=summary['approximate_offset_scenarios']
    for color,p in zip(COLORS,phase):
        rows=[r for r in sens if r['phase']==p['name']]
        axes[0].plot([r['scenario_offset_s'] for r in rows],[r['temperature']['mean'] for r in rows],'-o',label=LABEL[p['name']],color=color)
    axes[0].axvline(0,color='#777',ls='--');axes[0].set_xlabel('仅诊断的整体时间偏移情景（秒）');axes[0].set_ylabel('各阶段CH1均值（°C）')
    axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    names=['主G2','旧LS G2','A24动态G2'];axes[1].barh(names,[0,0,0],color='#9faebb');axes[1].set_xlim(0,1)
    axes[1].text(.5,1,'三套冻结模型均已执行资格检查\n352段最长26.013秒，未达到60秒\n合法新状态0；严格时钟配对0\n没有可用于表面排名的模型点',ha='center',va='center',fontsize=12)
    axes[1].set_xlabel('合法模型—表面比较点数（均为0）');axes[1].grid(axis='x',alpha=.2)
    fig.suptitle('时间与可解释范围｜偏移情景不是已证实误差界限，也不选择最优错时',fontsize=13)
    fig.tight_layout(rect=(0,.02,1,.94));fig.savefig(out/'图3-时间敏感性与比较边界.png',dpi=150);fig.savefig(out/'图3-时间敏感性与比较边界.svg');plt.close(fig)
    phase0=[r for r in sens if r['scenario_offset_s']==0]
    rows=[]
    for r in phase0:
        s=r['temperature'];rows.append(f"| {LABEL[r['phase']]} | {s['n']} | {s['mean']:.3f} | {s['min']:.2f}—{s['max']:.2f} |")
    t=summary['actual_surface_temperature'];j=summary['TJ_temperature'];ref=read(out/'fixed-reference.json')
    text=f'''# TTO-YET610L同步短问答：冻结模型离线比较报告

**2026-10-18｜仅run {data['run_id']}｜不重训、不用外部温度纠正状态**

这次取得了可用的真实局部表面记录：2027条、1秒间隔，CH1为{t['min']:.2f}—{t['max']:.2f}°C，记录内幅度{t['amplitude']:.2f}°C；本轮TJ为{j['min']:.3f}—{j['max']:.3f}°C。它们不是同一种温度，不能把表面读数直接当作Ts或TJ答案。

**三套冻结G2已实际执行本轮原生资格检查，但合法新模型状态为0，不能判断G2是否比LP30更贴近真实表面。** 5319条原始事件中有1843条accepted TJ；原生严格模型输入形成352段，最长仅{summary['longest_strict_segment_s']:.3f}秒，没有一段达到既有60秒初始化要求。不是把旧M曲线拿来配新CSV，也不是算出模型误差不好后弃掉结果。

另一个独立限制是仪表同步精度未知：原CSV没有时区，开始同框为本次重开之前的历史照片，结束同框只有显示到秒的差值，不能证明固定偏移、误差界或漂移。**严格逐秒时钟配对为0**。本报告仅按用户设定的北京时间、整体偏移0作近似展示，另完整报告±5/±10/±30秒情景；这些情景不是误差界，未选择最有利偏移。

按未校正的分钟尺度曲线看，稀疏组出现多次TJ尖峰时，该局部测点总体下降；最终回落阶段TJ先下降，该测点仍缓慢上升。它不是TJ的同幅度或简单延迟副本；这里只描述本轮两个测点，不把相反走势归因于某个部件、时滞或控制收益。

当前成果是“实际CSV格式及原值核对通过，现场表面记录已取得；模型—表面比较受原生初始化资格和时钟证据限制”。没有模型胜负、物理热容或控制收益结论。唯一建议下一步是先独立复审本次资格/时钟证据，讨论是否需要另立短缺口状态传播诊断合同；本轮不默认放宽规则，也不因此要求重跑实验。

## 1. 本轮真实记录

18条请求和300秒背景、稀疏6题、300秒组间、连续12题、600秒回落是一个连续现场热过程，不拆成18个独立样本。请求实际1.688—2.894秒，原题/payload没有为达到目标时长而改变。此前69a567d7等停止轮次及81条格式试录未拼入。

CH1由用户确认用专用耐温聚酰亚胺胶带固定在靠近出风口的局部鳍片表面；期间无移动、松脱或重设时钟。它不是空气、深部鳍片、整块均温或直接测得Ts；接触与探头响应未经独立校准。新run室温未知，没有复制旧M的24°C。

原CSV SHA为`698c3842216bb34a263ba630a2760aaf9858a6232050de798d5922a47eb15e80`，62108字节；2027行Date/Time/CH1与规范化记录逐行重新核对，原始行32—2058、2026个1秒间隔、1340对相邻等温均保留。原CSV与提取表SHA分别保存，不混为同一原件。仅此文件、CH1与日期格式通过，不外推所有YET固件。原导入run_id是本轮trial字符串，另以只读绑定说明关联本轮TTO observer UUID，没有回写原记录。

## 2. 实际执行和为何没有合法状态

读取与本轮manifest全部22份源文件SHA相符的TTO 0.2.4副本回放完整原始事件；不是旧每5秒预测起点表。保留原质量隔离、输入/控制资格及TTL；两独立rail与成功PWM按原语义使用，5V与gain未相加或当物理冷却输入。当前温度有效不等于控制上下文一直适合热模型。

本轮继续采集政策只允许记录继续、请求等current_ready恢复；它没有改变原生模型资格。native-health异常、temp_stale、normalized_valid=false和variable/default变化均保留，只报告事件与覆盖影响，不调查红叉根因。下列原生计数可重叠，不相加当独立故障次数：

```json
{json.dumps(summary['native_quality'],ensure_ascii=False,indent=2)}
```

1843条accepted TJ均源有效，1445个起点当前满足严格模型输入，但连续支持不足60秒。三模型共1056个片段资格尝试、5529条按accepted起点导出的新轨迹可用性记录，Tf/Ts为null并附原始引用/不可用原因；三套数值状态文件合法为空。A-long、因果G2、QS/LP30/LP120均没有可发布合法状态。15/45/90秒A-roll/B-HOLD也均无模型预测，未拿B0/B1或已知输入响应冒充灰箱成功。

冻结动态参数未改；预登记初始化本应仅用过去TJ的60秒前缀估计等效E/慢初态，随后固定E，真正缺口重建资格，阶段/工作块本身不重置。此处在前缀资格检查就未通过，没有估计新E、没有把未知初态设平衡、没有用外部温度补状态或改用旧M的Ts。A24仅指原冻结动态的诊断身份，没有给新run强设24°C。

## 3. 可报告的局部表面描述

以下阶段归属只按未校正的UTC+8显示解释，均值不是物理模型得分；完整7种时间情景和每条记录保留，不用这些均值挑偏移。

| 近似阶段 | CH1点数 | 均值°C | 原值范围°C |
|---|---:|---:|---|
{chr(10).join(rows)}

唯一预登记背景是驻模背景实际开始+150秒后的首个仪表样本：`{ref['original_instrument_time']}`，{ref['temperature_C']:.2f}°C。它不是冷机/热平衡。全部情景固定同一个原记录ID；因该点无合法模型状态，模型增量比较不可用，没有逐阶段平移或另挑更贴合背景。表面自身全程升降可以描述，尚不能从中定量分离探头响应、局部传热与Ts动力学。

## 4. 图怎么读

图1上排为本轮accepted TJ，中排为真实CH1局部表面，下排为两个独立功率rail。纵轴分开，阶段阴影只是时间标注；CH1横轴为近似解释，没有强制+1/+2秒、没有把早于重开的照片冒作新轮开始锚点。没有任何旧M或伪造Ts线。

![图1]({out.absolute()/'图1-真实温度与输入.png'})

图2区分“当前有资格”和“已得到60秒模型初态”：短暂恢复可让前者为1，却仍无法建立后者。中排352段均在60秒线左侧；下排真实TJ数量保留，模型状态数量诚实为0。当前原生合格输入支持约{summary['native_qualified_input_support_s']:.2f}秒，占原始观察时段{summary['native_input_support_fraction']:.1%}，这也不等于60秒连续初始化覆盖。

![图2]({out.absolute()/'图2-原生资格与初始化覆盖.png'})

图3左侧把所有预登记整体偏移情景并列，仅展示阶段统计敏感性，不是已知同步误差棒或模型胜负；右侧明确三套冻结模型都没有合法表面对照点。±30秒外误差仍未知，因此“在这些情景下变化小”也不能证明时钟准确。

![图3]({out.absolute()/'图3-时间敏感性与比较边界.png'})

## 5. 可复核证据与停止

来源ZIP为18020171字节，SHA`c0c3e1895ca9893d90a27559a491093aa4de1209ab1ae317494adc5ef3c94273`，CRC及255项成员已再次核对；原始采集、CSV、导入和钟点/测点说明均未改写。新研究代码、冻结spec/模型SHA、原生逐事件资格、全部1056次初始化资格尝试、5529条空值及原因、新run逐点时钟情景、图、测试、环境/资源和重跑入口随证据交回。

核对项目包括三份冻结参数的C传播与独立矩阵指数、过去前缀不读后续TJ、严格缺口不桥接、未知时钟不生成照片偏移、实际源资格/逐时距标签及模型SHA。实际通过数量及环境/资源由单一入口追加回执；不能当作N305现场资源成绩。独立研究环境的准备单独记录，未修改生产依赖锁。

本轮只在独立研究目录生成派生文件；没有接设备、发送新推理、修改生产/风扇/曲线/gain/保护/采样/TTL、CUDA、重训、在线参数更新、提交/推送或PR。完成后停止，交回复审；不能把这次采集完成称作原规则零异常通过。
'''
    report=out/'TTO-YET610L同步短问答-冻结模型比较报告.md';report.write_text(text)
    (out/'中文结果索引.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>真实表面记录与冻结模型比较</title><style>body{font-family:system-ui;margin:24px;max-width:1200px;line-height:1.7}img{max-width:100%}</style><h1>真实测温已取得，合法模型状态为0</h1><p>2027条CH1，1843条accepted TJ；352个原生严格片段最长26.013秒，未达到60秒初始化。严格时钟配对0；无模型胜负或Ts物理验证。</p>'+''.join('<h2>'+name+'</h2><img src="'+name+'.png">' for name in ['图1-真实温度与输入','图2-原生资格与初始化覆盖','图3-时间敏感性与比较边界'])+'<p>完整限制、原始引用及逐点输出见同目录Markdown与JSON。本页未按模型挑错时，也未以继续采集政策放宽模型资格。</p></html>')
    return report
