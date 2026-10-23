"""Write Chinese report from completed results; does not select or change candidates."""
import argparse
from pathlib import Path
from common import ROOT, read

TITLE='TTO-CPU增量活动信息-离线分析与冻结方案.md'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def report(out):
    result=ROOT/'runs/final-v2'
    tables=read(result/'temperature-common.json')
    allh={r['h']:r for r in tables if r['posthoc_stratum']=='all'}
    act=read(result/'activity-metrics.json')
    descriptive=read(ROOT/'verification/descriptive-root-cause-final.json')
    audit=read(result/'A1-independent-audit-readback.json')
    check=read(ROOT/'verification/contracts-and-protection-final.json')
    env=read(result/'environment-resource.json')
    names=['B0','B1','G2-HOLD','INPUT-BASE','INPUT-MEAN','INPUT-CORE']
    label=['B0 保持TJ','B1 趋势','原G2-HOLD','已有GPU/两rail','再加CPU均值','再加CPU最大值']
    mae=table(['方法','15秒 MAE','45秒 MAE','90秒 MAE'],[
        [l]+[f"{allh[h]['errors'][n]['MAE_C']:.3f}" for h in (15,45,90)] for n,l in zip(names,label)])
    tail=table(['方法','45秒绝对误差P95','45秒低估P95','45秒最大低估'],[
        [l]+[f"{allh[45]['errors'][n][k]:.3f}" for k in ['P95_absolute_C','P95_under_C','max_under_C']]
        for n,l in zip(names,label)])
    bg=table(['版本','共同无请求参照中ACTIVE秒数／事件数','排除块内短缝与DONE后3秒后的ACTIVE秒数／事件数'],[
        [a['variant'],f"{a['active_while_no_client_inflight_s']:.3f} / {a['no_client_inflight_active_events']}",
         f"{a['settled_background_active_s']:.3f} / {a['settled_background_active_events']}"] for a in act['groups']])
    onset=table(['真实工作块首提交','BASE延迟','MEAN延迟','CORE延迟'],[
        [s]+[f"{next(a for a in act['block_onsets'] if a['stage']==i and a['variant']==n)['delay_s']:.3f}秒" for n in ['INPUT-BASE','INPUT-MEAN','INPUT-CORE']]
        for i,s in [(1,'首次单路 R0001'),(3,'双路 R0024'),(5,'四路 R0056'),(7,'重复单路 R0157')]])
    strata=table(['45秒起点分层（事后）','点数','原HOLD MAE','BASE MAE','MEAN=CORE MAE'],[
        [dict(pre_submit_90s='下次工作块提交前90秒',submitted_not_yet_observed='已提交、BASE尚未观察到活动',
              observed_startup_15s='BASE观察到活动后15秒',sustained='持续',after_DONE_90s='DONE后90秒',background='其余背景')[r['posthoc_stratum']],r['n']]+
        [f"{r['errors'][n]['MAE_C']:.3f}" for n in ['G2-HOLD','INPUT-BASE','INPUT-CORE']]
        for r in tables if r['h']==45 and r['posthoc_stratum']!='all'])
    thresholds=table(['信号','激活阈值','回落低阈值'],[
        [n,f"{v['on']:.6f}",f"{v['off']:.6f}"] for n,v in descriptive['fixed_thresholds_in_original_units'].items()])
    receipt=ROOT/'verification/independent-rerun-receipt.json'
    rerun=read(receipt) if receipt.exists() else None
    replay_text=(f"另外在全新目录复跑，{len(rerun['scientific_files_byte_identical'])}份科学结果、补充诊断及{len(rerun['synthetic_interface_outputs_byte_identical'])}份合成接口输出逐字节一致。"
                 if rerun else '独立目录复跑回执在最终证据包verification中列出；尚无回执时不作通过声明。')
    body=f'''# TTO-CPU增量活动信息-离线分析与冻结方案

**本轮软件和离线计算已完成；当前1秒记录没有证明逐核CPU带来额外活动信息，也不支持用新输入策略替换原G2-HOLD。** 新增了一个可运行、可冻结的活动候选、同规则三组输入对照、完整功率/PWM情景转换和新记录离线评分入口。没有重训热模型、修改旧成绩或启动真机。

最直接的发现是：在2706个原有效起点上，INPUT-CORE与INPUT-MEAN的活动状态和新预测逐点相同。相对已有GPU/两rail，CPU均值只在四路块启动时提前约1秒触发，却把共同“无客户端请求在途”参照中的活跃判定从30.805秒增加到343.820秒。45秒MAE为：原HOLD **1.544°C**、BASE **1.666°C**、MEAN/CORE **2.760°C**。背景与结束后的错误抵消了局部启动/持续阶段的收益。

**唯一推荐下一步：将冻结候选和时间接口交独立复审；通过后，由测试线另请用户批准一次只读能力/开销核对。只有确认存在更细的独立信息和可核对的到达时间，才值得再由用户决定12请求补测。** 这轮不因CPU柱子更高就申请负载，也不据旧1秒负结果否定尚未测过的亚秒增量。当前没有高频实测、设备核对或现场许可。

## 1. 原成果的接受范围和本轮资料角色

唯一真实run仍是`5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3`。field/modeling为同run的两条交付；2706条CPU统计为同一数据的派生分析。本次校准已使用这批已分析资料，新增候选的所有数字都标为**开发内对照**，不称新留出验证。179条请求也不是179个独立热过程，未来12请求同样只能算一次连续过程。

已完整回读复审报告、下一步合同、field-audit/numeric-audit及其脚本和原始ref。本轮只执行模型线A1—A3：没有重做45分钟实测、42次拟合、I02或closeout入口；保存的因果热状态直接原样复用。

原G2仍有可保留价值：A-roll 45秒MAE0.334°C；A-long连续自由响应MAE0.888°C、平均偏差 **+0.837°C**。原B45平均优于B0，尾部却更差，最大低估12.712°C；90秒LP120的3.432°C仍优于G2的3.540°C。这些事实均保留，没有用本轮候选或跨M/Y总分改写旧结论。A类已知未来输入的响应不能冒充真实未来预测，更不代表控制收益。

## 2. A1：明确失温反馈与提交前后分层

新增的[A1补充说明](A1-原结果补充说明.md)及`stale4682-addendum.json`保留原样记录：北京时间18:05:38.535886，`observation:4682`有`temp_stale=true`、`auto_state=stale`、报文`temp_valid=false`，但HTTP成功且成功PWM为25%。前一份4679为66%，下一份4685恢复非stale、PWM37%，随后46%。约1.012秒暂停/降级及全部原始值保留。

这份记录包含明确异常反馈，原“上下文不就绪”不能把它解释成单纯未知。独立源仍收到有效TJ，不等于设备的控制温度反馈有效；不能用“HTTP都成功”证明没有失温。新增图3和图注只作说明，不改失温保护、控制政策、准入或原图。

![明确失温反馈及恢复](figures-v2/03-明确失温反馈及恢复说明.png)

原45秒共同集合2649点，其中360个跨阶段起点贡献 **78.0708%** 的绝对误差。这是事后解释，未进入B特征。181个跨到新工作块的起点全在真实首提交之前；它们仍全部计分，未来出现CPU信号不能倒改旧预测。

提交后也有严重失败：R0024在17:54:10.326879提交，`observation:2482`在0.040032秒后到达。原B45为48.898°C，答案60.875°C，低估11.977°C；本轮三种活动判断此时均IDLE，BASE/MEAN/CORE仍低估12.148°C。随后约1.041秒的原记录中CPU和GPU rail已升，而GPU%仍为0。该点不能用“用户还没提交”解释，也没有靠删点避开。

下表按真实首提交、首个BASE活跃接收、协议DONE分层；起点/标签与原表相同。提交前90秒优先于上一块DONE后90秒，所以互斥表中的DONE后行不包含全部回落；原阶段表与全部事件仍保留，不能把行数当独立样本。启动段小样本只作描述。

{strata}

新敏感性表另外保存。45秒原HOLD在原起点正常上下文2648点MAE1.544251°C，异常/未知1点为1.573722°C；预测区间触及明确stale到下一份恢复记录的46点MAE0.549706°C，其余2603点1.561837°C。这是新分表，不重写总分，也不通过删异常制造候选胜利。

## 3. A2：只冻结一个候选，没有追加搜索

`freeze.json`在任何本轮评分前绑定了analysis-spec及candidate。校准只取第一背景+60～240秒、第一单路+60～300秒的已有有效特征中位数；不看温度答案或检测成绩选参数。只有一次校准、一个规则、一种输入转换；没有遍历核心、全程相关性最大化、阈值网格或看到负分后重开搜索。

规则是对各特征作`(当前值−背景中位数)/(活跃中位数−背景中位数)`，取所需特征中的最大值。达到0.25激活；全部不高于0.10并有3秒连续有效低观测才从ACTIVE回落；首次有效低观测可建立IDLE。首次处于中间带、缺失、陈旧、时钟不明或源侧文件均为UNKNOWN，不写正常。实际阈值如下，功率为W、利用率为%。

{thresholds}

INPUT-BASE使用GPU利用率、GPU rail、CPU/SOC/MSS rail及各自原有效期/年龄；INPUT-MEAN再加全核均值；INPUT-CORE仅再加每个时刻的CPU最大值，未挑某个核。三者规则、3秒低值确认计时、单比特滞回记忆、原有效期、到达帧和转换完全相同。冻结spec的`history_budget_s=3`在此明确指低值确认计时：中间带内仍保留先前状态，并不是3秒后必然忘记ACTIVE；这一行为也是背景滞留的原因。澄清未改变参数或评分。两条rail独立，CPU/SOC/MSS不冒充纯CPU，5V未相加，CPU活动未作为另一条发热项。

**活动到未来输入的转换也已完整实现：**

- ACTIVE：GPU与CPU/SOC/MSS各自保持`max(当时功率,开发活跃功率中位数)`，先验分别26.532W和17.827W；没有偷看未来实际结束。
- IDLE：两条rail分别按`P_idle+(P_0−P_idle)×exp(−未来秒数/30)`回到各自背景1.984W和5.952W。
- PWM：完全沿用原冻结观察器在该起点的条件PWM并保持，保留其来源/资格，不从active布尔量生成成功PWM；不预测真实风扇动作。
- UNKNOWN或原热状态不可用：新策略无预测，原HOLD继续作为独立对照报告。

G2的θ、当前实测TJ锚点、过去得到的Ts/E、原状态资格和初始化一律相同；用精确仿射矩阵指数传播常值或指数衰减功率，预测段无TJ反馈。E仍是等效边界，不是室温；旧M的24°C没有复制到本run。潜在Ts不是TTP实测或热容。

这是一种有明确限制的开发先验：活跃会持续、背景会回落，不能预知任意新任务或结束。当前结果不支持把它叫可靠温度预测改进。可选EVENT-ASSIST本轮未实施，真实事件只用于事后评分参照，不喂给候选，也不要求通用TTO绑定推理服务。

## 4. 活动增量：一次均值先到，未见逐核再增益

![四次启动的已到达信息](figures-v2/01-四次启动的已到达信息.png)

图1的每个点是原日志在N305收到的信息，横轴相对真实客户端首提交。虚线不是GPU内核启动，归一化只为同图展示。CPU相对GPU%先动的片段中，两rail往往也已升；不能只拿GPU%当基线。

{onset}

四次均识别到，连续工作块内未重复进入ACTIVE；MEAN与CORE在四路块提前一条约1秒原采样，其他三块相同。**CORE相对MEAN在全部2706帧的状态差异为0，预测也相同。** 这证明该冻结规则在旧1秒开发记录上没有额外利用到逐核摘要；不等于证明所有设备/200ms窗口里CPU最大值永远无用。

全部179条请求均保留：各版本171条提交时已经ACTIVE、8条后来检测到，不能把171条报成171次“零延迟识别”。四块首提交延迟为依赖同一热过程的四个事件。结束后首个IDLE延迟BASE约5.718～9.925秒，MEAN/CORE约5.718～9.925秒，双路分别6.628与7.629秒。协议DONE仍不是GPU停止真值。

共同可用跨度2712.339秒，其中无客户端请求在途参照1240.241秒。下表的事件包括串行请求短缝；第二列规则与第三列固定补充口径都报告，避免把一切协议缝隙叫物理空闲。

{bg}

CPU版本在314帧中ACTIVE而BASE没有ACTIVE，另有最初约0.983秒的UNKNOWN差异；CORE与MEAN仍完全相同。根因是“普通CPU活动”不特指推理，OR规则配合回落确认会让背景CPU波动长时间维持活跃功率先验。仅调高阈值可能换来漏检，不能在看完这些成绩后偷偷重选。本轮没有这样补救，也不把失败归咎求解器。

活动可用率BASE100%、MEAN/CORE99.964%是**分类输出可用率**，不是温度正确率、正常控制比例或安全放行。

## 5. 温度同集合结果：局部改善不足以替换HOLD

所有MAE单位°C。15/45/90秒分别有2679/2649/2604个原共同起点；新候选没有把原共同集合缩小。各方法自身预测/标签覆盖与拒绝原因在`temperature-coverage.json`另列。没有90秒答案不删除45秒；没有补造高频TJ标签。

{mae}

{tail}

![活动及温度对照](figures-v2/02-增量活动与温度预测的成功及失败.png)

图2说明为什么不能只报一项好分数：观察到活动后的61个启动起点，最大低估从8.509°C降到0.664°C，但MAE由1.095变1.187°C；持续段1406点从1.541略降到1.489°C。两者支持“输入先验在局部可能有用”。然而原共同全集三个时距均变差，回落和背景尤其恶化；CPU版本45秒低估P95下降，是同时增加偏高预测的结果，绝对误差P95更差，最大低估仍12.712°C，不能算安全收益。

结论分开：原冻结热动态及因果状态可继续保留；本轮活动候选/输入先验未胜出；CORE独立增量未显示。它不是风扇算法失败或热θ需要立即重训的证据，风扇平稳平台、任务后有依据继续散热的产品目标也没有因此被否定。本轮没有调整普通需求后处理，原KF/QS/LP30/LP120及旧结果保持冻结；慢退本身不作为错误，需求指数也未映射PWM。

## 6. A3：新数据之前冻结的分析与时间接口

`analysis-spec.json`、`interface-contract.json`和`interface-freeze.json`规定下一次的输入、时间、缺失及数据角色。消费者与离线流式评分代码真实可运行；默认文件回放，loopback服务需显式标志启用。它不采集设备、不排请求，也没有永久raise假入口。现场源旁录/调度仍由测试线负责，本轮没有代做。

特征保存feature_source、原引用/原值、源序号、Thor采样/读完/统计窗口与时钟/boot身份、N305实际到达、年龄/有效期、更新证据及unknown。旧CPU后端/实际统计窗未核实就明确写未知。GPU年龄是来源年龄下界，不是CPU领先时差；跨主机UTC偏移/传输延迟未知不填0。相同数值的新来源身份保留；同一buffer反复读取不续有效期、不增加确认次数。缺口使活动UNKNOWN，恢复按当前证据重新判断，不重置原热状态或按工作块重置Ts。

未来实际高频记录使用同一真实到达序列同时比较BASE/MEAN/CORE，再在同一数据上按接收单调钟整数秒取**已经到达**的最新帧，形成因果1秒对照。保留原到达时刻与有效期，不向过去平移；两种速率的温度成绩另做共同起点/共同答案交集。实际有效更新频率必须由源窗口/计数/身份支持，不能把频率收益全归逐核。200ms目前只存在明确标记的合成fixture，不是Thor已验收能力。

活动指标以真正提交/协议完成作有局限的参照，报告共同可用点的延迟、漏检/unknown、背景ACTIVE秒数/事件数、连续组重复激活、恢复及覆盖。源侧潜力、到达侧及时性、物理CPU/GPU先后三者分开；没有真实接收时刻的实验后CSV不能作及时预测增益。视频、首token、DONE、GPU%上跳均不标定GPU内核起止，不优化曲线/视频错位。

新12请求主角色是一轮针对性连续过程，先检查本冻结候选。若必须看新高频数据再选窗口/阈值，就登记开发探索，不能再冒称独立确认，也不自动补一轮。注册文件绑定候选/spec SHA，并记录是否看过新数据选参；声明本身不能代替冻结与时间证据。

## 7. 验证、资源与交付核对

最终**17项研究测试通过**：实际自建loopback收发、显式许可/时钟未知、陈旧/缺失/重复buffer、相同数值新更新、未来截止、源/时钟切换、ODE独立传播、无热状态/错模型、45有标签而90无标签、未来特征扰动不影响过去预测，以及合成有增量时可以被检测。17项是本轮新测试，不冒充原研究的6项或复审重放已经再次运行。

另重建{check['label_decisions_independently_rebuilt']}个原时距标签判定、{check['baseline_values_checked']}个B0/B1值，复算原HOLD最大差{check['old_HOLD_max_abs_difference_C']:.3g}°C；没有重跑观察器或I02。{replay_text} 原来源15份逐字节核对，{check['protected_original_files_checked']}份受保护原文件SHA未变。参数候选始终一次；首次测试辅助代码和浮点核对辅助脚本的失败/修正日志、首轮及中间轮结果SHA均保留，未改参数消除失败成绩。

本机Python3.12.14、NumPy2.2.6、SciPy1.16.3，CPU/BLAS单线程；权威旧数据分析约{env['wall_s']:.3f}秒，峰值RSS{env['peak_RSS_bytes']/2**20:.1f}MiB。这是Mac离线分析资源，不是Thor/N305旁录开销或部署性能认证。CUDA、设备连接、真实请求、训练均为0。

证据包包括源码/新增研究patch、冻结spec/candidate与来源、原模型/观察器spec、原raw/旧逐点评价、本轮逐点状态/预测/分层/背景区间、三张中文新图与旧四图原件、有限尝试和测试日志、接口fixture、数据角色、环境/资源、逐文件SHA及`rerun.py`入口。README给出可直接运行的本地命令。

## 8. 仍未决的事项及停止点

真实Thor的CPU计数窗、jtop/NVML/rail独立更新时间、共享服务关系、时钟映射、N305实际到达与旁录开销，必须由测试线在用户另行批准的只读核对中确认，本轮未访问设备。12请求补测又是另一项当次授权，能力核对不自动升级为负载许可。

本候选不会因新负结果自动扩网格、换模型、启动另一轮测量或提出一串泛化测试。RAM/模型驻留和设备身份继续保存为上下文，未加50GB阈值，也未要求卸载/重载、CPU-only/GPU-only或新测点。普通推理中CPU/GPU共同活动是正常场景，当前共线不否定组合信息价值，也不证明独立发热贡献已识别。

当前交付为**通用离线分析与冻结候选已完成；逐核额外收益尚未证实；高频真实时间/开销与现场补测未执行**。生产TTO、collector、runner、安装器、TTL、采样、风扇/WS/曲线/gain/保护及旧报告/模型/成绩均未改；没有部署、服务重启、GitHub写入或新任务。完成本轮后停止，交独立复审。
'''
    out.write_text(body)
    addendum='''# A1 原结果补充说明（原报告与旧分数不改）

本文件是TTO-CPU-ACTIVITY-PREP-v1.0新增解释，须与原图4一起阅读。

run 5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3，2026-10-19北京时间18:05:38.535886，observation:4682明确记录temp_stale=true、auto_state=stale、报文temp_valid=false。HTTP成功，成功PWM25%，前4679为66%，后4685非stale且PWM37%，随后46%。原始记录完整复制在runs/final-v2/stale4682-addendum.json，引用输入原raw文件，不改原件。

“控制上下文不就绪”只是当时资格状态的概括，不能掩盖明确失温反馈；HTTP未超时不代表设备未报失温。独立TJ来源仍有效，不能据此替设备控制温度反馈写正常。约1.012秒调度暂停/降级和恢复如原记录，潜在慢态未按工作块重置。恢复观测的两个时刻不精确标定异常真实持续时间。

新图03只解释原事件：PWM与原有效TJ分开，底图只标TJ起点记录的模型资格，不冒充连续真机判定。旧图/旧报告/旧逐点评价保留原样。stale-and-context-sensitivity.json是新派生分表，不覆盖旧总分、删异常或改变失温控制政策。

360个跨阶段45秒起点贡献78.0708%绝对误差，仅用于事后解释。提交前的181个跨到工作块起点继续计分；observation:2482在R0024提交0.040032秒后仍低估11.977°C，不能再用“请求未发生”解释。完整起点/实际提交/协议DONE与本轮分层在新证据中可复算。

A-long平均偏高+0.837°C、原B尾部风险与90秒LP120较好均不删除；没有用M/Y不同构成的总分声称统一性能提升。新增CORE在旧1秒开发资料上无额外识别增益，不否定热动态或尚未实测的亚秒潜力。
'''
    (out.parent/'A1-原结果补充说明.md').write_text(addendum)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    report(ap.parse_args().output)
