# TTO Orin、Thor 与 CURVE 方案独立审查

2026年10月12日。结论：**需修改后执行。方向成立，首要问题是方案漏列了一项实际控制温度资格阻塞；此外需要把新旧合同的识别、回放与升级边界写成可验证的规则。**

本轮是方案和当前代码审查。未实施适配，未修改生产源码、安装器、原方案或设备；未连接真机、重启服务、部署、提交或推送。新建的审查文档、离线探针和派生报告用于复核本结论。

**审查依据与证据边界**

- 主方案：[TTO执行方案](../plans/TTO-Orin-Thor-CURVE执行方案-20261012.md)；配套方案：[监控服务执行方案](../plans/RM01OrinStatus-Orin-Thor执行方案-20261012.md)。两份“共同审查的数据接口草案”已逐字比较，一致。
- TTO当前提交为 `97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。核对了实时采集、Quality、Features、Engine、Journal、回放、训练、模型读取、评估、历史报告及安装配置链路。
- 同时只读检查本机rm01OrinStatus解析器，以及TianshanOS的CURVE/AUTO分支、温度状态API和状态读取路径。本机源码不能代替当前主板固件部署身份核验。
- 保存的实机run为 `run-2026-10-12T113943.639076_0000-7113c960`，北京时19:39:43至19:43:00。8个文件与既有SHA清单全部一致。
- 离线环境：macOS ARM64、Python3.10.18；aiohttp3.11.18、python-socketio5.13.0、python-engineio4.14.0、NumPy2.2.6、SciPy1.14.1、scikit-learn1.6.1、pytest8.3.5、pytest-asyncio0.26.0。本轮没有重装或升级依赖。

**实际发生了什么**

这一轮接收了628条原始记录：196条计算模块数据、194条fan状态、40条temp状态、196条tick及2条连接边界。保存了38个预测起点，正常AUTO起点为0。原始TJ、CPU/GPU温度和Thor功耗rail已保存，不能把“特征中缺失”统称为“设备没有上报”。

| 项目 | 原始证据 | 解释 |
| --- | --- | --- |
| GPU忙碌 | 该run的gpu对象为空；另一次NVML探测返回0% | 需要补监控入口；探测的0%不能回填到该run |
| Thor功耗 | vdd_gpu、vdd_cpu_soc_mss、vin_sys_5v0均有current/average/mW | 前两条被TTO硬编码遗漏；不是读取失败 |
| 分组温度 | soc012、soc345存在 | 当前只提取soc0/1/2，分组含义必须保留 |
| 风扇 | 194条均为curve；enabled、duty_valid均为true；无报告故障 | PWM实际上已记录，只有旧模型特征被资格门槛撤下 |
| 控制温度状态 | 40条均valid=false、active_source=default、timestamp_ms=0 | 这是CURVE之外的第二个资格阻塞，原方案没有单列 |
| 温度配置 | preferred_source=variable，bound_variable=agx_info.temperature.tj | 已配置绑定不等于当前绑定来源实际有效 |

最小理解是：**采集链路能接收数据，输入配置尚不适配Thor，且正常控制资格存在两个独立阻塞。** 这不能归纳为只需要把AUTO条件改成CURVE。

保存的旧版本资源统计为RSS峰值37.42MiB、CPU单逻辑核P95约3.00%、含特征与记录写入的prediction_ms P99约7.19ms。这些数值仅描述旧候选在该次N305观察中的情况；不能直接证明新增GPU/profile实现的资源预算通过。该轮没有模型效果验收和完整任务升温—回落过程。

**方案中应保留的决定**

1. 由计算模块监控服务报告平台，N305只消费声明；未知平台不伪装为Orin。
2. Thor用NVML补GPU百分比；0与缺失分开，GPU失败不撤下有效TJ。
3. GPU读数只在新seq提交时封存；迟到结果留给下一行，不在广播/HTTP时重新读取。
4. 保留实际rail和分组温度名称，不制造别名或总功耗，不改变TJ真值。
5. CURVE与AUTO分别定义资格，CURVE不要求AUTO专属gain，不改主板模式。
6. 四种有限特征配置的列数计算正确：54、53、51、50；没有必要提高64列限额。这是全部候选列数，不是每个训练模型都必须选择全部可选列。
7. 保留Ridge、三个时距、训练侧字段选择、三层共同集合、时间隔离、test-used和固定模型；没有新增模型搜索的必要。
8. 保留原始证据，新合同只产生新派生结果。方案把实机发布安排在后续明确授权之后，这个边界正确。

NVIDIA的[Thor文档](https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonThor.html#gpu-management-tool)支持用nvidia-smi观察GPU利用率；[nvidia-smi文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html)建议维护型工具优先使用NVML及Python绑定。它也说明GPU利用率是过去采样窗口的忙碌比例。采集完成时间和1秒读取周期都不能被表述为硬件瞬时测量时刻或驱动内部窗口长度。

**需要补齐的8项问题**

| 编号 | 优先级 | 性质 | 最小改动 |
| --- | --- | --- | --- |
| R01 | P1 | 现场根因遗漏 | 单列实际温度来源无效；保留资格阻塞，不以改mode绕过 |
| R02 | P1 | 新旧GPU合同判别不明确 | 定义统一GPU合同的存在标志，区分legacy与损坏的新对象 |
| R03 | P1 | 新平台身份没有接入现有冲突判定 | 将平台/稳定输入合同纳入身份和段变更规则 |
| R04 | P1 | GPU年龄没有落实到完整特征链路 | 明确收样、重复、当前值和历史窗口的资格规则 |
| R05 | P1 | 历史回放缺少明确版本分派 | 按记录合同保留旧段号/引用，独立生成新合同诊断 |
| R06 | P2 | 持久化配置升级有回归风险 | 兼容旧local.json及旧manifest，避免直接删除配置项 |
| R07 | P2 | 单个不可覆盖profile与运行变化的关系不清 | 固定run初始合同，按段/起点记录实际scope及合同身份 |
| R08 | P2 | AUTO专属诊断不只gain一个 | CURVE不输出AUTO固件预测或将旧AUTO温度当当前控制证据 |

P1表示必须在实施前冻结规则或补入验收；P2表示需要在实现合同中给出明确处理。不是要求扩建安全平台或重构全仓。

**R01：CURVE之外，真实控制温度状态也不满足资格**

原方案第26行把全部起点不正常归因于mode=curve。当前 [Engine.normal](../../src/tto/engine.py#L174) 同时要求有效温度、可信active_source和新鲜返回。40份temp状态全部是默认来源、无效、更新时间0；虽然设置了绑定字段，也不能把该字段当有效绑定证据。

离线探针只模拟“允许curve通过原mode条件”，其他条件不变。回放结果仍为0个正常起点，证明补CURVE不会单独解除现场阻塞。fan温度有数值与temp.status无效同时存在，不能据此断定TJ绑定配错，更不能用两个温度接近来替代来源核验。

最小修订：在问题表和报告验收中单列 `control_temperature_unavailable` / `control_source_unconfirmed`，把配置来源与实际来源分开。保留这40条记录；现场后续查明有效源、变量更新链或状态API/已部署固件的差异。TTO适配可以在正确的合成fixture上离线完成，但现场正常资格验收不能跳过这一项。当前材料不足以确定主板一侧根因，本轮不修主板、不改绑定。

**R02：“新GPU对象不存在”不能用gpu对象是否存在来判断**

原方案第77、81行正确要求新对象报错时不回退。但旧Orin已经使用 `gpu: {gr3d_freq: ...}`；gpu本身始终是旧合同的一部分。[当前提取器](../../src/tto/quality.py#L21)就是读取该对象。若实现成“有gpu就按新格式，没gpu才兼容”，旧Orin会被错误判为缺字段。

最小修订：明确统一GPU合同的标志，可采用独立GPU合同版本或明确的新增字段存在规则，并在两个项目同步。必须区分：legacy对象、合法统一对象、存在但缺字段/错误的统一对象。后者不得回退旧字段；有效0%不得被布尔真假判断丢掉。统一与旧字段同源冲突时撤下该GPU输入并记录原因，不默认宣布TJ数值冲突。

**R03：只写input-profile.json，不能保证同seq平台身份不可变**

[Quality.accept](../../src/tto/quality.py#L132)的指纹只包含temperature/cpu/gpu/power/memory，不含platform。实际探针在相同stream/seq下把Orin平台声明改为Thor，结果是duplicate，没有隔离。由于新平台字段尚未存在于原合同，这属于当前代码对新合同的能力缺口，不能称为旧代码已违反了未来合同。

最小修订：新合同指纹包括封存的平台字段及稳定输入含义；保持外层可增长的sample_age_ms不参与测量冲突。同身份的平台内容冲突要进入已有隔离语义并传到R3b报告，而不只记录“平台变化”。不同新身份发生平台/profile变更则断段、清历史、停止不匹配模型，保留原记录。字段缺失或GPU临时error不能随意变成平台切换。

**R04：年龄相加公式正确，但尚未定义所有消费点**

原方案第55、83行的年龄下界方向正确，但 [numbers](../../src/tto/quality.py#L9)没有观察器时间参数；[Features.mean](../../src/tto/features.py#L47)按左侧持有数值累计；[Engine](../../src/tto/engine.py#L90)遇到重复样本直接返回。仅增加GPU字段提取与valid判断，不能自动证明独立过期在当前值、缓存重发和30/120秒窗口都成立。

必须定义：来源封存时valid不等于N305接收时仍fresh。例如GPU基准年龄4500ms、外层年龄1000ms、timeout5000ms，TJ可以fresh，但GPU必须不可用。相同seq重发时推进既有单调年龄下界，不能用较小的新报告年龄“返老还童”，也不能本地经过时间算两次。

历史窗口可以使用当时仍有效的GPU观测，但不能把一次读数跨过其有效期无限左侧持有，更不能在GPU恢复后回填之前的缺口。最小实现是把每份观测的GPU有效性及必要时间证据交给统一特征器，而非让报告复制一套规则。GPU过期只撤下该字段和真正选择它的模型；未选择GPU组的M1、M0及正常TJ不能被一并停用。是否跨有效期、缺口多长才使均值不可用，须按既有“不插补”的合同冻结。

**R05：写新目录保护了原文件，还不足以保护历史成绩**

[replay](../../src/tto/dataset.py#L10)总是创建当前Engine；[recorded_results](../../src/tto/recorded.py#L72)用预测ID、run、segment、origin_ref、raw_refs和label_ref与它关联。新增平台或scope边界、重置起点间隔，可能改变旧记录回放的段号或引用支持。

负向探针只在旧run的首次平台解析处模拟新增边界，文件不改。正常合成夹具原有510条有效评分变为0，产生71条quality_origin_identity_mismatch和510条quality_score_reference_mismatch，日志没有缺失。这不是完整新实现已经失败，而是证明“当前Engine重放所有旧合同”存在可复现回归。

最小修订：manifest的record/input/feature合同决定历史回放路径；旧schema1保留原起点、段号、支持引用、控制资格和已有隔离，新schema2使用新路径。新合同诊断是另一种派生产物，不能作为旧实际预测的关联依据。原方案已有legacy原则，需要补明这个分派入口和验收。

回归必须保留44个M1起点/102条M1评分正常对照，以及R3b冲突510条排除、恢复306条有效；同时验证换模型、缺日志、降级、方法/模型身份关联与覆盖分母不变。不能把身份不匹配笼统写成丢失日志。

**R06：旧配置不能因移除不生效字段而失效**

原方案第85行允许移除旧power_current_rails，但 [merge](../../src/tto/config.py#L22)拒绝未知字段，[validate](../../src/tto/config.py#L75)还把features全部默认值冻结。Conda升级保留旧local.json，历史manifest也保存完整旧配置。

探针删除默认键后合入原配置，得到 `unknown configuration key: features.power_current_rails`。因此不能只删除defaults/validator里的字段就发布。

最小修订：选一个真正生效的有限profile作为权威来源；旧字段在旧配置合同下仍可读取，显式注明兼容含义；如需迁移则在内存中按版本迁移，保留原文件。候选安装验证应使用已有0.1.2配置、模型和数据升级，证明离线doctor及旧报告都仍能运行，而不只测试全新安装。

**R07：一份profile与四种动态配置需要明确关系**

原方案第65行推荐每run一次不可覆盖profile，第67、93行允许运行中观察到平台或scope变化后继续记录。当前 [Journal](../../src/tto/storage.py#L40)在收到第一份平台数据前已写manifest，[Features](../../src/tto/engine.py#L10)也已建立。平台初始unknown、稍后known，以及AUTO→CURVE→AUTO，都需要明确状态和持久化身份。

最小修订：把不可覆盖文件定义为“首次确认的初始输入合同”，每次变更以事件及段/起点的合同摘要记录，不改旧文件。起点必须带feature_schema/profile_id/control_scope，评分标签必须在匹配的连续scope内。unknown期间不借用已知平台历史；首次确认须清历史重新预热。出现多个不兼容已知合同后，run的混合标记不能因最后又回到初始配置而消失。

建库和加载/训练入口都应检查一致性，不能只看run的首份profile或最后状态。新增文件应进入Journal预算、收尾索引和哈希，写入失败要显式停止或撤下资格，不能继续发出无法追溯的模型预测。无需插件框架、多个自动轮转run或新的常驻服务。

**R08：CURVE应排除剩余AUTO专属诊断**

方案正确移除CURVE的gain要求，但 [Engine的firmware_45s_diagnostic](../../src/tto/engine.py#L158)也用normal门槛；report的TJ与control_temperature差异诊断同样读取AUTO相关状态。本机TianshanOS的CURVE分支更新曲线target/current duty及迟滞状态，AUTO分支才更新自适应预测状态；API仍可返回这些字段。

现场首份curve记录有实际temperature=46.3、controller_gain=0.75、control_temperature/guard_temperature/predicted_temperature均45.9。字段存在不能证明它在当前CURVE模式下被实时计算。独立合成探针把旧normal bool扩成CURVE后，会把47.5的AUTO诊断当作CURVE固件预测发出。

最小修订：正常CURVE资格与旧normal_auto分别保留，所有AUTO专属诊断明确限制在AUTO。CURVE可保留原始字段供追溯，但其预测、控制温度比较与auto_state展示要注明不适用，不能计为CURVE预测能力或新的绑定证据。不需要为此改固件。

**修订后的执行顺序**

1. 在两份方案共同冻结GPU合同存在规则、平台封存身份、独立年龄及非法/不可用处理。补列本轮控制温度来源无效，给出TTO侧准确阻塞提示；主板侧根因留作独立核对。
2. 先确定schema1/schema2回放分派、旧配置兼容和profile生命周期，再实现有限四配置。把GPU状态转换和scope资格交给同一生产链路。
3. 在监控服务提供的Orin/Thor fixture上完成生产Engine/Journal→回放→正式report；通过合成完整过程验证split→train→evaluate与固定模型输出。CURVE需要真正有效的temp状态对照，另保留本轮无效temp反例。
4. 重跑原88项及针对上述8项的新增测试，保留旧测试中正确的合同。测试矩阵除原方案项目外，必须包括同seq只改platform、旧gpu对象存在、GPU在来源valid但接收已过期、GPU恢复后的均值缺口、旧日志跨版本报告、旧配置升级和AUTO诊断不泄入CURVE。
5. 构建有独立版本/SHA的新wheel，在干净目录非editable安装，用旧配置升级对照及实际导入文件核验。交回候选、离线证据及回退步骤；软件完成不以真实模型收益为前提。
6. 后续用户批准现场窗口后，核验监控服务和TTO实际运行包、两路状态及真实控制来源，再运行有界doctor。接口适配可以离线完成；正常CURVE资格、任务响应及模型精度仍按现场实证分别验收。有效来源尚未恢复时，报告阻塞并保留记录，不改模式或放宽温度条件。

**本轮验证结果与可重跑证据**

原88项回归全部通过，耗时34.88秒；包含实际loopback协议测试、R1/R2/R3/R3b/R4正常及反例覆盖。它证明当前0.1.2基线未退化，不证明未实现的新方案通过。正式report入口已对保存的真实run重新生成新目录报告；未传实机配置，没有联网。

离线探针确认了平台指纹缺口、CURVE之外的无效温度阻塞、旧配置移除失败、旧回放分段回归及AUTO诊断泄入CURVE的局部改法风险。探针是负向设计实验，不是候选实现，也不是实机收益测试。

- [回归日志](../../evidence/orin-thor-curve-plan-review-20261012/regression.log)
- [审查身份与依赖](../../evidence/orin-thor-curve-plan-review-20261012/review-identity.json)
- [探针结果](../../evidence/orin-thor-curve-plan-review-20261012/review-probes.json)
- [可重跑探针](../../evidence/orin-thor-curve-plan-review-20261012/review_probes.py)：使用含依赖的Python执行，不连接网络；只写本审查派生JSON。
- [正式命令输出](../../evidence/orin-thor-curve-plan-review-20261012/formal-report.log)与[新生成的当前合同报告](../../evidence/orin-thor-curve-plan-review-20261012/current-production-report/report.json)

真实run及使用的旧合成run所有原始文件前后SHA一致；两份方案和生产源码身份保留在review-identity.json。没有执行新候选构建、N305安装、新接口实机验证、任务负载响应或模型训练/效果验收。本轮止于审查，不自动转入实施或发布。
