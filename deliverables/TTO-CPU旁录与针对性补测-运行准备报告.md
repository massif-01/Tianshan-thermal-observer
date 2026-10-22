# TTO-CPU旁录与针对性补测：运行准备报告

2026-10-19｜候选 **0.2.4+cpu.1**｜交回复审，**尚未获得设备连接、安装或12请求许可**。

**软件已完成：** 已准备真正可安装、可运行的CPU旁录与12请求profile，沿用closeout.2唯一采集、冻结估计、准入、Requester与归档链。原模型、旧成绩、I-02、生产观测/控制合同和fixed-anchors计划保持原件。当前只完成离线与自建服务验证，没有真实推理。

**真机仍未知：** Thor当前安装身份、jtop服务关系、GPU/rail独立刷新窗、CPU实际200ms读窗质量及旁录对原链的开销。现有数据不能回答“逐核是否比GPU＋两rail＋CPU均值多提供及时信息”。本候选为这个问题留证据，不先宣布CPU领先或预测获益。

**验证有一条必须保留的负面结果：** Mac自建服务的12条单路全部正常完成；Linux x86/CPython3.10容器安装、48项身份、CLI权限和Linux累计CPU读取通过，但该容器的一次完整链尝试在第6条后触发预登记CPU预算，停止旁录和后续请求。未调高预算、未把6条写成12条。它不能代表N305真实开销，也不能写成目标环境完整负载通过。

**建议下一步：** 先复审本包，再由用户单独批准安装/真实身份与60秒无新增负载能力核对；回执证明条件值得测、模型线冻结分析合同后，再另行决定是否批准12请求。用户暂不需要开仪表或模型负载。YET/视频均可选，缺少不延长或重跑。

## 1. 离线核对与保留结果

唯一既有真实run仍为`5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3`。field/modeling是同run两条交付。本次只读原始文件，核到2706个来源序号、12核和记录中的NVML查询周期1000ms；GPU遥测接收年龄中位518.324ms。它不是CPU物理领先518ms，原CPU原始百分比也没有精确累计计数窗。本轮没有新CPU实测、活动阈值搜索、42次重拟合或热θ更新。

附件独立复审指出的双路启动反例保留：GPU利用率仍为0时，GPU rail已从1.984W升至8.726W、21.392W。因此后续必须使用嵌套比较INPUT-BASE（GPU＋两个独立rail）、INPUT-MEAN（再加全核均值）、INPUT-CORE（再加同窗每时刻最大值），不能只比较GPU柱子或选择事后最佳核。当前不替模型线实现活动分类器或未来输入转换。

独立新说明保留`observation:4682`显式`temp_stale/auto_state=stale`与PWM25%及恢复影响；这不是只有HTTP成功或普通回落。原始示例见`checks/original-examples.json`，不覆盖旧报告、不调查失温根因、不改策略、不删除异常段。

冻结主模型SHA：`dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`；observer spec：`2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`；旧比较spec：`9b2c5586ffbd9b3daae1bddf8dd77eaf8a40d5b6b27e5e5be864cc7b3ecb7711`。新副本逐字节核对一致；旧test-used文件只读登记SHA，没有更名或修改角色。角色预登记见`config/data-role.json`：旧数据已用于开发；新本地数据仅软件模拟；未来12请求默认探索/开发，一个热过程，不自动成为独立确认集。

## 2. 来源与实现边界

本地WS代码使用独立tegrastats子进程及NVML reader，无jtop导入或IPC。已找到与历史安装回执parser SHA匹配的wheel内文件；本地platform_gpu.py/server.py也与历史回执一致，本地parser新文件另列身份，未假装它就是当前安装。**这能证明所审代码不依赖jtop服务，不能证明2026-10-19真机全部当前文件或jtop配置。** 不启动jtop、不改客户端interval、不重启任何服务。后续若需变更服务配置，另交影响说明，不能藏在录像动作里。

候选在独立`experiments/cpu_activity_pilot_v1/`。原42项中39项不变，3项为版本、runtime扩展接点及新profile许可/YET可选分支；另增5个CPU模块和1个计划文件，总48项。完整patch与前后SHA见`docs/closeout2-extension.patch`及`source-identity.json`。native采集、质量/TTL、冻结数学、I-02、原Requester和fixed-anchors计划均保持原字节。并非另造采集器或重做closeout。

| 新模块 | 实际职责 |
|---|---|
| cpu_cli / cpu_pilot | 离线preview、独立许可、固定计数profile；实际四槽容量可照实记录，本次只用1客户端 |
| cpu_source | 200ms目标读取/proc/stat与在线状态；可选现有pynvml；仅显式已确认sysfs rail路径 |
| cpu_transport | 仅复用已认证Thor SSH mux，先检查socket；禁止新TCP认证回退；源脚本/配置SHA先核对；保存N305实际到达/判断时刻 |
| cpu_interface | 严格因果可用性筛选及三组视图fixture，不训练、不更新状态、不输出控制 |

源文件记录host/boot/session、CLOCK_MONOTONIC、UTC括号/分辨率、SC_CLK_TCK、前后累计计数、每核在线状态、CPU差分窗，以及每个GPU/rail读窗、单位和可获身份。CPU total取前8计数，busy扣idle/iowait，guest不重复加；计数减少、重置、离线/缺前窗记不可用。未观测到的GPU/rail底层窗、年龄及新生成ID为null；不按值变化或查询次数判新样本。原两rail始终独立，不随意相加。

原生链实际写出唯一UUID后，源记录通过command_id和接收日志关联；旁录不能为原生数据续龄或改变准入。N305保存真实接收/生成时刻；`network_latency_s=null`，不直接减两台主机单调钟。事后只拷源文件只能评价源侧潜力；可靠映射缺失时，严格同域分析入口拒绝该源窗，模型线可另评价接收顺序，但必须保留源年龄/窗口未知，不能伪填接收时刻为源时刻。未实现任何CPU→热模型现场输入替换。

NVML/rail若只有约1秒独立信息，可保留“相对现有粗观测的活动增量”用途；不能给出亚秒物理先后结论。若模型线判断这种条件区分不了主问题，就不安排负载。

## 3. 预登记开销与停止

预算在新真机结果之前固定，文件`config/resource-budgets.json`。源CPU限单核等效累计5%（5秒后评价）、RSS64MiB；读耗时P95≤20ms、单次≤100ms、抖动P95≤100ms，约5秒滚动窗；诊断流≤100KiB/s，1秒无包即停止旁录。接收进程总CPU每秒快照≤8%（35秒后）、RSS128MiB；原生callback延迟≤250ms、成功fan间隔仍≤2.5秒，能力回执还核对callback P95相对基线增量≤100ms。

N305已有实验3.24%均值/6.88%最高单核等效CPU、95.84MiB RSS用作接收侧选限参考；Thor5%/64MiB是保守候选限额，尚未现场证实。60秒能力核对前30秒参考、后30秒旁录，短窗不证明长期无扰动。原始资源、抖动、读耗时、字节量和原链延迟保留；CPU不能区分所有模型进程和监控干扰，报告必须标明这个混合来源。

超预算先停旁录；pilot中停止后续派发并沿用有界自然drain，保留已有TTO记录。未在准备期取得旁录时不启动请求。不会改采样、放宽TTL或提高限额凑完成。`inspect_capability.py`只生成离线软件资格回执，不自动授予负载许可；execute还需新command、回执SHA及另一次用户决定证据。

容器负面记录：第35.930秒接收进程快照202.262%单核等效CPU，触发8%限额；6条已完成，停止原因为`sidecar_unavailable_no_meaningful_pilot`，sidecar原因为`receiver_total_resource_budget_exceeded`。这是本地Mac上的Linux x86容器数据，不能外推N305；完整失败日志和当时wheel副本留在`checks/target/`。后续安装检查只证明最终wheel安装/权限/源读取，不补称这一尝试完成。

## 4. 固定未来计划与许可分层

审查方pilot-plan原字节保留。60秒准备/能力段→180秒驻模背景→6条孤立自然完成，各后等30/60/35/55/40/50秒→6条串行自然完成→180秒最终回落→最多120秒清理。原resident模型、原messages/sampling、256token、30秒协议预算、1客户端；约14—20秒自然短工作，不称2秒任务。

最坏正常预算60＋180＋12×30＋270＋180＋120＝1170秒，硬1200秒。等待、暂停、连接准备和drain共用预算；1080秒起停止新工作，不额外叠加12次90秒drain。原固定不可用/明确异常/未知结束规则保留，model available、measurement、control和当次许可分别判断。未知SSE/HTTP结束停止后续；清理不表示服务端GPU已停止。无旧M/Y override、无自动换模型/补跑/延长。

源侧需未来单独部署只读脚本/配置，使用现有Python及NVML绑定；N305需独立prefix安装此候选。现阶段没有安装过真实设备，也不授权板端刷写/服务重启。回退是停止本候选及旁录、保留文件，原TTO与closeout.2未动。

YET导入工具原字节复用并交回：动态文件/新run/实际行数，Date+Time、CH1、Celsius、原1秒格式；没有沿用81条断言或旧run。可选记录仍同鳍片位置、首末独立时钟锚点，原日期/SHA保留；旧M24°C不移入。jtop录像首轮可不做；若未来已确认不影响服务且录制，只在Mac显示端保留原视频、PTS/帧率、界面真实刷新与任务标记，不OCR造毫秒曲线。两者缺失均不触发重跑。

## 5. 有限验证结果及复验入口

| 实际检查 | 结果/限制 |
|---|---|
| 12项局部测试 | 通过：完整虚拟等待/预算，STOP自然结束，未知结束不续发，1080边界，CPU计数/离线，缺失/陈旧/时钟/序号，因果筛选，许可/容量，mux命令与源SHA启动保护 |
| 原计划完整虚拟时钟 | 12×30秒正常完成；1秒驱动tick含调度额外12秒，结束1062秒＋120清理=1182秒；未改1170理论表，剩18秒；正式0.1秒调度实际开销另记 |
| Mac自建服务实际链 | 12份SSE均正常，单路峰值1，原生run/engine/observer各唯一；测试进程缩短等待，仅证明链路，不冒称正式20分钟过程 |
| 未知SSE / STOP / 缺旁录 | 未知仅发1条；STOP后无续发；缺旁录0请求；原始失败和结束状态保留 |
| 60秒无负载自建诊断 | 0 Requester、0模型查询、0推理POST；仍记录原生measurement/model/control层 |
| 最终Linux x86 CPython3.10安装 | 独立prefix、精确原依赖、48项身份、无许可execute拒绝、Linux原累计计数读取检查；非N305现场安装或完整12负载通过 |
| 目标容器完整链尝试 | 6条后预算停止，作为负面证据保留；没有放宽限额重跑这条完整尝试 |
| 因果/缺失fixture | 未来到达、陈旧、未知时钟不进入新视图；null不补零；录像/YET不是必须输入；原热模型无新CPU注入 |

源码`tests/test_pilot.py`；真实自建服务驱动`tests/integration.py`；最终包目标检查`tests/target_check.py`。12项测试并非全仓189项，也没有重拟合旧模型。`docs/source-identity.json`逐字节证明原source合同未改；新旧候选不能仅凭同版本号混认，最终wheel及交付清单SHA为准。中间容器安装回执均按其当时文件身份保留；最终交付身份以`checks/target-delivery/identity.json`为准。

运行入口、安装/回退、两次独立许可、新binding、STOP及归档步骤见《一页操作卡》。准备阶段已结束：未申请或执行现场动作，等待独立复审，不自动进入能力核对或12请求。

## 6. 证据导航与指标依据

证据包包含`source/`独立源码、局部patch/清单、配置/角色/分析fixture与原YET工具；`candidate/`最终wheel、既有安装器与精确依赖wheelhouse；`checks/`离线核对、有限测试、完整自建run、目标安装及失败日志；`inputs/`复审依据与历史来源文件。旧大实验包只按既有身份引用，不递归打包或复制旧成绩作新成绩。

本次输入ZIP SHA为`4a5f2897e3f19cc13d873d26da8144308d7b9d6fe0b7f917f8631d804df280f0`。最终wheel为122051字节，SHA `3a0d118a50a93a8d77a3dc714a546bd98d28f7b9254acb69084da9806628ac92`。本次package manifest按真实字节生成，ZIP CRC/SHA与清单核验回执随交付。

指标语义以官方资料约束，不据公开新版本猜本机版本：[/proc/stat与iowait限制](https://docs.kernel.org/filesystems/proc.html)、[jtop服务interval与interval_user区别](https://rnext.it/jetson_stats/reference/jtop.html)、[NVIDIA GPU利用率采样窗说明](https://docs.nvidia.com/deploy/nvidia-smi/index.html)。200ms查询与底层采样精度分开；以上资料不是本机能力或CPU领先证明。
