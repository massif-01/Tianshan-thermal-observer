"""Readable Chinese report from the sealed offline computations; no model operations."""
from pathlib import Path
from collections import Counter
import json
from prepare import read,jsonlines,digest

ROOT=Path(__file__).absolute().parent
TITLE='TTO-快慢热状态与平稳散热需求-研究报告.md'


def f(value,d=3):return '—' if value is None else f'{value:.{d}f}'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    result=ROOT/'results'
    metrics=read(result/'temperature-metrics.json')
    def cell(kind,run,h=45,scale='run',stratum='confirmed_normal'):
        return next(x for x in metrics if x['kind']==kind and x['group']==run and x['h']==h and x['scale']==scale and x['stratum']==stratum)
    specs=read(ROOT/'slowstate-spec.json')
    data=read(ROOT/'sources/registered/data.json')
    demand=read(result/'demand-signal-metrics.json')
    signals={(r['run'],r['group']):r for r in demand}
    tails={r['event']['run']+'/'+r['event']['id']:r for r in read(result/'post-task-tail-metrics.json')}
    jumps=read(result/'state-window-diagnostics.json')
    sensitivity=read(result/'frozen-model-state-sensitivity.json')
    coverage=read(result/'coverage.json')
    resources=read(result/'resources.json')
    points=jsonlines(result/'four-branch-predictions.jsonl')
    cals={m:read(ROOT/f'sources/evaluation/{m}/calibrations.json')['G2'] for m in ['primary','old_LS','A24']}
    branches=['STATE-G2','STATE-QS','STATE-LP30','STATE-LP120']
    counts=Counter(r['run'] for r in data['accepted'])
    figindex=read(ROOT/'figures/figure-index.json')
    text=[]
    text.append('''# TTO：快慢热状态与平稳散热需求——研究报告

**执行合同：TTO-SLOWSTATE-v1.0｜2026-10-14｜已完成实际离线计算，等待独立复审。**

G2慢态有增量信息，但简单滤波已能解释一部分平稳行为。45秒、真实未来功率/PWM已知的共同集合上，G2的TJ误差在L/S/M为0.315/0.409/0.191°C，30秒因果滤波为0.444/0.502/0.195°C。L/S上G2更好；M上两者接近，不能宣布模型全面替代简单滤波。

短脉冲不必复制为普通需求的一次明显升降；持续M负载下，G2需求也不是永远为零，会逐步升量并保留回落尾部。S连续短问答只有约36.3%的整组时间具备原状态资格，尚不能证明完整平台；已热参考还会令一些稀疏短任务的增量被裁成零，零值不能解释成没有散热需要。

本轮真正导出了Tf与Ts，没有把旧的欠峰Tf改名。原TJ短峰误差仍存在；HOLD也仍不知道下一次任务，M负载段45秒预测MAE约4.13°C。潜在Ts尚无体温真值，不能据此给出安全风扇档位、噪音收益或现场放行结论。

**唯一推荐下一步：另行预登记一次保持原AUTO/曲线/gain/保护的被动同步复核，加入一个位置明确的独立散热结构温度参照，覆盖完整连续短任务与随后的回落。** 目的同时检验慢态增量是否对应结构温升、补齐平台证据，而非继续挑更平滑的曲线。本轮不执行，也不要求用户现在追加实测或购买仪器。

---

**1．本轮做了什么，哪些仍未发生**

模型动态参数重新拟合次数为0。主模型固定第二轮D-LSM-G2（Efree）；旧LS-fit G2和D-LSM-G2-A24仅作冻结敏感性。所有模型均`deployable=false`，L/S/M均为已看过的开发资料；没有新增模型族、参数搜索、未来请求预测器或在线参数更新。

| 项目 | 本轮状态 |
|---|---|
| 模型/输入字段语义 | 已冻结；Tf仍是TJ输出，Ts仍是未测慢态 |
| 两维A-long与因果60秒状态 | 已实际导出并逐点核对 |
| G2/QS/LP30/LP120对照 | 已完成15/45/90秒A-roll和B-HOLD |
| 普通需求及快风险接口 | 已完成离线原型、即时失效与恢复核对 |
| 物理慢态验证 | 未完成；没有结构温度真值或实测热容 |
| 真正未来温度预测 | 固定HOLD诊断已完成；未来负载切换问题仍未解决，输入策略研究暂缓一轮而非取消 |
| 现场控制与噪音收益 | 未发生；没有设备指令、部署或安全放行 |

本轮只新增`experiments/thermal_slowstate_v1/`。未改生产TTO、旧tests、采集器、runner、安装器、依赖锁、版本、原始日志、旧模型/成绩/spec、设备配置、风扇、WS或TianshanOS；未联网设备、发推理请求、运行现场doctor/collect/shadow、新负载、CUDA、服务重启、提交、推送或PR。原工作树保留。
''')
    text.append('**2．来源、冻结与覆盖**\n')
    text.append(f"规则冻结时间为`{specs['implementation_freeze']['frozen_at']}`，在新成绩产生前写入。冻结spec SHA256：`{digest((ROOT/'slowstate-spec.json').read_bytes())}`。模型、原归档和新派生物各自有SHA，没有沿用新结果的旧身份。\n")
    text.append(table(['记录','完整accepted数','原严格段数','具备60秒状态的起点','普通需求时间覆盖'],[
        [r,counts[r],len([s for s in data['segments'] if s['run']==r]),
         next(x for x in coverage if x['run']==r)['legal_causal_state_origins'],
         f"{signals[(r,'whole-run')]['branches']['STATE-G2']['available_fraction']:.1%}"] for r in ['L','S','M']]))
    text.append('''

共6643个accepted起点，沿用约1秒序列、原始引用、质量隔离、源身份、功率有效性、成功PWM与原TTL。58个严格段中13个足够长，主模型有5430个合法因果起点。请求与工作块没有被当作独立热过程，三轮才是三个连续热过程；这里的n是相关时序样本数，不是独立实验数。

两个大ZIP均已核对SHA和CRC：`r2-results-original.zip`为`809e90eef398daf34e9cabfd5d4427d35275fc8185541d61810f67943f35aecb`，`r2-prerequisites-original.zip`为`7f52d7cfad66564ff07178bfe14a5a46da83390b0855c28f2b65cad8910c3614`。交付只索引原ZIP，不递归打包它们。`source-inventory.json`固定本轮直接使用的成员；`historical-provenance-index.json`额外索引同一已冻结归档内的历史身份附注，不回写第一阶段封存。

私有与分享身份分开保留在`sources/provenance/r2-source-identity-supplement.json`。例如S的私有manifest SHA为`51cd77db0f8748c3f6fb002a964a170208ddc783177f711a271d7c7f10402bfa`，分享manifest为`2c5c6c3593b70dab6b3bdf2c1ea5425c49dc08d556235ceb2e211221720e8c3f`；其observations仍同为`121341bbccef3bb5bd34e2f5b327ebb4eb4f342d745cc26004d9c6061409c707`。这些是保留的历史身份记录，不宣称本轮重新读取了另一份私有日志。

M用户确认24°C原附注逐字保留，只绑定`637f114b-563b-4c35-8062-a7588a89ce1c`。没有补造L/S室温，没有改ambient_snapshot、manifest、原SHA或原E。现场请求准入override未被用来放宽模型资格。
''')
    text.append(table(['冻结模型','本轮角色','原model.json SHA256'],[[m,'主对照' if m=='primary' else '诊断，不参与择优',sha] for m,sha in specs['model_sha256'].items()]))
    text.append('''

**3．真正的Tf/Ts、初态和缺口**

每个模型都从原因果前缀的Ts_initial和E出发，用记录中两rail及成功PWM进行两维传播。A-long在前缀后不再吸收TJ反馈；其5430个Tf与原封存A-long逐点相同，最大差0.0°C（明示容差1e-10°C），Ts取同次传播的第二列。三模型两类轨迹分别完整保存，不拼线择优。

因果模式直接读取原states.jsonl；每点只用过去60秒。第一维Tf被锚定到当前TJ，不能把这个零当前误差计成预测能力。第二维Ts、未锚定的窗口末Tf、窗口首末引用、E、有效截止、当前输入和模型SHA都保留。每个预测起点的第二状态才在四分支间替换。
''')
    text.append(table(['前缀得到的有效E（°C）','L','S','M'],[[m]+[f(next(v['E'] for k,v in cals[m].items() if k.startswith(r)),5) for r in ['L','S','M']] for m in ['primary','old_LS','A24']]))
    text.append('''

E在每轮首次合法前缀完成后固定，后续真实缺口仅重建慢初态。主模型M的E约35.164°C仍是等效边界，用户室温24°C没有被强写进去；A24则沿用既有M=24诊断。L/S的A24有效E也不代表测得室温。

60秒不是热平衡：以M-00的固定方程和真实输入为例，初始Ts偏1°C，在60秒末仍令Tf偏约0.674°C、Ts偏约0.641°C；到300秒仍分别约0.177/0.169°C。这里只计算固定模型的单位线性敏感度，没有新拟合。初态/边界与短前缀的关系保存在`prefix-and-unit-initialization-sensitivity.json`。
''')
    text.append(table(['主模型记录','滑窗重估修正绝对值中位数（°C）','P95（°C）','最大（°C）','初态贴边次数'],[
        [r]+[f(next(v for v in jumps if v['model']=='primary' and v['run']==r)['correction'][k],4) for k in ['median','p95','max']]+[
        next(v for v in jumps if v['model']=='primary' and v['run']==r)['bounds_hit_n']] for r in ['L','S','M']]))
    text.append('''

这里的“修正”是当前滑窗Ts减去“上一合法状态沿已经到达的实际输入传播到当前”的Ts，用于区分估计器重估与真实输入传播。S02窗中能看到窗口移出短峰后的下探和回升；全部极值、速率、窗口首引用和初态变化均留存，没有另设跳变门槛剔除难点。绝对曲线并不等同于物理散热结构温度。

M20/M60/M180三个开始边界前后均属M-00，过去窗口跨过边界，绝不新建慢初态。M只在原有真实失温/资格缺口处分为M-00、M-01。所有源缺口断线，恢复先满足原历史资格；新段增量参考是新参考，不能接成上一任务已冷却的证据。
''')
    text.append(table(['因果Ts主模型相对冻结参照','绝对差MAE（°C）','固定首前缀增量差MAE（°C）'],[
        [x['run']+' / '+x['other'],f(x['absolute_difference']['MAE']),f(x['incremental_difference']['MAE'])]
        for x in sensitivity if x['mode']=='causal60']))
    text.append('''

状态敏感性只用每轮各模型的第一个合法起点作一次固定参考，没有每段自由平移或全段归一化。M上主模型与A24的绝对Ts差MAE约3.688°C，而增量差约0.355°C；这支持讨论部分形状信息，同时暴露物理标定和边界解释的不确定性。不能把增量较近说成绝对温度测准。

**4．四种慢态的同条件温度对照**

主模型θ、每轮前缀E、当前实测TJ、同一输入情景和温度答案固定。STATE-G2用原过去60秒Ts；STATE-QS是当前TJ和PWM下的慢方程零导数代数状态，不含历史；LP30/LP120只对这个代数状态作因果指数低通。低通使用实际不规则dt、上一个输入左持有；首个合法起点允许因果回放已发生前缀，前60秒不对外宣称E已知或滤波稳态。LP保留整段过去，G2仍用原60秒窗，记忆差异未隐藏。

A-roll允许真实未来输入，不读未来TJ反馈；B-HOLD只保持当前输入，不知道后续请求或实际结束。原RELAX30、B0、B1、紧凑Ridge的系数/缩放/成绩均保留为旧参考，不重训也不逐点择策略。新STATE-G2的14339个A-roll、16290个HOLD派生值与原预测数值完全一致；其中无合法温度答案的预测仍保留，但不算误差。

下面是未来控制状态可确认正常层的共同标签MAE（°C）。每行四分支同集合；A与B仍是不同信息合同，不能用A的好成绩宣称B或风扇成功。
''')
    rows=[]
    for kind in ['A_roll','B_HOLD']:
        for run in ['L','S','M']:
            for h in [15,45,90]:
                c=cell(kind,run,h)
                rows.append([kind,run,h,c['n']]+[f(c['metrics'][b]['MAE']) for b in branches])
    text.append(table(['类别','轮次','时距秒','共同n','G2慢态','无记忆QS','LP30','LP120'],rows))
    text.append('''

G2在45秒的三轮平均误差都优于这三种固定对照，但并非每个时距/分层都胜出：L的90秒A-roll中LP120优于G2；M的45秒回落层LP30约0.177°C，G2约0.179°C。简单滤波并非无效，M上整体差距只有约0.004°C，没有独立重复实验或置信区间，不能称显著优势。

这个增量价值指本轮固定比较中的状态估计信息：G2初始化器结合过去TJ、功率与PWM，QS/LP则是规定的代数状态/简单滤波；不能把差别唯一归因为某个已测物理热容。它是下一步核对的依据，不是物理命名的许可证。
''')
    text.append(table(['45秒主模型','轮次','偏差（°C）','P95绝对误差（°C）','最大欠预测（°C）'],[
        [kind,run]+[f(cell(kind,run)['metrics']['STATE-G2'][key]) for key in ['bias','P95_abs','max_under']]
        for kind in ['A_roll','B_HOLD'] for run in ['L','S','M']]))
    text.append('''

仍需正视动态失败。45秒B-HOLD在M工作起点层MAE约4.130°C，在L回落起点层约3.240°C；这主要暴露HOLD对未来负载/PWM切换的假设，不能仅换慢态就解决。原A-long在S02/S03/D01真实TJ峰时仍分别欠2.339/1.934/2.089°C。它们仍是Tf对TJ的错误，没有转名为“本来是在预测散热体”。

对所有未来控制上下文均保留的45秒B共同集合，基线情况如下；S上B0与R_IO仍优于G2，不能删待机或改集合制造胜利。
''')
    refrows=[]
    for run in ['L','S','M']:
        c=cell('B_HOLD',run,stratum='all_contexts')
        refrows.append([run,c['n'],f(c['metrics']['STATE-G2']['MAE'])]+[f(c['references'][b]['MAE']) for b in ['B0','B1','R_TJ','R_IO','G2-RELAX30']])
    text.append(table(['记录','n','G2-HOLD','B0保持TJ','B1趋势','R_TJ','R_IO','原RELAX30'],refrows))
    text.append('''

每个15/45/90秒独立判标签资格，有45秒答案而无90秒答案时保留45秒。A需完整输入路径；B遇未来辅助缺口仍保留可用温度答案，并分别报告正常、辅助缺口、已观测异常/变化、未分类缺口及旧严格集合。未知没有被记为正常。每个指标单元保存起点/时距/答案引用集合SHA，覆盖另表：
''')
    text.append(table(['记录','时距秒','温度答案总数','A四分支可评分','B四分支可评分'],[
        [c['run'],c['h'],c['qualified_temperature_labels'],c['A_roll_scored'],c['B_HOLD_scored']] for c in coverage]))
    text.append('''

逐轮/工作/回落/背景/阶段/原事件窗的MAE、偏差、P95和最大欠预测完整见`temperature-metrics.json`及`event-temperature-metrics.json`，原B参考在逐点文件中独立字段保留。没有混合不同覆盖的分数排名，也没有将合并开发成绩称作最终泛化。

**5．普通需求：哪些平稳来自状态，哪些来自固定后处理**

每个严格段第一个合法因果状态固定各分支s_ref；原始指数为(s−s_ref)/10，保留负值和超界，再裁至[0,1]。相对上一输出差不超过0.02则保持，否则每秒升量最多1/30、降量最多1/120。每个分支完全相同，无网格搜索；10°C及死区/速率是本轮展示塑形值，绝不是物理热常数或固件值。

下表均为相同资格期间，跨不可用缺口不累加变差或方向反转。有效反转按从极值累计反向移动≥0.02计数，防止下降每步小于0.02就被漏算；同时保留幅度，不能把始终零判作更好。
''')
    srows=[]
    for run in ['L','S','M']:
        for b in branches:
            v=signals[(run,'whole-run')]['branches'][b]
            srows.append([run,b,f(v['z_raw']['amplitude']),f(v['z_raw']['total_variation']),
                f(v['z_output']['amplitude']),f(v['z_output']['total_variation']),v['z_output']['significant_reversals'],f(v['lower_clipped_s'],1)])
    text.append(table(['记录','状态来源','原始幅度','原始总变差','输出幅度','输出总变差','输出有效反转','低于下限秒'],srows))
    text.append('''

所有分支上限裁剪时间均为0；原始幅度、负值、下限裁剪及不可用原因秒数全部留存。这里没有把指数标成百分比，也没有PWM换算。实际成功PWM独立坐标，只是原现场参考。

稀疏S02中，G2慢态确实短暂上升，但仍低于本严格段较热的参考，G2/LP输出均被裁为零；QS更直接追随TJ尖峰，塑形后仍有一次上升和尾部。这个例子不能证明短任务没有热负担，也不能把零输出叫作模型控制获胜。

连续S全组138.8秒，仅约36.3%具备状态/需求资格。可用前段G2指数范围约0.040–0.085、LP30约0.040–0.083，二者均较平稳；QS约0.047–0.173并有7次有效反转。由于后段缺资格，只能说已观察到前段累积趋势，尚未验证整组稳定平台。不能续TTL或补线制造完整结果。

M20/M60/M180（实际约32.7/65.0/192.9秒）均在同一M-00内，工作段需求时间覆盖100%。G2工作段输出峰约0.157/0.261/0.566，持续任务越长，原型仍逐渐增加；LP30约0.185/0.334/0.589。LP120更慢、更低，不因曲线更平就自动更好。G2与LP30在多个信号指标相当，模型的附加价值更多体现在固定方程下对后续TJ的解释，而不是平稳外观专属权。

结束后的状态尾部与塑形尾部分开，统一“接近本段参考”为指数≤0.02，未交叉则按300秒窗口/下一题/资格缺口/记录结束截尾：
''')
    tailrows=[]
    for ev in ['phase-M20','phase-M60','phase-M180']:
        row=tails['M/'+ev]
        for b in ['STATE-G2','STATE-LP30','STATE-LP120']:
            v=row['branches'][b]
            tailrows.append([ev,b,f(v['z_target']['first_return_s'],1),f(v['z_output']['first_return_s'],1),
                f(v['z_target']['final_value']),f(v['z_output']['final_value'])])
    text.append(table(['M工作块结束','来源','目标首次≤.02（秒）','输出首次≤.02（秒）','约300秒目标','约300秒输出'],tailrows))
    text.append('''

G2的M20目标约109秒接近参考，塑形输出约128秒；M60约189/242秒。两者之差来自死区和限速，不是额外测得的热容。M180在300秒时目标仍约0.064、输出约0.083，尚未回到阈值；LP120尾部更长，不能由长短独自排序。返回阈值后的再越界也记录，首次交叉不冒充永远冷却完成。

S连续组结束时普通状态不可用，因此原任务尾部/返回时间为未知。稍后资格恢复建立的是新段参考；图4明确标出，未接回原任务。S02的零增量更不等于冷机。所有返回描述都只是指数行为，不是风扇退档许可。

**6．真实TJ与即时风险没有被慢滤波隐藏**

快通道读取全部原到达节点的TJ、成功PWM引用、保护/故障/失温/源身份及当前资格，另添加仅从已知有效期安排的到期事件。它不等下一个TJ采样、死区或120秒降量。明确异常/变化或资格不足即普通需求null、清除持有信号；恢复须重新满足原历史规则，不续旧信号年龄。

29个已观测异常/控制变化节点都在同一节点输出普通需求null；这是节点数，不是29个独立故障。辅助资格到期时，若最新真实TJ仍有效，快通道继续保留TJ和引用，普通需求仍不可用。未知状态保留null与原原因，不写成正常；普通高PWM也没有被自动当硬保护。没有新增跨Jetson统一温度阈值或设备写接口。

全accepted需求可用性、每个原观察节点/已知到期的状态和原因，分别在`accepted-demand-availability.jsonl`、`fast-status-and-demand-ledger.jsonl`。普通指数与风险通道是接口分工，既有系统继续负责保护，本研究无控制权。

**7．两rail共同活动的有限诊断**

GPU与VDD_CPU_SOC_MSS保持两个rail，后者不是纯CPU。组合等效驱动q_equiv=b_g·P_GPU+b_c·P_CPU_SOC_MSS，单位°C/s，是G2快状态方程的一项，不是W、总热量或实测热容。5V、gain与其他温区仍留原诊断字段，没有相加当热输入。
''')
    q=read(result/'combined-drive-diagnostics.json')
    text.append(table(['严格当前输入资格','n','功率相关r','GPU范围W','VDD_CPU_SOC_MSS范围W','GPU/另一rail范围'],[
        [x['run'],x['strict_current_input_population']['n'],f(x['strict_current_input_population']['power_correlation'],5),
         f(x['strict_current_input_population']['VDD_GPU_W']['min'])+'–'+f(x['strict_current_input_population']['VDD_GPU_W']['max']),
         f(x['strict_current_input_population']['VDD_CPU_SOC_MSS_W']['min'])+'–'+f(x['strict_current_input_population']['VDD_CPU_SOC_MSS_W']['max']),
         f(x['strict_current_input_population']['ratio_gpu_to_cpu_soc_mss']['min'])+'–'+f(x['strict_current_input_population']['ratio_gpu_to_cpu_soc_mss']['max'])] for x in q]))
    text.append('''

完整accepted功率域与严格当前输入资格域分别保存，不用辅助失效点扩大模型预测集合。旧LS、主模型与A24的组合驱动形状在已观测域相关很高（M的主模型对旧LS约0.99999、对A24约0.99990），但绝对强度并不相同；快慢耦合、有效边界及系数存在补偿。温度响应相近不证明参数独立物理贡献唯一。

因此共同推理活动不是数据错误，也不因共线性取消组合预测价值；A24的b_g接近0更不能推出GPU不发热。功率比例域外迁移仍缺证据。本轮不要求CPU-only/GPU-only实测，也不改变现有输入或模型解释。

**8．四类图怎样读**

可先打开`figures/中文图解.html`，每图有PNG与SVG，以下每图三句话。独立纵轴在图内明示，°C、无量纲指数和PWM不硬叠在同一轴。
''')
    for figure in figindex:
        text.append('**'+figure['name']+'**\n\n')
        text.append('![中文研究图]('+str(ROOT/'figures'/figure['png'])+')\n\n')
        text.append('\n\n'.join(figure['caption'])+'\n')
    text.append('''

**9．验证、复跑和唯一下一步**

新增研究测试12项通过，覆盖字段分离、真实两维传播与SciPy矩阵指数对照、过去前缀因果性（改未来TJ/输入/请求元数据不改当前状态/需求）、不规则dt与左持有、断段/恢复/预热、M块不重置、同条件消融、独立时距标签、幅度/饱和/累计反转、即时风险失效与有效TJ保留、尾部时段不越界及冻结状态敏感性。合成输入只验算法，没有当RM-01实测。

独立回读重算了276个逐轮共同集合指标单元，核对16290个因果状态的引用和过去截止、原41个直接来源成员及历史身份附注；1797个原文件SHA全部未变。四张图均做了视觉检查；新段参考和灰色资格缺口明确标注。没有重跑全产品/固件回归，未对无证据范围做全仓审查。

新程序早期失败保留日志：无温度答案仍试图统计误差、S阶段没有macro字段的元数据兼容；另修正已知辅助到期仍保留快通道TJ，以及大UTC浮点相加引起的微秒级尾部时长越界。最后采用本轮单调时钟作区间裁切。死区边界单测也改用无相减舍入的精确构造。没有按结果扩大模型搜索、调整旧预测或塑形参数。
''')
    text.append(f"一次完整CPU计算重放约{resources['wall_seconds']:.1f}秒，进程峰值RSS约{resources['maxrss_bytes_macos']/1024**2:.1f}MiB，NumPy {resources['numpy']}，BLAS相关线程固定为1，CUDA使用为否。计算/绘图实际环境与每阶段用时见`results/resources.json`、`figures/plot-environment.json`和`replay-logs/receipt.json`。一条`rerun.py --input-dir ...`入口自动使用本机已有运行时，重建全部派生物、限定测试、四图和回读；不联网安装依赖。\n")
    if (ROOT/'independent-replay-proof.json').exists():
        proof=read(ROOT/'independent-replay-proof.json')
        text.append(f"另将候选证据ZIP解压到新目录，通过同一入口从原ZIP重建、测试和回读，{len(proof['scientific_output_files'])}个科学结果文件全部逐字节相同，用时{proof['wall_seconds']:.1f}秒。`independent-replay-proof.json`记录被重跑候选ZIP的SHA、逐文件对照、环境和阶段回执；最终打包加入这份回执及交付说明，未改变上述科学结果。最终ZIP本身另核CRC与成员SHA。\n")
    text.append('''

交付证据含新增代码及code.patch、前置冻结、三个原model.json、来源/私有分享SHA区别、全部状态/逐点消融/需求/快状态、完整分层指标、四类图及HTML、有限测试、失败与成功日志、资源与独立入口。原两个大ZIP仅索引引用。成果成员SHA与ZIP外层SHA单独封存；独立重跑应在新解压目录进行，以保留本次封存结果。

唯一下一步仍是第一屏所述的一次被动同步复核：保持原AUTO、曲线、gain、保护和采样/TTL，用位置明确且记录精度/安装方式的独立结构温度参照，同时保留TJ、两rail、成功PWM和完整异常/恢复引用，覆盖完整连续短任务与随后回落。可证伪的是“慢态增量在多种任务节奏下比LP30更能解释该结构温升/回落”；若只有简单滤波同等或更好，不因模型名称保留物理解释。测点不等于整个TTP真值，需另行登记位置和边界。本轮不执行、不要求立刻购置仪器；现场记录不全或既有保护异常时停止该记录并由原系统处理，不调整风扇以追求漂亮结果。

当前工作已停止于离线交付，等待独立复审。未来输入策略保持暂缓状态，短任务提前退档原型未实施。
''')
    (ROOT/TITLE).write_text('\n\n'.join(text)+'\n')
    print(TITLE)


if __name__=='__main__':main()
