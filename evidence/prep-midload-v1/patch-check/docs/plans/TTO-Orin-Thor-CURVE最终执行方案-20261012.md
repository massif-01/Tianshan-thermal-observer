# TTO Orin Thor 与 CURVE 最终执行方案

版本：TTO-PLATFORM-CURVE-v2.0。日期：2026年10月12日。

目标是交付能够自动识别Orin/Thor、正确记录实际数据并解释可用性的TTO及配套监控服务候选。测试者无需手选平台；现场CURVE保持原状。软件与离线验证完成后即可交付，真实模型效果及现场安装另行验收。

本方案同时落实 TTO 独立审查和 WS 会话本次八项修订。第4节是两项目新增接口的唯一合同，版本为 TTO-PLATFORM-CURVE-v2.0；此前两份方案的共同段同步本文，不得各自另定字段。TTO 既有 CURVE、历史记录、模型和报告审查要求保持。

用户现已授权分仓 Goal 本地实施：WS 会话只负责 rm01OrinStatus，已有实施会话只负责 TTO。各自保存并接续已有改动，不同时修改对方仓库；授权不包含设备连接、部署、服务重启、真实采集或发布。

## 1 用户应获得什么

测试者安装候选、填写两路真实设备地址，再运行有界检查。报告直接告诉用户：识别的平台、收到的新TJ、GPU/功耗/PWM覆盖、实际风扇模式、控制温度来源是否有效，以及哪些条件阻止建模。

| 用户目标 | 软件完成标准 | 仍需现场证明的事项 |
| --- | --- | --- |
| 成功探测数据 | 正确读取支持的输入；缺失、错误、过期分别提示；不造值 | 当前端点可达、源包已生效、真实输入按合同更新 |
| 自动识别Orin/Thor | 监控服务从本机设备树识别，TTO自动选对应配置；未知明确显示 | 已部署服务声明与实际设备证据对应 |
| 保留CURVE | 正常CURVE使用成功PWM；不依赖AUTO专属gain | 实际控制温度来源有效、完整使用过程可观察 |
| 使用固定模型 | 输入、平台、scope与冻结模型匹配；降级原因可查 | 新模型的真实时间留出效果与旁路表现 |

探测成功与建模条件分开验收。即使控制温度暂时无效，也应交付能够记录、诊断并解释阻塞的软件。

## 2 工作范围与停止边界

后续离线实施范围为 `/Users/massif/Tianshan-thermal-observer` 和 `/Users/massif/rm01OrinStatus` 中必要的生产实现、回归、打包及说明。先分别保存工作树、源码和现有包身份；保留未提交工作，不reset、clean、覆盖旧交付或回退重建。

| 项目 | 负责的改动 |
| --- | --- |
| rm01OrinStatus | 设备树识别、Thor GPU读取、原子样本、平台/GPU接口、实际能力与安装身份诊断 |
| TTO | 新旧输入识别、数值及独立新鲜度、CURVE资格、有限特征配置、模型匹配、历史回放与报告、Conda升级验证 |
| TianshanOS | 只读源码与保存证据作参考；本轮不改固件、TJ绑定、曲线、增益或保护 |

保留现有只读双路输入、成功PWM、Ridge、15/45/90秒预测、因果特征、时间隔离、三层共同评分集合、test-used、固定模型和资源上限。TTO现有网络与训练依赖锁保持；新增NVML依赖只属于监控服务。

离线实施不连接真实设备，不运行doctor --live或真实collect/shadow，不部署、重启、调风扇、改变源采样频率、启动实机负载或使用CUDA。不提交、推送或创建PR。协议测试只访问测试创建的loopback；信号只发给自己的测试进程。

发现独立问题，记录证据、影响和归属，继续可独立完成的范围内工作。无实机数据或主板来源尚无效，不阻止离线软件交付。代码、离线回归、候选包和报告交回后停止。

## 3 起点与现场阻塞

TTO审查起点为 `97546ba3b403c02d1b9f81aa9fa50276355a4fd3`、软件0.1.2；原wheel和Conda包身份见现有交付回执。监控服务当前基础包为1.0.1；实施前重新核对实际工作树，不把历史提交当新候选。

保存的现场run为 `run-2026-10-12T113943.639076_0000-7113c960`，北京时19:39:43至19:43:00，约196.5秒。8个文件与[原SHA清单](../../evidence/device-install-20261012/collection-sha256.json)一致。628条记录包含196条计算模块数据、194条fan状态和40条temp状态；保存38个起点。

| 已确认问题 | 本轮处理 |
| --- | --- |
| Thor没有GPU利用率输入 | 监控服务增加NVML读取；TTO消费新合同。旧run不得回填另一时刻探测的0% |
| 两条Thor rail和两组温度被硬编码遗漏 | 按真实名字与单位提取，不做Orin别名、不拆分或求总功耗 |
| fan全部curve，旧资格只接受auto | 增加独立CURVE资格，保留旧normal_auto含义 |
| 40份temp全部valid=false、active_source=default、timestamp_ms=0 | 明确阻塞原因，保留资格；不以改mode或温度接近来通过 |
| 新旧合同、模型与配置可能混用 | 明确版本、配置升级和历史回放分派 |
| 报告把收到TJ误当建模准备好 | 分别报告连接、输入覆盖、控制资格、过程完整性及模型证据 |

temp中虽然配置了 `preferred_source=variable` 和 `bound_variable=agx_info.temperature.tj`，实际来源仍未确认有效。这不足以断定绑定错误或风扇没有用温度；需后续核对来源更新链、状态API和已部署固件身份。该项属于单独现场核对，不并入本轮主板修复。

旧候选在这次N305观察中的RSS/CPU统计仅作对照，不证明新候选资源预算通过。本轮短记录没有任务起止与完整回落，不能用于模型收益结论。

## 4 两项目共同冻结的数据合同

唯一共同接口合同版本为 `TTO-PLATFORM-CURVE-v2.0`。以下规则在两份方案中保持逐字一致，作为后续实施和交叉测试的共同依据；用户现已授权分仓本地实施：WS 会话只负责 rm01OrinStatus，TTO 会话只负责 TTO；接口及候选仍须按证据验收。后续必要变更必须同步两份方案及 fixture，不能分别改名或改变时间含义。

新增合同采取加法扩展；既有 `telemetry_meta.schema_version=1`、`stream_id`、`sample_seq`、`time_basis=collector_receive` 和响应时刻的顶层 timestamp 语义保持不变。新增版本号不重定义既有 schema1。

| 字段 | 含义、类型和约束 |
| --- | --- |
| `platform.schema_version` | JSON 整数 1；与 telemetry_meta 和 gpu 的版本分开，bool 或 1.0 不能冒充整数版本 |
| `platform.family` | `jetson_orin`、`jetson_thor` 或 `unknown` |
| `platform.soc` | Orin 为 `tegra234`，Thor 为 `tegra264`，unknown 为 null；family/soc 必须一致 |
| `platform.identification_source` | 已确认时为 `device_tree_compatible`，unknown 为 null；不能无证据声明识别成功 |
| `platform.compatible` | 实际读取的 NUL 分隔 token 列表，用于追溯；在生命周期内封存，不从 model/hostname 生成 |
| `platform.gpu_backend` | 本生命周期选定的策略：Orin 为 `tegrastats`，Thor 为 `nvml`，未知为 `unavailable`；缺依赖和临时故障不改此身份 |
| `gpu.schema_version` | 新增 GPU 合同的 JSON 整数版本，首版为 1；不能用 gpu 对象是否存在来区分新旧合同 |
| `gpu.utilization_pct` | valid 时为有限 JSON 数字，0 至 100，允许整数或小数；其他状态为 null。bool、字符串、NaN、Infinity 和 MHz 不合法 |
| `gpu.source` | valid/stale 时为该结果来源，error 时为失败的选定后端，均为 `tegrastats` 或 `nvml`；unavailable 时为 `unavailable` |
| `gpu.status` | 封存时的 `valid`、`unavailable`、`error` 或 `stale`；关联字段组合见下表，重发时不修改 |
| `gpu.sampled_at_utc` | valid/stale 时为成功读取的 ISO8601 UTC 字符串（Z 或 +00:00）；Orin 以同一源行接收近似起算，NVML 以查询成功返回完成起算。error/unavailable 为 null，失败尝试时间另记诊断 |
| `gpu.age_at_telemetry_receive_ms` | valid/stale 时为成功结果相对该源行接收时刻的年龄，用采集端同一单调时钟计算，为有限非负数字；error/unavailable 为 null |
| `gpu.sample_interval_ms` | 选定后端的实际生效读取调度周期，正整数毫秒；Orin 等于源周期，Thor 独立。它不是成功读数之间的实测间隔，也不是 NVML 硬件统计窗口；无选定后端为 null |
| `gpu.freshness_timeout_ms` | 选定后端的正整数毫秒超时，固定为 `max(5000, 3 × gpu.sample_interval_ms)`；无选定后端为 null |
| `gpu.device_uuid` | NVML 已选定设备的稳定 UUID，未选定或 tegrastats 路径为 null；选定后失败仍保留，不换设备。null 到首个 UUID 是首次确认，不是平台切换 |
| `telemetry_meta.source_sample_interval_ms` | 新增正整数毫秒字段，来自实际启动 tegrastats 的归一化 parser.interval；schema_version 仍为 1，不能用 GPU 周期或 timeout 推算 |

选定后端暂不可用时，GPU 周期和超时仍记录本生命周期已生效的调度设置，不代表读取已成功；实际尝试/成功间隔、耗时和能力原因记录在诊断中。未知平台没有选定 GPU 后端，其 GPU 周期和超时为 null，源周期仍按实际 tegrastats 命令发布。功耗继续为整数 current/average、unit=mW，温度继续为原名称对应的数字，不新增 rail 合计或别名。

**新旧合同判别与旧字段**

1. 任一 platform 字段、gpu.schema_version 或统一 GPU 字段出现，即进入新合同检查；缺标志、类型错误、未知版本和缺必需字段都报告合同错误，不能转入旧路径掩盖问题。统一 GPU 字段指上表 gpu 下除 schema_version 外的字段，包括 device_uuid；platform=null 或错误类型也不是字段缺失。已知 family/soc/backend 必须符合上表，valid/stale/error 的 gpu.source 必须匹配选定后端。
2. 只有 platform 缺失、gpu.schema_version 缺失且没有任何统一 GPU 字段的明确旧结构，才允许 legacy_v1 兼容。旧 gpu={} 或 gpu 缺失表示 GPU 缺失；旧 gr3d_freq 的合法 0% 仍有效，平台保持未确认。不能因旧字段形似 Orin 就确认硬件。
3. 既有 gpu.gr3d_freq 仍表示真实 tegrastats token 的利用率百分比，不改成 MHz，不从 NVML 值生成。统一来源为 tegrastats 且旧百分比有效时，两字段必须一致；不同来源不强求数值相等。Thor 若实际出现旧 token，可以保留原始解析结果，统一 GPU 仍按选定 NVML 策略读取，不增加 fallback 链。
4. 新 GPU 的 error/stale/unavailable 或非法结构不能回退到旧字段。普通 GPU 合同/能力问题撤下 GPU 值并记录原因，保留其他有效输入；样本身份冲突则按既有隔离和断段规则处理。

**GPU 状态与恢复规则**

| 情形 | status / source | utilization、时间与年龄 |
| --- | --- | --- |
| 最近符合因果条件的成功结果，年龄小于 timeout，含合法 0% | valid / 结果后端 | utilization 为真实数字；成功 UTC 和非负年龄均必需 |
| 依赖缺失、指标不支持、Orin token 缺失、未知平台、尚无首个结果，或有界历史中无符合 t 的结果 | unavailable / unavailable | utilization、sampled_at_utc、age 全部为 null；诊断记录具体原因 |
| 初始化、worker 启动或读取失败；选定后端的异常结果是 t 前最近结果 | error / 失败后端 | utilization、sampled_at_utc、age 全部为 null；不得继续提供前次成功值或刷新其时间 |
| t 前最近结果曾成功，但其年龄已达到或超过 timeout，且没有更晚的错误结果 | stale / 成功后端 | utilization 为 null；保留那次成功 UTC 和真实年龄以便追溯 |

成功、错误和能力结果均有内部完成单调时刻与生命周期标识。按完成时刻选择结果时不得越过最近错误重新挑选旧成功值。error/unavailable/stale 只有在新的成功 GPU 结果进入后续新的源样本时才恢复为 valid；不会改写已封存样本。不可用原因和 worker 清理状态通过启动、运行和退出诊断表达，不把实时诊断写进已封存的 gpu 对象。

**因果合并、身份与独立新鲜度**

Thor 源完整行接收时先取得同一生命周期且完成时间不晚于 t 的 GPU 结果副本，或使用有界历史按 t 选择最近结果，再解析和原子提交。成功、错误和能力结果都参与选择；只有 latest 单槽、解析后再过滤不满足要求。例如 A 在 9.9 秒完成，源行 10.0 秒接收，B 在 10.1 秒覆盖 A 后才提交：本帧不能使用 B，有符合条件的 A 时必须能取到 A；历史耗尽则诚实记录 unavailable，不能把负年龄截为 0。Orin 从同一源行解析 GPU 百分比，不新增异步 GPU 缓存；以该行 t/UTC 近似起算。GPU 查询不在 parser 数据锁、HTTP 或 WS 路径执行，结果选择及复制只持短锁，有界历史及容量写入实现说明和测试。

每个 stream_id/sample_seq 封存全部测量字段、platform、gpu 和 source_sample_interval_ms。只有外层 sample_age_ms 和响应 timestamp 按原合同更新。NVML 单独完成读取不产生主样本或递增 seq；相同数值的新有效源行仍产生新 seq。停止/重启创建新生命周期和 stream，旧 GPU/源线程晚到的结果不得发布、进入新缓存或修改新会话资源。

TTO 在重复样本返回之前，将 platform 全对象和 source_sample_interval_ms 纳入不可变内容校验，gpu 全对象继续纳入指纹。同 key 变化是 identity_conflict；同一 stream 跨 seq 的 platform、源周期或 GPU 调度周期/超时设置变化是生命周期合同违例，记录事件、断段并停止不匹配模型，保留原始证据。GPU 状态/读数可在新 seq 合法变化，设置不能随故障改变。不能把这些违例降格为普通 duplicate 或 GPU 缺失。

TTO 首次接收时以 gpu.age_at_telemetry_receive_ms + telemetry_meta.sample_age_ms 作为 GPU 年龄下界，之后推进 N305 单调时间；重复样本沿用源年龄单调下界锚点及既有 max 推进规则，不能倒退或重复加本地经过时间。它不包含未测网络在途时间，不能跨机器减 UTC。年龄达到 timeout 即不再可用；即使封存 status=valid，消费者也必须计算接收/使用时的有效状态，不回写原文。GPU 单独过期撤下 gpu_busy 及依赖它的模型输出，不使新鲜 TJ 自动失效。Orin 的年龄以源行接收近似起算，NVML 的读取完成时间也不是硬件测量的精确时刻或统计窗口。

新服务的源周期来自最终 tegrastats 命令。TTO 在输入配置记录该值及来源，已有人工 source_sample_interval_ms 只用于明确旧合同；新服务与非空人工值冲突时报告配置冲突，不静默覆盖。旧合同缺周期且无可信人工配置时保持未知，不反推或授予需要已知周期的正式数据集/模型资格。源周期和 GPU 周期分别保存，不增加特征列。

**生命周期协作与接口范围**

NVML 会话由一个生命周期内的 GPU 读取组件拥有，初始化/查询在其唯一 worker 中执行，延迟导入可选绑定，成功初始化才由该 owner 配对释放。停止请求唤醒周期等待；初始化、查询和释放不占 parser 数据锁，join 时不能持有 worker 发布/退出所需的锁。信号只记录退出意图，正常控制流执行清理。一个组件清理抛错后仍尝试其余组件，保留原始启动错误和各清理错误；shutdown 抛错记录 cleanup_error，保留初始化归属，只有确认没有执行中调用后才由原 owner 重试释放。未完成资源不虚报成功。

GPU worker 的退出等待预算为 2 秒；它只限制调用方等待，不会取消原生 NVML 调用。超时记录 cleanup_pending，不跨线程释放仍在使用的 NVML 会话；旧 worker 未退出或旧会话未释放时不启动第二个 GPU worker。其他组件照常清理；若随后重新开始非 GPU 采集，GPU 报 error 并诊断 cleanup_pending/cleanup_error，不自动重试创建 worker。旧 owner 最终释放时不能操作新生命周期。目标驱动上出现此限制则阻止候选发布并返回审查，不临时引入服务进程或复杂容错架构。

| 入口 | 本轮输出范围和无首帧行为 |
| --- | --- |
| /api/status 与 tegrastats_update | 完整有效源样本携带封存的 platform、gpu 和 telemetry_meta；同 seq 封存内容一致，响应 timestamp 和外层年龄可不同 |
| /api/cpu、/api/memory、/api/temperature、/api/power | 保留当前字段投影和返回码，既有 telemetry_meta 加源周期；不自动扩展为完整 GPU/平台接口 |
| /api/health | 保留服务存活及既有 telemetry_meta 含义，不能把 healthy 当作 GPU 可用或包身份验证；可加独立 package_version、进程身份和 capabilities 诊断；诊断不进入封存测量对象，不查询 NVML |
| 尚无有效源行 | get_current_status 仍为空、主数据 API 仍返回 503、seq=0/fresh=false，不发送主样本；先完成平台识别或 GPU 读取也不能造首帧 |

旧主板客户端兼容验收限定为既有有效 TJ 和报文接收行为；旧解析器不理解新 GPU 可用性，缺字段后的零初始化值不能称为 Thor 实测 0%。分别验证最终 Socket.IO 包封装、字节数和现有 4 KB/8 KB 接收/分片边界，保留正常报文可读性及已知越界行为证据；不能以 Python JSON 可解析或旧候选大小代替新报文验证。本轮不改天山 OS，也不跨会话修改对方生产代码。

**对应本次八项审查的共同验收矩阵**

| 编号 | 必须覆盖的交叉用例 | 通过标准 |
| --- | --- | --- |
| T1 新旧判别 | 旧 gpu={}、旧 gr3d_freq=0；新版本 1、bool/float 版本、未知版本、缺字段；新错误与旧合法字段并存 | 合法旧 0 保留，新非法/失败不走旧 fallback；有效 TJ 不被普通 GPU 问题撤下 |
| T2 平台身份 | 同 key 仅 platform 变化；同 stream 新 seq 平台/后端/源周期/GPU 周期及超时设置变化；新 stream 正常切换 | 去重前发现冲突并断段；状态恢复不误判为身份切换，不匹配模型停止；raw 不改写 |
| T3 合并顺序 | 9.9/10.0/10.1 覆盖反例、晚到、历史耗尽、错误覆盖旧成功、缓存重发、相同数值新输入 | 无未来结果和负年龄修正；有界选择正确；同 seq 全对象封存，GPU 单独更新不生主样本 |
| T4 生命周期 | CLI/server/parser/worker 实际路径：信号到达初始化/读取/关闭阶段、线程构造/启动失败、清理/shutdown 抛错及原 owner 重试、重复 stop、重启旧回调、查询超时后最终返回 | 保留信号修复和非 GPU 采集；其余清理执行、启动原错保留、成功 init/shutdown 配对；pending/error 诚实报告、无第二 worker/跨代污染 |
| T5 状态类型与年龄 | 0/非零/null、bool/字符串/越界/NaN/Infinity，四状态及恢复；独立过期、阈值相等、重复年龄推进、UTC 跳变 | 状态组合符合表格；失败不刷新旧值；封存 valid 可在消费者变为过期，TJ 保持独立有效 |
| T6 周期贯通 | CLI 的 1000/1000.0/1 与环境优先级、preview、parser.interval、进程替身命令、wire 字段、TTO 配置；旧缺周期与配置冲突 | 单位始终毫秒，1 不变 1000；实际命令与源周期一致，GPU 周期独立，未知/冲突不猜测 |
| T7 接口与客户端 | 首帧前 GPU 已就绪、HTTP/WS 并发/慢发送、分类 API/health、Orin/Thor 最大代表性报文、4 KB/8 KB 封装与分片、旧 TJ 解析 | 无首帧造数；只比较封存字段一致性；TJ 合同保持，大小和边界有新候选证据，不宣称旧客户端已支持新 GPU |
| T8 包与发布身份 | 服务非 editable wheel；Orin 无 NVML 依赖、Thor 可选绑定替身；版本一致、有效 ExecStart/解释器、旧 override/旧 PID、依赖及源码 SHA；TTO 消费候选 fixture | 干净包验证不依赖源码目录；安装/存活不冒充生效；发布/回退路径及证据完整，实际设备操作另行授权 |

共同矩阵为两会话必须实现的交叉验收；一端的通过记录不能替代另一端结果。目标 NVML 的 Python/绑定/驱动匹配、负载响应和原生调用退出行为仍需独立证据。

**分仓执行与交接**

WS 会话拥有 rm01OrinStatus 的唯一写入权，负责本仓代码/测试/服务依赖/候选/说明/证据；TTO 会话只拥有 TTO 的代码、测试、配置升级、候选和证据。此前跨仓改动作为交接起点保留、核对并接续，不回退重做，不同时写相同仓库。两边不替对方构建或宣称验收通过。

最终稿第4节是本次新增接口的唯一权威，前两份方案共同段必须与之逐字一致；若需调整，先说明证据、同步三份方案和同版fixture再继续。服务提供 Orin/Thor/unknown、错误/过期/旧格式 fixture、源码/包身份及 T1–T8 producer 结果；TTO 独立验证 consumer、Engine/Journal及原计划模型/报告链路。固定fixture目录及SHA后消费，不能在对方正在改写的目录构建交付包。各自交付后分别停止，交独立复审；不连接设备、不部署、不提交/推送/创建PR。

## 5 TTO输入与GPU新鲜度

TTO保留每份原始对象；新增解析使用一个有限、明确的profile定义。配置中的orin节名和TTO_ORIN_URL等兼容名称继续保留，它们不表示远端一定是Orin。

| 字段组 | Orin | Thor |
| --- | --- | --- |
| 目标 | temperature.tj | temperature.tj |
| 可选温度 | cpu、gpu、soc0、soc1、soc2 | cpu、gpu、soc012、soc345 |
| CPU聚合 | 有效核usage/freq及报告核数 | 保留同一计算定义 |
| GPU | 统一合同优先；合格legacy兼容 | 统一NVML合同 |
| power current rail | vdd_gpu_soc、vdd_cpu_cv、vin_sys_5v0 | vdd_gpu、vdd_cpu_soc_mss、vin_sys_5v0 |

current只有unit=mW且数值有效才除1000转W；average不替代current。真实分组温度不拆分，rail不相加。未知平台保留原始数据和有效TJ，基线可记录；不猜已知profile、不启用已知平台模型。

新合同Quality指纹包括封存platform、统一GPU及原有测量字段。外层可增长年龄和发送时刻不作为数值冲突。相同身份改变平台须隔离原段，质量结果沿R3b调用链传递；新身份的关键合同变化则断段、清历史并停用不匹配模型。GPU临时不可用不改变平台身份，不断开有效TJ。

GPU接收时年龄下界为 `age_at_telemetry_receive_ms + telemetry_meta.sample_age_ms`。之后仅增加N305单调经过时间。重复seq使用既有下界推进与重报下界的最大值，不返老还童、不重复加本地时间、不生成新起点；UTC跳变不参与GPU有效性。

例如基准年龄4500ms、外层年龄1000ms、timeout5000ms，GPU已经不可用，即使源封存status=valid、TJ仍fresh。状态展示必须分开“来源当时状态”和“观察器当前有效性”。

每个GPU特征样本携带当时有效性、年龄及有效到期的本地单调时刻。当前值在该起点必须有效。30/120秒均值沿用因果左侧持有，但每段持有在该读数到期处截断；整个窗口不能由有效历史覆盖时，均值为缺失，不补0、不跨缺口续值。历史当时有效的观测仍保留，恢复后的新读数不能回填旧缺口。

GPU过期只撤下gpu_busy组和选择了该组的模型输出。未选择GPU的M1、M0及有效TJ基线按各自条件继续。该规则由Quality/Engine/Features共用，报告不复制另一套判定。

## 6 CURVE控制资格与诊断

新合同分别记录实际control_scope、control_eligible及逐项不成立原因。normal_auto仍只表示合格AUTO，不扩成“所有自动控制”。

AUTO和CURVE共同要求：fan/temp返回新鲜、风扇启用、无报告故障/保护/失温、成功duty有效、温度有效且非人工测试、实际来源与绑定可信。来源条件沿用已接受的agx或可信variable绑定；配置的preferred_source不能替代active_source。保留原新鲜度门槛，不因本轮现场无效温度放宽。

真实duty=0在duty_valid=true且其他条件成立时仍有效。target_duty、RPM、fan温度与TJ接近都不能替代成功输出或来源证据。

| scope | 模型控制必需输入 | AUTO诊断 |
| --- | --- | --- |
| auto | duty当前、30/120秒均值、30秒变化、gain | 保留原有语义和资格 |
| curve | duty当前、30/120秒均值、30秒变化 | gain、auto_state、自适应预测等只保留原始追溯，不当CURVE有效预测 |
| manual/off/unknown或异常 | 保留原始记录，撤下正常模型/评分资格 | 不冒充支持范围 |

mode、来源绑定、人工温度、故障/保护或资格变化均按已有观测边界断段；历史重新预热，待评分目标不得穿过该边界。不增加主板写操作来制造资格。

firmware_45s_diagnostic、AUTO控制温度/guard温度及自适应状态比较明确限定AUTO。CURVE下API即使返回这些字段，也不得把旧值当当前固件预测或可信控制温度。报告区分“不适用”与“缺失”，真实原文不删。

## 7 有限特征与profile生命周期

固定四种feature_profile_id，不使用全平台列并集或插件注册框架。

| feature_profile_id | TJ必需列 | 控制必需列 | 可选列 | 全部候选列 |
| --- | --- | --- | --- | --- |
| orin_auto_v2 | 13 | 5 | 36 | 54 |
| orin_curve_v2 | 13 | 4 | 36 | 53 |
| thor_auto_v2 | 13 | 5 | 33 | 51 |
| thor_curve_v2 | 13 | 4 | 33 | 50 |

列顺序、字段组、单位和变换在代码中以一个静态定义为权威，生产与离线共用，并对四种列数断言。可选组仍仅按训练区95%可用率及非恒定性选择；验证/测试不决定字段。

input-profile.json在首次确认有效平台合同后创建一次，不覆盖；只描述该run首次确认的平台、GPU后端、源周期证据、单位、接口版本和识别原始引用，**不把可变化的control_scope固定在这个文件里**。GPU设备UUID以原始样本/诊断事件追溯；首次从null变为已确认不算平台切换，两个已确认UUID不同则按设备变化断段，留下mixed_profiles，不混入同一模型历史。

每个段和起点另外保存feature_schema、feature_profile_id、control_scope及input_contract_sha256。input_contract摘要只含稳定输入含义，不含不断变化的GPU读数、临时错误或首次设备诊断补全。平台/schema/backend/已确认周期合同变化写事件，保留首次profile；缺平台身份或所选模型必需的输入合同身份时模型输出暂停。没有选用GPU组的模型不因GPU周期暂未知而被撤下；GPU从不可用恢复仍按原预热和窗口规则处理。

unknown预热期间不借用已知平台历史。首次确认或合同变化清历史重新预热；AUTO↔CURVE同样断段。一次run发现多个不兼容的已知平台合同或AUTO/CURVE配置后，永久标记mixed_profiles，即使最后恢复原配置也不消除。

manual/off等无资格片段仍进入历史计划量和原因统计，不伪装成独立实验。首次unknown的无资格前导段也不静默删除；它不被自动改标为后来识别到的平台。

Journal负责profile文件/事件的预算、索引和SHA；记录合同要求有profile而文件被移走时报告缺证据。整轮未确认平台则报告platform_unconfirmed，不把未应生成的profile称为丢失。落盘失败不得继续发出无法追溯的模型输出。

## 8 新旧记录、配置、模型与评估

### 8.1 记录合同分派

新候选创建record_schema=2、input_schema=2、feature_schema=2、model_schema=2的run，处理合同为TTO-PLATFORM-CURVE-v2.0；源telemetry_meta仍为1，platform/GPU对象各为1。配置文件格式首轮保留schema1，不把这些版本混为一个开关。

manifest在run开始时记录处理合同，首次平台证据另存profile与事件，不改旧manifest。明确声明既有schema1记录合同的run，report/replay按冻结的旧Engine/Features规则读取；不得套用新增平台或scope边界改变旧段号、起点ID、支持引用或标签关联。声明schema2却缺必需字段、版本组合冲突或未知记录版本时，保留诊断但拒绝评分，不能因为字段缺失退回schema1。若存在更早的缺版本历史记录，只能根据已核实的旧记录合同明确列入兼容规则，不从文件夹或数值猜版本。

新合同诊断旧输入时写独立新目录，标diagnostic_replay，不能替代旧实际预测/评分的关联依据。旧observations、predictions、scores、events、manifest及操作记录均不改写。

R3b继续按run、segment、预测ID、时距、方法、模型身份和原始引用关联；既有隔离段退出有效误差，恢复段保留，历史分母不缩小。日志完整性与评价资格分开。更换当前模型文件不能影响已有旁路统计。

### 8.2 持久化配置升级

Conda安装器保留旧local.json、模型和数据，不提高轮询频率、不改Conda base。旧features.power_current_rails继续按旧配置合同识别，标明为兼容冻结字段；schema2的实际rail名单由平台profile决定，不能让用户以为改这个旧列表就能换rail。

不能直接删除默认键导致闭合merge拒绝旧配置，也不能更改冻结features默认值后让所有旧manifest校验失败。确需转换时按版本在内存中转换，保留原文件，并测试旧配置加载、旧报告及升级安装。

### 8.3 建库与冻结模型

新dataset/model为schema2，保存平台、input_contract摘要、feature_profile_id、control_scope、单位、源周期及选择的列组。train、evaluate、shadow均在实际调用入口核对；加载器同时验证schema、必需列前缀、可选完整组、维度、缩放及三个时距系数，不能只放宽列名白名单。

正式schema2数据集只允许一种已确认的平台输入合同和一种AUTO/CURVE配置；整轮从未确认平台或mixed_profiles的run明确拒绝正式冻结。初始unknown前导起点保留原身份，只参与计划量和诊断，不进入已知平台的正式训练/共同评分；不能改标为后来平台。build_dataset与load/check/train入口分别核对，不能只信首份profile或只过滤后段来通过。无资格起点保留用于覆盖和原因统计，不进入训练成绩。

M0/M1依旧在共同可训练/验证起点拟合；三个时距、Ridge权重、训练侧标准化、有限lambda及验证45秒选择不变。评估保留B0/B1、B0/B1/M0、B0/B1/M0/M1三层同起点同标签集合。缺GPU、M1降级不抹去M0证据，不跨集合比较MAE。

schema1模型保留加载、历史报告和旧冻结数据集离线评估能力；不补写平台或自动升级。schema2在线run不能调用缺新身份的schema1模型，包括新Orin AUTO轮次；此限制是为了避免把未声明硬件范围的旧模型冒充已匹配模型。旧0.1.2包和资料继续可恢复，不静默覆盖。

只有显式提供且匹配的新冻结模型才能在新run输出M0/M1。源周期证据仍按原合同登记，GPU周期不能替代。输入不可用或模型不匹配时继续有限采集与明确标记的基线，不在线训练、不自动换模型、不使用模拟模型连接真机。

## 9 面向测试者的报告

JSON、Markdown、HTML使用同一结果对象，并给出实际下一步。至少分开显示：

1. 观察器主机身份、来源及资源；远端SoC身份与声明来源另列。
2. 两路连接、有效新TJ与各输入字段覆盖；GPU来源状态、当前新鲜度与缺项原因。
3. 实际mode、control_scope、正常AUTO/CURVE计数；控制温度有效性、配置绑定与实际来源分别显示。
4. profile/模型匹配、预热、输出、降级及未来标签状态。
5. 历史已发、历史评分、质量排除、当前有效；覆盖分子和历史分母。
6. 完整过程、分组、部署身份与模型效果证据是否齐备。

本轮旧诊断run应提示：已收到196份新TJ；记录为CURVE；控制温度状态无效/实际来源未确认；Thor部分输入未进入旧特征；没有真实模型效果结论。不能仅因收到新TJ就建议直接训练。

移除固定“当前主机不是N305”文字，按有来源的主机信息显示；无证据则写未确认。平台声明不替代wheel/固件部署身份。任务开始和结束沿用关联人工记录，保留原文、来源、近似事件时刻及写入时刻；任务结束不停止回落采集，不增加常驻仪表盘或打点CLI。

## 10 实施顺序和每步交付

| 步骤 | 工作 | 可验收产物 |
| --- | --- | --- |
| S0 | 保存两工作树/包身份，核对锁和测试副作用；补新合同样本 | 起点清单、Orin/Thor/unknown与错误fixture |
| S1（WS会话） | 监控服务平台识别和GPU生命周期；封存并发布同一原子样本 | 生产parser/get_snapshot/HTTP/WS路径回归、依赖锁及接口fixture |
| S2（TTO会话） | TTO新旧配置/记录分派、有限profile、数值与GPU时间处理 | Quality/Engine/Journal实时与回放一致；旧记录不退化 |
| S3（TTO会话） | CURVE资格、模型匹配、建库训练评估与报告 | 四配置完整生产链路、正常及缺项/冲突/变化反例 |
| S4（各自仓库） | 各自离线回归、候选wheel、干净安装与相关旧配置升级 | 实际导入路径、包/源码SHA、安装验证与最小证据 |
| S5 | 独立复审 | 本轮到此交回；不自行现场发布 |

候选版本使用与旧包区别的版本：TTO0.2.0、tegrastats-api1.1.1；实施时如已有同名候选，选择新的未使用版本并记录，不能复用旧包身份。两边源码、wheel、实际导入文件均独立核验。

常规实现选择在以上合同内自行推进，不逐项等待用户确认。接口定义确需变更时先说明证据与影响，同步两项目；不能只让一端改字段来通过测试。

## 11 离线验收与候选安装

第4节共同 T1–T8 必须按分工分别提供 producer/consumer 证据。原监控服务110项和原TTO88项覆盖保留；正确合同变化需要更新测试时，保留旧失败与修改理由。监控服务先核对tests/offline隔离和副作用，再跑原覆盖及必要新增测试，不盲跑可能启动设备/模型服务的其他目录。

| 验收项 | 必须通过的断言 |
| --- | --- |
| 自动识别 | 设备树Orin/Thor精确匹配；model/hostname/端口不能替代；unknown不猜 |
| 新旧GPU | legacy对象存在仍兼容；0%有效；新版缺标志/字段或报错不回退；同源冲突明确 |
| 原子提交 | 相同seq只改platform或GPU元数据触发冲突；正常重发不新增起点；迟到GPU不回写 |
| 独立时间 | 4500+1000>=5000的接收过期反例；UTC跳变、重复下界、静默、恢复后窗口缺口 |
| Thor数值 | 实测rail与分组温度一一转换；mW/W、current/average无混用或假alias |
| CURVE正向 | 真正有效temp来源下支持CURVE、duty=0、target不同、无gain；正常预热及评分 |
| CURVE反向 | 本轮40条无效temp保持阻塞；manual/off、故障/保护/失温及来源变化撤资格 |
| AUTO诊断 | CURVE不输出AUTO固件预测/自适应状态为有效诊断；AUTO原合同保持 |
| profile变化 | unknown→known重新预热；AUTO→CURVE→AUTO与平台A→B→A留下mixed标记 |
| 冻结与模型 | 混平台/scope拒绝；build/load/train/evaluate/shadow均校验；三层公平评分不退化 |
| 历史报告 | schema1段号/引用保持；44个M1起点/102条评分对照；冲突510排除、恢复306有效 |
| 历史证据 | 换模型、缺日志、无评分、降级和评分身份原回归保留；所有原日志SHA不变 |
| 协议与资源 | R4目标请求数0、正常WS/polling、心跳/重连与ESP32 GET；原预算不提高 |
| 安装升级 | 新wheel非editable；导入文件对应源码；旧local.json/模型/记录不改；Conda base不变 |

必须走生产Engine/Journal、正式report命令及split→train→evaluate链路，不能只测辅助过滤函数。合成数据与模型始终标模拟，不冒充实机或独立实验。

TTO在Python3.10兼容、依赖完整的隔离环境验证。两项目分别从候选wheel在干净目录非editable安装；检查实际import路径与文件内容。TTO实际Conda安装/旧配置升级使用新临时前缀和准备好的离线依赖，不在用户默认目录安装，不连接设备。RM实际目标Python/驱动与资源只能由后续现场证据验收，离线包测试不得代替。

## 12 交付物与完成条件

各会话只制作各自仓库的候选、增量补丁、源码/测试、依赖锁、中文报告及最小证据包；服务另提供同合同 fixture/SHA，TTO消费者验收单独登记。任何一端不得替另一端宣称完成。下面两端整体完成条件用于交接复审，各自 Goal 以本仓验收和可复核交接满足为终点；对方尚未完成的真实交叉结果明确待验证，不能冒充通过。

交付《TTO Orin Thor CURVE适配实施与验证报告》及最小证据包，附两项目增量patch、必要源码/测试/fixture、失败与成功日志、候选wheel、TTO Conda安装包、依赖锁、SHA清单和可独立重跑入口。更新中文测试者说明与操作卡，让测试者先看数据检查、再看资格及模型。

报告逐项对应R01—R08、S0—S4和上表验收，写清已通过、剩余限制和未执行项。证据包不重复全部历史大包，不含真实凭据或私人任务数据。未知指标保持不可用，不要求“所有字段都非零”或“全部都有模型成绩”才交软件。

离线完成必须同时满足：两端新合同一致、生产路径回归通过、旧配置/历史记录兼容、候选安装身份一致、最小证据与中文交付可用。原现场温度状态尚无效不阻止这一完成条件，但必须继续作为现场资格阻塞呈现。

满足后结论为：**软件适配及离线验证完成，待独立复审；新候选实机验证未执行，真实预测效果待验证。** 不能写真机通过、模型有效或可以降低风扇档位。

## 13 后续现场安排

用户审阅候选后另行确定安装和只读窗口。顺序为：核对并发布监控服务实际环境，再安装TTO候选，确认包/解释器/有效ExecStart及配置身份，运行180秒有界doctor，最后按新run记录正常任务和回落。

接口适配检查与正常CURVE资格验收分别登记。temp仍报告无效时保留数据并列阻塞，不自动换绑定、改mode、重启设备或宣称建模准备完成。GPU负载响应使用用户正常任务观察，不为制造非零启动额外负载。

现有源服务override和真实进程路径需分别核对；API返回新版字段不能单独证明安装包身份。现场记录CPU/RSS、队列丢弃、GPU读取耗时和轮询漏期，不能用旧N305成绩替代新候选。

完成过程采集后再依据现有独立episode和未使用测试要求训练评估。观察器主机、源服务、主板状态、模型效果四类证据分别报告。

## 14 分仓执行方式

按用户本次明确决定使用两个独立 Goal：当前 WS 会话在 rm01OrinStatus 完成 S0/S1及本仓 S4；已有 TTO 实施会话在 TTO 完成 S0/S2/S3及本仓 S4。两边共享第4节唯一合同和冻结fixture，不共享生产代码写入权。已交接的服务改动由 WS 会话审查接续，不回退、不重复创建一套实现。

范围内常规选择自行推进，原回归和共同矩阵完成后交独立复审。协调消息仅用于合同、fixture和进度交接；不因对方未完成就在本仓造值、扩大权限或跨仓修代码。合同确需变更时必须同步三份方案和fixture，并说明原因及影响。

Goal终点只到本仓第12节离线交付；第13节现场安排另行授权。预算耗尽或范围内无法解决的外部阻塞如实交回已完成证据、尝试路径和未完成项，不能据此宣称完成。[Goal官方说明](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)不改变文件、设备或发布权限。

TTO会话采用附带的TTO专用启动文案；WS会话已按用户要求开启服务专用Goal。本文件修订不要求另开第三个实施会话。
