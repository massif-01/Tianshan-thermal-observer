# TTO-observe.2：长时运行有限收尾报告

2026-10-21 · TTO-OBSERVE-LONGRUN-CLOSE-R1 · 仅离线与自建服务，交回复审

**O1/O2已修复并封存独立observe.2，observe.1原件保留。** 实时observe不再保留SavedStream全历史quality，完整输入与质量仍写盘；运行中的history按数字片号读取，最近记录与关闭后相同。冻结模型、输入有效性、TTL、单线程、128MiB/8%预算及原试跑计划均不变。

**实际验证：原24项观察回归加2项修正/相邻检查，共26项通过；86400条新旧投影串行SHA一致；已有状态回放通过；一次65秒自建loopback、一次STOP和归档校验通过。** 未访问设备、部署或发负载。Linux x86_64/Python3.10安装与真实2小时/24小时仍待当次现场许可和严格目标核验，不能以本地Mac结果代替。

## 最终身份和窄差异

|项目|身份|
|---|---|
|新版本|0.2.4+observe.2，65项运行文件|
|wheel|160088 bytes；SHA256 481a9671148fe40fcc33c2a65bc98c818be3178fe3138c1cd06bc93b3d21b725|
|candidate-files|SHA256 28680be46280395e4257a4e5beaf07a30b0c4b781797604439cb7bb622eddd84|
|原observe.1 wheel|SHA256 492916f2f6f50fe69853e3b248ecf266283d52eca2c2fbf1c80e48b45178ba06|
|原observe.1完整ZIP|SHA256 b303cfe7d3dfe017277897b525d4b97c32675aa1ec87c36664535b569bf8c139|

运行文件仅修改projection.py、observe_runtime.py、observe_cli.py及版本__init__.py，另更新candidate-files；61项运行文件字节不变。pyproject、封存/装包脚本、文档和相应测试按新版本登记，完整局部patch与逐文件前后SHA均随包。没有新增依赖，仍21个原锁定依赖；没有修改生产根目录。原observe.1源码、封存包和交付等1060个文件核对未变。

冻结primary dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0、spec 2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b及整个A1、I-02、数值线程、quality engine和推理事件模块均字节不变。本次projection确有诊断保留改动，不能再称该文件与observe.1完全相同。

## O1：去掉实时路径不用的全历史诊断保留

根因是SavedStream.feed对每份quality永久append。observe并不读取这份列表计算状态，而磁盘已有完整raw_quality，所以没有保留全程内存副本的必要。

SavedStream新增明确的retain_quality_history关键字，默认true，保留旧离线工具兼容路径；唯一observe Consumer明确传false。两种策略都累计quality_seen，只有旧离线策略append。运行summary.projection_diagnostics给出retain_history=false、retained=0、quality_seen，以及完整磁盘流observations；按stream-index定位实际分片，未删减raw、I-02或质量字段。

使用原自建服务native schema的一份源记录，按1Hz递增时间/序号分别在两个独立进程加速处理86400条。没有网络、设备、拟合或请求；这是一日数据量，**不是实际跑24小时，也不证明物理预测准确性或N305内存承诺**。

|输入条数|旧版缓存条数/RSS MiB|修后缓存条数/RSS MiB|
|---:|---:|---:|
|1|1 / 56.22|0 / 55.41|
|21600|21600 / 122.69|0 / 57.31|
|43200|43200 / 187.61|0 / 57.42|
|86400|86400 / 317.45|0 / 57.45|

独立进程PID 16297（observe.1）与16518（observe.2），基线RSS分别56.20/55.38MiB，最终增加261.25/2.08MiB。每小时阶段、实际Python/依赖、RSS、源码SHA、进程身份和墙钟耗时在O1-before/after.json。两边86400条全部被原质量引擎接受，所有输出帧按原顺序序列化的SHA均为：

`63447511dbd0159794f3dac6a4aac783ecd1cb9ba52d7a638667955158840e85`

另复用原181条保存状态回放，10391个语义数值字段最大差1.99e-13，小于1e-8，模型传播/有效性语义不变；结果标replay，不覆盖旧成绩。没有再做历史179请求回放或拟合。

直接相邻容器只读核对：原生features保留180秒且4096项硬限；observe队列64、过去TJ181、事件去重4096、诊断统计4096；评分数组受24小时/5秒起点上限限制，待成熟项按时距/失效出队。没有发现需在本轮另改的同类全程quality副本；未扩展全仓性能审查或改变事件线。

## O2：运行中最近历史按片号，而非字典顺序

原先states.jsonl与states-0002.jsonl等按字典序排序后倒读，首片被当成最新。新代码仅识别该逻辑流的准确文件名，首个无编号文件按第1片、后续按数字片号排序；observations-0001也按片号读取。关闭后仍复用原stream-index。

同一真实SessionStore写0..19，仅缩小本地chunk_bytes触发轮转，实际安装后CLI回读：

|候选|运行中last3|关闭后last3|
|---|---|---|
|observe.1|[1, 2, 3]|[17, 18, 19]|
|observe.2|[17, 18, 19]|[17, 18, 19]|

新增测试覆盖states/predictions无编号首片、observations编号首片；last=3/7/25（跨片及超过总行数）；运行中与关闭后逐行一致；读取前后原字节不变；无关前缀文件不混入；9999→10000保持数字顺序。只读history不初始化采集器/模型/网络，不改变轮转、采样或热状态。原24项中跨5个虚拟4小时轮转的状态连续检查继续通过。

## 有限集成结果及环境限制

本地明确使用macOS ARM64 / Python3.12.3，原NumPy2.2.6/SciPy1.15.3等已接受依赖，独立新prefix安装新wheel，实际verify-install核对65项通过。起初默认python3已变为3.14，安装器按版本合同拒绝；未豁免，改用明确3.12解释器的新prefix，失败准备目录保留。目标--target在Mac按预期拒绝；本机无python3.10、Docker daemon socket不可用，没有为此安装或启动环境。

最终一次CLI loopback：65.223秒，PID 16265，native UUID 54ac2409-0a01-46ba-92dd-5138f80acf46，208条观察/状态、117条发布、15条成熟评分。fan长缺口、断连恢复、保护状态变化及模型降级/恢复沿用原脚本；1 collector、1有状态估计器、0 sidecar/Requester/推理查询。实际同PID单线程回执保存；62份quality全在磁盘、quality_seen=62、内存retained=0。平均CPU 0.688%单核、RSS峰值71.97MiB，仅本地短合成场景，不与旧CPU成绩混比。

STOP 1.060秒退出，forced=false，未停止其他服务；loopback与STOP的各21项文件索引逐字节SHA/大小复核；STOP归档21项验证通过。原始失败反例、回归原始日志和所有收尾回执随包，没有选择性替换成绩。

## 操作卡和原试跑计划

安装器、preview、新registration/grant、status/history/stop/archive和回退继续可运行，操作卡仅更新新版本及O1/O2检查。原TTO/cpu.3/closeout/observe.1与基础解释器保留；依赖无增量。现场必须Linux x86_64/Python3.10精确依赖并verify-install --target，不用Mac或主审Python3.13豁免。

后续仍由用户一次批准具体设备、配置、源端点、目录/预算、窗口与停止负责人：首台前2小时健康检查，同一窗口最多24小时，首批最多3台；不机械再加60秒。观察为0Requester，普通fan缺口保真降级，不要求CPU、YET、jtop、Web UI或通讯Issue全部关闭。停止、归档、回退保留原边界，不自动延长/重启或发负载。

附件03已转交原模型线和推理线仅知悉，无新增开发要求。新模型/旧成绩未动，CPU能力/12请求循环继续暂停。本轮封存后停止，交主审只核O1/O2增量，不自行登录或部署。
