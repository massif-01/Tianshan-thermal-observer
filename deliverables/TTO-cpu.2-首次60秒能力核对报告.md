# TTO-cpu.2-首次60秒能力核对报告

目标安装通过，唯一一次原生记录已完成；CPU旁录仅取得约5.20秒，能力门槛未通过。暂不进入12请求。明确障碍是N305接收进程总CPU超出原8%单核等效预算，且旁录启用前就已明显超限，不能直接归因于旁录。未调整预算、修改候选或补跑。

本次没有推理请求、模型列表查询或模型重载；没有创建Requester、启动jtop、要求YET或改变风扇/TTL。模型线仅用冻结工具离线判断本轮局部数据，不能以短片段证明CPU先导或预测改善。

## 1. 本轮身份与实际时间

- command_id：`cpu2-capability-20261020-1ca3a249-8ea9-4608-aa05-105f9aff5614`。
- 唯一native UUID：`80938521-b659-4160-a7b2-5fdfb6ebc197`；1个原生采集器、1个估计器、0个Requester，退出后自有async任务0。
- 2026-10-20北京时间22:02:51.366调用本轮入口，22:03:51.936退出；实际runtime为60.038918秒，原因`diagnostic_duration`，native原因`duration`。调用时间含导入/退出，不代替runtime时钟原点。
- t=30.013864秒安排旁录，mux检查约7.95ms；t=30.022912秒启动源子进程；t=35.487110秒因`receiver_total_resource_budget_exceeded`停止旁录。原生链继续至60秒。
- 两台主机分别保存CLOCK_MONOTONIC、host/boot、UTC括号；Mac前/后UTC仅约束读取过程。跨主机精确偏移、单程延迟、NVML独立生成窗口未知，不写零延迟或毫秒物理领先。

## 2. 已审候选与目标安装

|项目|实际核对|
|---|---|
|wheel|`tto_field_candidate-0.2.4+cpu.2-py3-none-any.whl`，123392字节|
|wheel SHA256|`b265045129c67f62fd28bdb15f5f6288a29ef5a682a54175c1e998529bfe35fa`|
|安装prefix|`/home/rm01/TTO-field-cpu2-capability-20261020`，全新独立目录|
|目标核验|Linux x86_64，CPython3.10.22，`verify-install --target`通过，48项文件|
|主要依赖|aiohttp3.11.18 / socketio5.13.0 / psutil7.0.0 / numpy2.2.6 / scipy1.15.3|
|原依赖|20个wheel与已接受cpu.1归档逐字节一致；新wheelhouse只有cpu.2一个候选|
|cpu.1归档SHA|`bc6cf12b845d11f964253346c24b254fe2bf558eb183004a2d8b0d595c5d3693`|
|源脚本SHA|`7f674e6913458dc73e8a677fbb46d6574812da05c5a5ba2938d126b53ca14382`|

安装使用原安装器，未覆盖原TTO、closeout.1、closeout.2或基础解释器。完整解释器字节SHA、23个已安装分发包身份和pyvenv来源见`field/interpreter-dependency-identity.json`；原cpu.1交付/锁定依赖保留。没有为来源报告器修订重打运行wheel。

用户本次明确批准安装/只读源放置/单次能力记录，并另准许密码恢复连接与确认N305新主机密钥。密码仅用于交互认证，未写入配置、脚本或证据。记录启动前N305→Thor复用已认证成功，实际旁录只复用这条通道。原N305 known_hosts未覆盖。

## 3. 原生链与旁录数据

|指标|实际值|
|---|---:|
|native callbacks / WS包|193 / 60|
|TJ与两rail可用覆盖|59.495s|
|模型可用覆盖|50.476s；初始化/临时态另保留|
|控制上下文可用覆盖|54.426s|
|成功fan最大间隔|1.041912s；超过原2.5s共0次|
|wire / arrivals|27 / 27；首包只有原累计计数，不能构成前后差分窗|
|完整CPU窗口|26个，源侧跨度5.200243s|
|CPU读取间隔中位 / P95|0.199999 / 0.200158s|
|在线核 / possible核|0–11 / 0–13；12、13原始记录为offline，不补成在线|
|SC_CLK_TCK|100|
|源读耗时P95 / 最大|3.300 / 7.836ms|
|源deadline jitter P95|0.280ms|
|源CPU（累计5s后最大）|1.958%单核等效，门槛5%|
|源ru_maxrss峰值|43.488MiB，门槛64MiB；原峰值未丢弃|
|接收数据率（整片段粗估）|约30.76KiB/s；不是源独立生成频率证明|

累计计数、每核在线集合和前后读窗保留。利用率总量取前8项，busy=total-idle-iowait，guest不重复加；离线/负差分/零窗标不可用，首包不伪造利用率。

NVML读取有值，单位percent，driver580.00、binding13.615.71，但generation/source_window/age未知。直接旁录rail配置为空，避免猜sysfs；原生WS约1秒的GPU与独立两rail继续作为BASE，不能把重复NVML调用当200ms独立GPU采样。

Thor沿用既有WS解释器；现场已有jtop进程作为背景，未打开/重启/改interval。旁录本身与模型进程/其他CPU活动不能完整归因；本轮不宣称逐核新增活动来自推理。

## 4. 为什么能力未通过

原回读器`qualified=false`：包数不足100、旁录未正常覆盖至native结束；其余所列延迟、完整native、CPU窗、读耗时、抖动、fan间隔检查通过。这是完整的一次原生诊断与失败的旁录能力，不是整轮丢失。

|实际阶段|接收CPU均值（单核等效）|CPU峰值|RSS峰值|
|---|---:|---:|---:|
|旁录前0–30s|166.16%|184.81%|73.47MiB|
|实际旁录30–35.487s|167.84%|176.49%|73.88MiB|
|旁录停后35.487–60s|167.46%|179.71%|74.21MiB|

触发时接收CPU176.49%，超过原8%门槛；RSS约73.88MiB，小于128MiB。源预算未触发。接收高CPU在基线已存在，停旁录后持续，因此仅能确认“接收原生/估计执行链总开销不满足原预算”，不能确认是网络、旁录、BLAS线程或具体函数造成。本轮未扩展根因剖析、改环境线程数、调门槛或重跑。

回读器把30秒后统称sidecar区间；本报告另按实际停止点拆分，避免把后24秒无旁录的资源当持续旁录开销。原回读结果不覆盖。

本轮native callback lag P95：基线4.919ms，30秒后5.097ms，均在原门槛内；这不抵消CPU超预算。诊断`start_allowed=false`是预期，measurement/model/control覆盖分别记录，不按单一红绿判全盘失败。

## 5. 模型线联合判读

使用原唯一bridge `cpu-arrival-bridge-1.0.0`，SHA `8d6fe5f013e67d2a26c192419b0b82f29a4c1aa794ddd598e2f6ba33a45045e3`。来源报告器独立修订为`cpu-joint-reporter-1.0.1`，只区分合成/声明现场证据另核/未知，未改cpu.2、冻结θ/活动参数、旧成绩或旧回执。

模型线实际使用本轮27包、221个FRAME及60个原始TJ起点完成判读，结果在`experiments/thermal_cpu_capability_review_v1/`。来源报告器正确标为“声明现场，证据另核”；独立host/boot、源代码/配置SHA及同run关联核对成立，跨机精确时窗映射仍未知。

1. 新增CPU累计计数窗可追溯；26个完整窗、实际源跨度5.200秒。接收侧CPU资格支持约5.096秒，资源停止即撤销，没有按旧CPU期限继续使用。CPU新包不续龄GPU/rail；该能力不等于整30秒或低开销能力已通过。
2. 按真实接收顺序可比较BASE/MEAN/CORE。有限背景中BASE为IDLE约59.515秒，MEAN/CORE同为ACTIVE约4.695秒，两CPU分支状态与预测完全相同。说明存在背景CPU活动，不能将其归因为推理，也没有证据证明逐核相对全核均值的新增价值。已有jtop等背景影响未分离。
3. 15秒三分支共同仅5点：冻结MEAN/CORE MAE均约7.120°C，G2-HOLD约0.0618°C。45秒和90秒的CPU共同评分点为0；60个TJ起点分别只有45/15/0个15/45/90秒标签，未整行删掉或补造。该极小背景片段的负结果保留，不能当成12请求任务识别成绩、独立热过程或模型泛化结论。

建议先停在接收总CPU超预算这一明确障碍，不进入12请求。原热模型SHA `dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`、observer spec `2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`、活动candidate及原分析spec不变；新资料只作诊断/开发分析，未选参、重训或替换旧成绩。CPU“接收+1秒”仍是研究资格支持，不是精确源龄。每秒抽取200ms窗是交付节奏对照，不是重建1秒积分窗。

## 6. 附加任务：N305 OpenClaw清除

本次用户另行明确要求“删干净”。在能力记录开始之前，已停用并卸载用户级OpenClaw/Wukong和系统级Wukong服务，移除`/usr/lib/node_modules/openclaw`及`/usr/bin/openclaw`、两套专属数据`.openclaw`/`.openclaw-wukong`、启动脚本和临时目录。记录结束后清除两条shell补全引用及rm01/root下5个OpenClaw专属npm缓存键。常见安装/缓存位置的有界补查还发现`/root/.openclaw`旧状态库，已整体移除，未读取或导出内容。

独立回读：服务/自启动/进程/命令/专属数据均未检出，shell引用和专属缓存键均为0。Node/npm和旧TTO/基础解释器保留。共享系统journal、shell历史等历史审计未全局清空，不为清理一个应用删除其他程序的日志。

## 7. 归档与停止边界

电脑侧目录：`evidence/cpu2-capability-20261020/remote-result/`；同run原生raw/manifest/summary/files、states、admission、protocol、resources、wire/arrivals、事件/stderr、本轮配置/preview/binding/permission和源SHA均保留。原始run文件不改写，派生统计另存field/。

传输清单、外层run索引、native索引逐项校验60项全部通过；最终交付另附SHA256清单与ZIP校验结果。依赖大包只按已接受SHA引用，最小包不递归复制55MiB wheelhouse和大历史归档。

本轮不做12请求、不重训、不改Web UI/GitHub或生产控制代码。后续先针对接收原生/估计链高CPU提出有限处理与独立复审，再由用户另行决定是否安排补测；本报告不签发下一轮许可。

模型线正式交付：`deliverables/TTO-cpu.2首次60秒能力记录-模型线判读/`，小包1110482字节，SHA `67509182cfbe5854ef11ae19ce0f1555b0900e55a091d7281dffb46ac339cb5c`；独立解包复跑通过。来源标签修订包148322字节，SHA `1eb81c988822819590903850c0479984b5266031f1eb60e4327146ce6d3084cf`，3类来源测试通过。模型线原始比较与跨节奏共同比较分别保留；后者共同4点，MEAN/CORE仍完全相同（MAE8.881962°C，HOLD0.047212°C），不混用样本集合。上述两包随统一证据包提供，不递归加入大历史包。
