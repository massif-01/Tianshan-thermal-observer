# TTO-CPU旁录离线适配与失效撤销：模型线收尾报告

**R1已完成：实际旁录原件已能通过唯一离线适配，进入原Activity与原evaluate_stream；最新失效立即撤销旧资格。** 本轮没有重做旧研究、调整活动阈值、热模型或旧成绩，也没有代做测试线的SSH/运行候选修复。

联合验证使用测试线真实`cpu_source.stream/read_cpu/utilization → Sidecar.receive`代码生成的150包，逐行核对wire原字节与接收source一致，再完成342个事件帧、56个原TJ决策起点的模型联调。输入是合成/proc和自建原生服务；不是Thor/N305新实测，不是12请求或新的CPU先导结论。

**14项有限回归通过；模型线代码/接口身份已冻结，“实际安装与测试”已从独立副本实际调用并复核通过；由其汇总cpu.2候选、必要证据与操作卡。** 真实60秒能力核对及12请求仍均未获本轮授权，不自动继续。

## 本次改动

新增`bridge.py`是唯一实际信封→冻结FRAME/thermal origins入口，读取同run的arrival、native/state、source config及明确失效事件。旧一秒adapter和旧资料未修改，`cpu_interface`旧平面helper不被调用。测试线负责将旧helper明确废弃/修正及完成有界SSH，本线没有复制另一套活动算法或现场调度器。

CPU均值与最大值从完整在线集合的原始累计计数和同一前后读取窗重算：first8差分中扣idle/iowait，guest不重复加；完整性核对possible/online文本、状态映射、原proc文本与计数。全部核心原值/在线状态保存在原件，适配帧保留完整在线结果与引用，不能只挑几个核。

计数回退、online集合切换、缺窗、明确incomplete、source身份/序号问题、native epoch及传输停止立即撤销；下一完整合法新窗恢复。不先过滤invalid再找旧valid。相同数值的新合法计数窗保留，重复buffer不续期。测试直接证明失效发生时旧值原截止尚未到，仍被立即撤销。

GPU/两rail取保存的原生来源、原update_id及原截止，不让200ms CPU包更新可用时间或续龄。原生断连时，即使CPU仍在接收，BASE继续不可用；直到原生实际恢复。旁录直接查询而独立窗/generation未知的GPU/rail只存诊断，不伪造generation、不替换BASE或与原功率相加。

## 时间、身份与资格

接收实际received_at/decision_generated及host/boot/domain、native UUID与命令绑定；未知receiver boot保留null。Thor独立host/boot/session、原始计数和读取窗保留在源时钟域，不与接收单调钟直接相减。不把源时刻改名成接收时间，不填0传输延迟或精确源龄。

明确采用**接收顺序研究资格**：CPU最早在真实decision完成后可用，截止不晚于真实received_at+1秒，沿用已有旁录无包预算，较晚解析不能续期。这不是生产TTL或CPU源龄验收。接收domain不能关联时明确拒绝放上此时间轴；源时钟不明则撤销CPU，保留BASE自身真实资格。

thermal origin每个原接受TJ仅一条：在实际state envelope生成/可用时刻预测，另存原measurement_received_mono_s，不把计算状态倒填到较早raw接收时刻。此新接口时间基准单独登记；所有分支同起点/同标签，仍用原15/45/90秒、+2秒及逐时距资格规则，无高频TJ标签。旧run评分时间轴和成绩不改。原Ts/E、当前TJ、条件PWM及安全字段直接复用，CPU不更新热状态/参数或安全资格。

causal-1s-decimation只在每秒选最后已到达的200ms窗结果，改变交付节奏；**不重建真正1秒CPU累计统计窗**。60秒能力检查将来只检查可读信息、时间与开销，不要求空闲段先证明先导收益；是否做12请求由能力和用户另批决定。

## 实际联合结果

唯一run：`b1a4248e-7274-4991-91ce-d8d61644006b`；命令`SYNTHETIC-CPU2-JOINT-20261020`。测试线提供的完整样例目录与source config已原样封存；首个不完整/资源超限尝试由测试线另外保留，没有拿它冒充完整联调。

| 冻结分支 | ACTIVE事件帧 | UNKNOWN事件帧 |
| --- | --- | --- |
| INPUT-BASE | 314 | 28 |
| INPUT-MEAN | 214 | 128 |
| INPUT-CORE | 214 | 128 |

不是全UNKNOWN，也不将这些合成状态计数称精度或CPU收益。撤销ledger有计数回退1次、online切换2次、native epoch切换5次、源初包缺前窗1次及停止1次。真实断连/恢复、CPU重置/offline来自同一次实际收发样例；其他异run/时钟等负向回归明确标记为对这些实际信封的变异，不以手工模型FRAME替代两端联调。

原evaluate_stream已经运行真实到达与因果1秒交付选择两条分支；各自产生25个CORE温度预测起点。15秒仅1个合格共同温度答案，45/90秒没有合格共同答案，分别保留，不删除15秒。这些是接口与标签资格证明，**没有新物理温度成绩或活动增益结论**。原CORE=MEAN及CPU策略未胜HOLD的开发负结果完全保留。

## 有限验证与交回

14项新回归覆盖：实际发送/接收原字节与源码身份、完整CPU窗口、真实计数回退/online/native epoch撤销及恢复、失效早于旧到期、旧粗缓存不续期、缺粗来源不造值、重复buffer、相同值新窗、异run/源session/序号/时钟、部分核拒绝、未来数据不可提前使用、原时距资格及解析不能延长支持。未重跑原17项科研研究或旧拟合。

独立离线复跑对5份适配产物逐字节核对；11份模型联调产物结构/引用/状态/计数严格一致，派生浮点按1e-8°C容差，实际最大差0。原件/代码/参数/模型继续严格SHA，未强行要求不同数值库的科学浮点JSON逐字节相同。测试总控另从独立副本用其原始样例实际运行bridge/joint_check及14项测试，5份适配输出逐字节一致，回执原样附verification。2173份受保护原文件核对未变；原活动candidate、analysis-spec字节和模型/spec身份未改。

转换入口仅需Python标准库。模型联调用原冻结NumPy/SciPy，验证参考环境为Python3.12.14、NumPy2.2.6、SciPy1.16.3、pytest8.3.5；本研究requirements记录参考环境，不是生产依赖锁或N305安装候选。目标3.10安装、SSH预算、cpu.2版本/清单与操作卡由测试线单独汇总。

代码在本目录；唯一CLI、样例和复跑命令见README.md，细节见接口说明.md，新身份见interface-freeze.json，权威数据为results/final-v2及results/joint-final-v2。证据包含新研究patch、原样输入/源码身份、适配/撤销/诊断/模型消费结果、测试与复跑回执及逐文件SHA。`model-handoff.json`给测试线绑定，不替代其整体验收。

本轮设备连接、部署、真实请求、重训练/参数搜索及GitHub写入均为0。模型线有限收尾结束，等待两线汇总与独立复审。
