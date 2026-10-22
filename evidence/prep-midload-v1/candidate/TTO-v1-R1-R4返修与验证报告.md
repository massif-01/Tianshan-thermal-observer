# TTO v1：R1—R4返修与验证报告

**四项已在锁定依赖下关闭。软件返修已验证，真实预测效果待验证。** 本轮继续当前TTO工作树，先复现原问题，再修改生产调用链、补回归并构建0.1.1候选；保留原架构、双路只读采集、身份/新鲜度、成功PWM、特征器、Ridge、15/45/90秒、冻结模型和资源限制。

日期：2026-10-11（Asia/Shanghai）。执行依据：TTO-REPAIR-v1.0、独立复审与原TTO-PLAN-v1.0。目录：`/Users/massif/Tianshan-thermal-observer`。没有真实设备连接、部署、源服务重启、负载、风扇/绑定/曲线/增益/保护调整、CUDA或Git提交/推送/PR。

## 用户工作流与关闭结论

|问题|是否关闭|修复前与修复后的行为|
|---|---|---|
|R4 WebSocket握手跳转|关闭，真实loopback|锁定aiohttp3.11.18原反例第二目标收到1次请求和非敏感测试header；现在跨源和同源未授权路径目标均0请求，正常WS/polling/GET及有界关闭通过。|
|R1 跨run时间/过程|关闭，离线|原A-B-C-D-E-A被分为train/train/val/test/test/train；现在创建和直接校验均明确拒绝并给出run/时间/过程冲突；相邻A-A、正常唯一过程与单run探索保留。|
|R2 分层比较|关闭，离线|原四方法总交集为0，阻挡M0；现在基线层266点、M0层198点、M1层0点的45秒结果分别呈现，M0可独立判断，M1缺项不算成功。|
|R3 实际旁路报告|关闭，离线实际落盘|原44个M1起点/102条M1评分未进报告，移走日志也不变；现在报告读取102条实际保存的M1评分，模型更换不改统计，移走应有日志明确缺证据。|

R2/R3数字都来自固定合成夹具，只证明软件路径。R2进入非模拟判断分支时，仅在决策函数内使用明示测试副本；保存的数据、评估、Markdown/HTML始终标模拟。102是起点/时距评分记录，不是102个独立过程。

三项单独裁定：

1. **基础采集可进入180秒真实只读检查的条件已具备。** R4与完整协议回归通过；目标机安装、端点与最终部署身份仍须现场核对。这是软件条件，不是本任务授予真实访问权限。
2. **可使用合法的新切分和分层评估决定模型价值。** 必须具备真实部署/数据质量和未使用的独立过程；旧无效或时间证据不足的清单不能继续使用。本轮没有真实模型收益结论。
3. **shadow报告能展示当时保存的预测与评分。** 已验证生产Engine/Journal落盘、正式CLI report、模型文件改变、缺日志、未评分、降级与旧记录兼容；实机在线表现仍待真实记录，不冒充新独立留出或降低PWM证明。

## 起点保护与原反例

修改前源码/defaults共18项与复审candidate逐字节相同，原wheel SHA `2498062c139b70241a42c942305e269d2c4f88bf153fe6b35ba4bc3d5299b03b`、原ZIP SHA `27772983e7c5155da9b2dffca3a69c48342d1d360968275c40574515c0d5a354`匹配。它们只标识修改前起点，不能作为返修验收。

Git原状态main无提交、项目文件未跟踪；已有未提交文件、.DS_Store及旧交付均保护。已保存未忽略工作树完整ZIP、逐文件SHA、Git状态与tracked diff：`evidence/repair-v1/before/`。tracked diff为空不代表项目无改动；本轮增量patch以保存快照对照当前源码生成。

复审包完整保留在`evidence/repair-v1/review-original/`，candidate没有覆盖工作树。原两个反例脚本在当前修改前生产实现下运行，结果见`before/model-probes.json`与`before/ws-redirect.json`。记录器原本可在发现缺陷后退出0，所以关闭依据是行为断言而非退出码。

本轮也用依赖完整、非editable的原0.1.0安装重跑保存的原61项：**61通过**，见`before/original61-tests.txt`及XML。独立复审的54通过/7未执行仍是其原环境事实，本报告没有将之改称旧版已独立全量验证。

## 根因、修改位置与验收

### R4

`src/tto/collector.py::sessions`的外层_request不在底层_ws_connect实际HTTP调用链中。现在使用会话局部TraceConfig：request_start核对实际method/origin/path，request_redirect在aiohttp跟随Location前关闭响应并拒绝。没有给ws_connect塞不支持的参数，没有全局猴子补丁、改第三方文件或关闭TLS。

锁保持aiohttp3.11.18、Socket.IO5.13.0、Engine.IO4.14.0。两个polling传输HTTP槽和ESP单在途GET保留。新增`tests/test_repair_r4.py`与原`test_network.py`真实服务测试覆盖跨源、同源未授权路径、GET原限制、正常WS/polling/心跳重连及失败后关闭。目标计数0是决定性断言。

调用链依据：[aiohttp v3.11.18官方client.py](https://raw.githubusercontent.com/aio-libs/aiohttp/v3.11.18/aiohttp/client.py)；关闭结论来自本机锁定版本真实运行，不沿用另一版本推测。

### R1

`src/tto/dataset.py::replay/build_dataset/chronological_runs/freeze_split/check_split`登记每run实际接收UTC范围与其单调锚点，核对时钟一致性，并检查全部run顺序。名称不连续复用、时间范围交错或证据不足会明确拒绝；不自动改名、删后段或增加独立实验。

创建和消费都使用相同规则。train/evaluate继续调用check_split；直接手工构造旧错误清单也被拒绝。跨分区边界按各runUTC锚点转换实际支持区间做purge，单run、原始引用、来源SHA和未来扰动回归保留。不同run单调时钟不直接相减。

`tests/test_repair_r1.py`覆盖原序列、相邻A-A、输入顺序打乱但实际时间合法、直接反转分区、缺UTC证据/交错、跨run支持重叠及单长过程。单run --exploratory即便UTC跳变仍使用自己的单调时间隔离，明确不证明跨过程泛化。

旧dataset缺少足够时序锚点时，必须从保留的原始run在新路径重建派生结果；旧split/model/test-used不覆盖。真实已看过测试的身份不会因重建而变未使用。本轮全部重建仅为合成夹具。

### R2

`src/tto/evaluation.py::comparison_layers/layer_judgements/value_conclusion/evaluate`固定基线/M0/M1三层同起点、同标签集合。每层独立给计划数/共同数/覆盖、过程、阶段和全部时距指标；判断只用该层内部成绩。旧四方法字段保留为M1层兼容视图，不再作M0前置门槛。

`src/tto/report.py::evaluation_report`的JSON/Markdown/HTML共用comparisons，三个时距保留，45秒过程/阶段可读展开；不同层MAE不能直接比较。全量方法覆盖、缺项/fallback与欠/过预测保持。基线-only正常出报告；部署未知、少过程、只待机、无稳定收益与模拟结论保留。

`tests/test_repair_r2.py`保持训练/验证不变，只移除测试M1已选字段；重训methods完全相同。覆盖全部缺项、局部缺项、四方法完整、只有基线及格式一致。两项原决策函数测试仅适配输入到明确的新分层合同，原断言场景未删除。

### R3

`src/tto/recorded.py::recorded_results`从已有日志按预测ID/horizon/method/model SHA关联；不读取当前模型，不重算模型预测。新manifest在`storage.Journal/collector.collect/cli`保存报告类型和当时模型SHA；`engine`追加评分带模型身份。旧评分缺SHA可由唯一预测身份追溯当时预测记录，不能按行号硬拼。

`report.summarize/run_report`区分collect质量、离线holdout评估、shadow保存事实。记录已发/可评分、MAE/RMSE/绝对误差P95/偏差/欠过预测、计划覆盖、实际方法、fallback、未评分/跨段/缺项及原始/日志行引用。缺日志时未知数量为null，明确缺证据；有但空评分日志明确等待/未能评分；无模型明确只有基线。CLI只回重点与路径，技术细节在JSON/HTML中。

`tests/test_repair_r3.py`验证正式report入口、直接汇总原日志、替换/移开当时加载的模型文件统计不变、原预测评分字节不变、缺日志/空日志/无模型、部分降级、评分重排和模型身份不一致。图按预测目标时刻对齐。

## 最终候选与完整重跑

- 新版本：**0.1.1**。
- 新wheel：`wheels/tianshan_thermal_observer-0.1.1-py3-none-any.whl`。
- **最终wheel SHA-256：`f7dca909cbc6c19a5316b29be715c590e291c212575dcb30fb1139e138c509f6`**。
- Python：CPython3.10.18；开发/验收主机macOS ARM64。目标N305/Ubuntu22.04未运行。
- 依赖锁未改变，SHA：`426fa81527a8e31213b3ea49b4841cb1f7b9b9f1b4702f1dcaeb625a95a6f97a`。
- 源码/defaults19项 = wheel内文件 = 干净site-packages实际导入文件，逐字节/逐SHA核对；身份见`evidence/repair-v1/delivery/identity.json`。
- 新wheel干净非editable安装的**81项回归通过**，包含原61覆盖与必要新增/参数化场景；随后离线doctor、模拟采集→合法split→train→分层evaluate、生产Engine/Journal→实际日志→正式shadow report、真实loopback协议及自有CLI信号、独立训练入口全部通过。

一条重跑入口：安装新wheel与锁定依赖后，运行`python scripts/reproduce_offline.py --output 新目录`。它包含`verify_r1_r4.py`的标注适配版；原复审脚本保留原样，适配只处理修复后的拒绝/分层接口，没有改实质输入。准备依赖可以下载包；重跑本身只访问自己创建的loopback，测试信号只发给持有PID的子进程。

三类代表产物在`evidence/repair-v1/delivery/simulation/collection-report`、`simulation/evaluation`、`repair-probes/shadow-report`。同一候选的模型缺字段反例在`repair-probes/missing-m1/evaluation`，结果与关闭摘要在`findings.json`。仅包含合成观测，不含真实私人记录。

本轮增加了实际Markdown换行/场景分隔符核对，格式断言通过；浏览器检查模拟标记、模型身份、实际评分与三层报告可读，控制台0错误/0警告，请求仅loopback报告。完整技术数据仍可直接打开HTML，没有常驻仪表盘。

## 失败记录与剩余限制

- 修改前R4断言失败与原反例数据保留，随后目标0请求通过。
- R1新增夹具首次把“反向传入文件列表”误当“时间排序后的run列表”校验索引；修正夹具按实际episode找run，保留原失败日志，生产行为不靠改反例变绿。
- 两项原值判断单元测试因分层函数输入合同更新而适配；原61未改版本另在0.1.0实际重跑，返修所有场景在0.1.1重跑。
- 中间构建、旧成功/失败日志分开保留，不作为最终候选。最终验收仅认delivery身份、当前wheel及独立重跑。
- 跨run严格顺序依赖可核对的本机接收UTC与单调锚点。时间不足/冲突时拒绝严格未来留出，不能用主机文件mtime或不同run单调数值猜顺序。
- 旧run没有模式标签且预测日志全丢失时，不能复原历史模式/模型；只给可验证质量与具体缺证据，不冒称完整旁路统计。
- 训练保持原共同可训练起点与冻结模型格式；本轮修的是评估分层，没有扩展新模型路线、插补或超参搜索。
- 没有N305安装/资源、真实180秒doctor、真实模型价值或长期旁路验证；本轮未开展全仓fuzz/安全平台/其他项目审计，也未确认需要另行并入的独立缺陷。

**本轮结束于交回独立复审。** 可在用户后续自行运行或另行明确授权后做有界真实只读检查；本任务未自行转入实机或长期运行。软件返修已验证，真实预测效果待验证。
