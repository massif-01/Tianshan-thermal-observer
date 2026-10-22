# TTO Orin Thor 与 CURVE 适配执行方案

状态：八项审查已合入唯一最终稿，用户已授权分仓本地实施。日期：2026 年 10 月 12 日。

目标是让 TTO 根据监控服务提供的身份自动适配 Orin 和 Thor，正确使用实际温度、负载、功耗和主板成功 PWM，并支持现场必须保留的 CURVE 控制模式。保留现有两路只读输入、因果特征、离线训练、固定模型旁路和原始证据机制，只修改已确认的输入、资格和报告缺口。

用户已授权两会话分别本地实施：本 TTO 会话只修改 TTO，WS 会话只修改 rm01OrinStatus。新增接口唯一依据为同目录《TTO-Orin-Thor-CURVE最终执行方案-20261012.md》第4节，本共同段同步该最终稿。不连接设备、不部署、不开始真实采集或新热模型项目、不提交/推送；既有模型/run/评分保留，现场操作另行授权。

## 已明确的需求和边界

风扇由 RM-01 独立主板控制，现场 CURVE 模式必须保留。TTO 只观察，不修改风扇模式、PWM、温度绑定、源频率或主板固件。CURVE 必须按真实模式记录，不能为了通过既有 AUTO 条件而改名或切换设备模式。

平台识别由运行在计算模块上的 RM01OrinStatus 完成，TTO 消费其声明和实际输入能力，不要求用户手选 Orin/Thor，也不在 N305 上猜远端平台。软件自动选择输入合同不等于自动训练、切换模型或证明跨平台预测效果。

任务开始和结束继续使用本轮关联的人工操作记录。保留上报原文、来源、近似事件时间和记录写入时间，任务结束不停止温度回落采集。此次无需新增 CLI 打点命令或后台服务。

## 已确认的问题和保留基线

本地审查基线为提交 `97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。N305 安装 TTO 0.1.2，wheel SHA 为 `bfe55c967c017c45ebe0287a886eb17e30d7e44a0ca7af01d385fd4ad97ab465`。实施前必须重新核对工作区和候选包；不要覆盖已有未提交工作。

| 问题 | 现场及代码证据 | 实际影响 |
| --- | --- | --- |
| GPU 输入 | `quality.numbers` 只读旧 `gpu.gr3d_freq` 百分比；Thor 可通过 NVML 读取 | 本轮 gpu_busy 可用率 0%，不能作为模型有效输入 |
| 功耗 rail | 固定 `vdd_gpu_soc/vdd_cpu_cv/vin_sys_5v0`；实机返回 `vdd_gpu/vdd_cpu_soc_mss/vin_sys_5v0` | 两个真实 rail 已保存，却未进入特征；仅改配置列表不会修复硬编码 |
| 分组温度 | 固定读取 soc0/1/2；Thor 返回 soc012/soc345 | 两个真实测点被遗漏 |
| 控制资格 | `Engine.normal` 要求 mode=auto；全部 194 条 fan 状态为 curve | 38 个预测起点均 normal_auto=false，duty/gain 特征均缺失 |
| 特征合同 | 当前 54 列，全局上限 64；新增两组 rail 和两组温度直接并集将达 66 列 | 不能无条件追加所有平台字段或随意提高限额 |
| 模型与报告 | schema1 无明确平台匹配；报告可以在 AUTO 资格为 0 时建议建模，host_scope 仍写非 N305 | 连接可用不能代表训练或模型验收条件已满足 |

本轮记录为 `run-2026-10-12T113943.639076_0000-7113c960`，2026 年 10 月 12 日北京时间 19:39:43 至 19:43:00，约 196.5 秒。628 条原始记录、196 个 Orin 事件和 38 个预测起点已保存，停止原因 SIGINT，无人工任务起止标记。8 个文件的本地副本与实机 SHA256 一致。

证据在 `evidence/device-install-20261012/`：原始 run、`collection-sha256.json`、`collection-stop.txt`、`thor-checkpoint-20261012/` 报告、`thor-adaptation-audit.json`。这轮是输入适配诊断基线，不是完整任务加温度回落过程，也不是模型精度验收。

本次服务方案审查已确认：Thor 温度/功耗在服务端正确保留，TTO 提取仍硬编码 Orin 名称；quality.accept 当前指纹未包含 platform，同 key 只变平台被当 duplicate。服务原有离线 110 项通过不等于 TTO、新 GPU 或设备通过；下列 T1–T8 为尚待实施的交叉验收。

## 两个项目共同审查的数据接口草案

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

## 修改步骤

### 第一步 自动选择输入和特征配置

使用首个有效源样本中合法且已知的 platform 合同确定输入配置，不要求 GPU 此刻有效。每轮创建一次不可覆盖的 input-profile.json，保存合同修订号、平台/后端、字段含义、实际源周期及其来源、GPU 调度/超时设置和原始引用。先按共同 T1 校验版本与结构，按 T2 在 duplicate 返回前校验完整 platform、GPU 和源周期。不能用 gpu 对象是否存在区分新旧，不能靠用户手选或字段外形猜平台。

未知或非法平台可以保存原始记录和其他有效 TJ，但不能启用已知平台模型。临时 GPU 状态改变不修改 input-profile 的固定平台/后端/周期及超时设置，也不被误报为平台切换。同 key 仅 platform 或源周期变化为身份冲突；同 stream 新 seq 改平台/后端、源周期或 GPU 周期/超时设置为生命周期合同违例，记录、隔离、断段并停止不匹配模型。新 stream 合法切换也需断段和模型匹配，不覆盖已保存 profile。一个 run 含不兼容配置时不能正式冻结；不自动重启或轮转 run 掩盖变化。

只有满足共同合同的明确旧结构才按历史 schema1 回放/诊断，标记 legacy_v1 且平台未确认；旧 gpu={} 为缺失，旧 gr3d_freq=0 为合法百分比。platform 虽缺失但统一 GPU 字段已出现的残缺新结构、非法新版本和缺字段不能退到 legacy。旧数据不自动取得新 Thor/CURVE 模型资格。实际源周期取新服务字段；旧服务仅使用有证据的人工配置，否则未知。新服务字段与非空人工周期冲突必须报告，不能从 freshness_timeout 或 GPU 周期猜源周期。

### 第二步 正确提取 Thor 数值

| 指标 | Orin 配置 | Thor 配置 |
| --- | --- | --- |
| 预测目标 | 实际 `temperature.tj` | 实际 `temperature.tj` |
| 温度可选项 | CPU、GPU、soc0/1/2 的实际可用测点 | CPU、GPU、soc012、soc345 的实际可用测点 |
| GPU 忙碌 | 按 gpu.schema_version 与完整字段判别新合同；明确 legacy_v1 才读旧 gr3d_freq | 新合同中来源 nvml、状态和接收时有效年龄均合法的百分比 |
| 功耗 | VDD_GPU_SOC、VDD_CPU_CV、VIN_SYS_5V0 | VDD_GPU、VDD_CPU_SOC_MSS、VIN_SYS_5V0 |
| 主板输入 | 成功 duty 和实际控制状态 | 成功 duty 和实际控制状态 |

功耗由 mW 除以 1000 转为 W，current 与 average 不互换，rail 不求和。分组温度保持原名和含义，不拆分。GPU 按共同状态表及有限数字规则提取：非 valid、非法结构、负年龄、缺时刻或周期不合法均撤下 gpu_busy 并报告原因，不借旧字段掩盖。来源 tegrastats 的新旧有效百分比必须一致；NVML 与真实旧 token 不同源时不比较数值是否相等。

GPU 使用时年龄等于封存 GPU 年龄加当前源年龄下界；duplicate 复用已有源年龄锚点推进，不二次加本地时间，不用跨主机 UTC。封存 valid 也可能在收到时或之后过期，按 >=timeout 撤下 gpu_busy 及依赖它的模型输出，保留有效 TJ、其他输入和标记正确的基线。新成功结果仅在后续新源样本恢复；不能给旧 seq 补 GPU 或新增预测起点，不能把缺 GPU 的降级计成 M1 成功。保留原身份冲突、倒退、断线和队列缺口机制，并扩展 platform/周期保护。

相关代码集中在 `quality.py` 的 `numbers/accept`、`features.py` 和 `config.py` 的字段合同。当前 `features.power_current_rails` 未实际驱动提取；修改时选择一个真实生效的配置来源，移除或明确旧项的兼容含义，不能保留看似可配置但不生效的项。

### 第三步 定义 CURVE 的真实资格

CURVE 和 AUTO 是不同控制策略。TianshanOS 的 AUTO 使用自适应 gain，CURVE 走曲线加迟滞路径。两者都由主板控制，但不能合并为一个未标记的训练范围。

保留既有正常条件：fan/temp 新鲜、风扇已启用、无故障/保护/失温、成功 duty 有效、温度非手动测试、来源和绑定可信。对 CURVE 新增独立资格，不再因为 mode!=auto 丢掉实际成功 PWM。`target_duty` 和 RPM 仍不能替代成功 duty。

控制历史和目标窗口不得跨 mode、来源绑定、故障、保护或人工温度切换；scope 变化必须断段和重新预热。模型匹配包含实际控制 scope。旧 normal_auto 字段及其含义保留在历史合同中，新增合同用明确的 scope 和资格，不把旧字段悄悄改成“任意自动控制”。

CURVE 的 M1 必需字段拟为成功 duty 当前值、30/120 秒均值和 30 秒变化，去掉 AUTO 专属 gain 要求。gain 可以保留在原始主板诊断中，不能因 API 返回一个默认值就认为它是 CURVE 控制的实际输入。AUTO 的既有 gain 合同保留。共同训练集合与公平比较依照每种 scope 的真实必需字段生成。

### 第四步 固定有限特征配置和模型合同

按平台和控制 scope 明确定义有限配置，而不是把所有平台列做全局并集。拟议列数如下，须在实现中通过断言核对：

| 配置 | TJ 必需列 | 控制必需列 | 可选列 | 全部候选列 |
| --- | --- | --- | --- | --- |
| Orin AUTO | 13 | 5，含 gain | 36 | 54 |
| Orin CURVE | 13 | 4，无 gain | 36 | 53 |
| Thor AUTO | 13 | 5，含 gain | 33 | 51 |
| Thor CURVE | 13 | 4，无 gain | 33 | 50 |

Thor 可选项共 11 组：4 个温度测点、3 个 CPU 聚合项、1 个 GPU 利用率和 3 个功耗 rail；每组保留当前值及 30/120 秒变换。首轮不增加 GPU 频率特征。可选字段仍仅按训练区可用率和非恒定性选择，不读取验证/测试区决定字段。

新特征合同拟升级为 feature_schema=2。run 配置、数据集和模型记录共同接口修订号、平台、具体特征配置、control_scope、单位、源周期及来源；GPU 调度和超时作为输入元数据单独保存，不增加特征列。train/evaluate/shadow 前验证匹配，周期未知或冲突不授予要求已知周期的正式资格。schema、列名、维度和 JSON 模型读取一起调整，不能只放宽 loader；本轮仅实施既有离线软件/模拟回归，不训练真实新模型或连接设备。

正式建模首轮要求同一数据集平台及控制 scope 一致。混合 Orin/Thor 或 AUTO/CURVE 数据集明确拒绝正式冻结，除非后续另有实验设计和授权。M0/M1 的训练、验证及三层评估保留当前公平比较和覆盖率规则。

旧模型可按原合同读取，但不能被自动升级、改标平台或在新 Thor/CURVE 轮次中启用。新模型缺少匹配身份时停止模型输出并继续有界采集和基线。统一的配置选择应供实时和离线使用，避免实现两套不同逻辑。

相关路径包括 `engine.py`、`features.py`、`dataset.py`、`training.py`、`model.py`、`evaluation.py`、`recorded.py` 和 `storage.py`。保持直接 Ridge、训练权重、15/45/90 秒窗口、时间切分和 test-used 登记，不扩到其他模型或在线学习。

### 第五步 报告和历史证据

报告分别呈现连接可用性、有效 TJ、输入字段覆盖、真实控制模式、资格不成立原因、模型输出/降级、未来标签及已保存评分。连接检查成功不自动推荐进入训练；没有足够完整过程、资格或覆盖时给出实际阻塞项。

观察器主机身份和远端 SoC 身份分开记录，移除固定“不是 N305”的错误表述。N305 资源证据只支持该主机；服务声明平台不能代替 firmware/wheel 核验。报告分别呈现接口可用、样本/GPU 有效、选定后端与能力失败、源/GPU 周期及来源、实际安装/进程身份；health 存活不能称为 GPU 正常，旧主板有效 TJ 不能称为已支持统一 GPU。NVML cleanup_pending/cleanup_error、周期冲突和身份冲突给出明确阻塞原因。

保留原始 observations、predictions、scores、manifest 和人工操作记录。新版本回放历史数据只能写入新目录，并注明当前回放版本和合同；不能用新资格重写旧的实际预测或评分，再宣称历史已通过。

本轮缺少 GPU 原始输入，升级后无法回填为当时真实 GPU 读数；本轮很短且缺任务标记，不能补造完整热过程。新候选必须新开 run，与旧记录保持区别。

## 离线验证和实机验收

先检查 `tests/conftest.py` 的离线保护和各脚本副作用，再运行相关测试。实机配置不得传给训练、演示或回归脚本。真实记录的数值提取可以离线回放，但按新合同产生的资格只是新回放诊断，不是旧在线结果。

| 测试层 | 必须覆盖的情况 | 通过标准 |
| --- | --- | --- |
| 输入合同 | 共同 T1/T2/T5：旧空对象/0%、新版本类型/缺字段、四状态、同 key 平台变化及跨 seq 违例 | 判别、字段组合和去重前检查正确；GPU 普通失败独立降级，身份冲突不被掩盖 |
| 因果时间 | 共同 T3/T5：覆盖反例、错误覆盖旧成功、封存 valid 收到时已过期、阈值相等、重复推进、UTC 跳变 | 不用跨机器 UTC、不倒退或双加年龄，同 seq 不生新起点；新 TJ 与过期 GPU 独立 |
| 周期入口与服务生命周期 | 共同 T4/T6，消费服务实际 CLI/进程替身产出的 fixture、清理错误及 pending 状态 | 新源字段来自最终命令、旧配置来源明确；不把 GPU 故障误作平台切换或 TJ 停止 |
| HTTP/WS 与旧客户端边界 | 共同 T7，首帧前、投影/health、缓存重发和最终报文大小/分片 | 只消费完整有效源样本；封存字段一致；旧客户端仅按既有 TJ 合同验收 |
| Thor 提取 | 实测 rail、soc012/soc345、TJ、CPU/GPU 温度 | 原始值到特征一一对应，mW 转 W，无错误 alias |
| CURVE 资格 | 正常曲线、真实 0 duty、target 与 duty 不同、manual/off、故障/保护/失温 | 正常 CURVE 使用成功 duty；不需要 AUTO gain；异常撤资格 |
| 特征和模型 | 四个配置、缺选中可选项、schema1/2、平台或 scope 不匹配 | 列数和顺序符合合同，缺项降级明确，旧模型不能冒充新模型 |
| 数据集和评估 | 平台/scope 混合、控制变化、未来标签、原切分隔离和三层比较 | 正式数据集不混不兼容配置；不改变当前防泄漏规则 |
| 报告 | 旧诊断 run、新 CURVE fixture、未知平台、仅基线、缺日志 | 连接成功与模型准备度分开，保留历史评分和排除理由 |
| 包 | 共同 T8，服务候选 fixture + TTO 新版非 editable wheel、锁定依赖、安装器与实际导入身份 | 两包接口一致，版本/SHA/文件一致；干净安装包验证，设备生效另行授权 |

后续先在离线且非 editable 的干净候选环境消费同版服务 fixture，运行共同 T1–T8 的消费者用例与 TTO 原有回归；服务原 110 项不能代替 TTO 结果。分别保存两包版本、wheel/源码/依赖 SHA 和实际导入路径，版本和运行诊断一致。用户另行批准安装后，先核对服务有效 ExecStart、解释器、override 和切换后的实际 PID/加载身份，再核对 N305 上 TTO 包及原配置/模型/run 备份；安装器不覆盖这些资产，回退恢复旧 wheel/依赖及配置，并按授权重新验证身份。

用户批准后再运行 180 秒只读 doctor，检查有效新 TJ、两路状态、真实 CURVE 资格、GPU 时间合同和独立 rail，同时记录 CPU/RSS、队列丢弃、轮询漏期及服务查询/退出行为。沿用已有预算，不临时提高限额。该时长仅验输入链路，不替代历史预热、15/45/90 秒未来标签、完整过程或模型效果验收。

doctor 通过后，经用户批准开启新一轮有界采集，执行用户正常任务、人工起止标记和温度回落。检查 GPU 利用率随任务变化和参考 NVML 的时间差异；短任务或低占用未必持续显示非零，不能为制造非零额外启动负载。先收集完整过程，再按既有独立 episode 数量要求训练和评估，不以一轮短诊断得出模型收益。

## 两个会话的交接与执行顺序

1. 本轮按用户授权分仓实施；核对唯一最终合同共同段和 T1–T8，TTO 会话不再写 rm01OrinStatus。
2. 服务由 WS 会话完成识别、worker owner、因果封存、异常清理与周期贯通，提供同版新旧/错误/过期 fixture；任何合同调整同步两份方案。
3. 本 TTO 会话基于冻结的同版 fixture 实现去重前身份校验、实时/回放共用的提取与独立年龄、原计划的 CURVE 资格、有限特征配置和报告，不扩大模型范围。
4. 各自完成原回归和共同矩阵、干净候选 wheel、依赖/文件身份、安装及回退说明；旧配置、模型、run 和实际历史评分保留。
5. 用户另行批准后，先切换并核对服务实际进程，再安装和核对 TTO 候选、执行输入 doctor；新 run、任务、回落采集与训练评估沿用原阶段授权，不自动启动。

阻止验收的情况：CURVE 被改名为 AUTO；rail alias/错误单位；新 GPU 非法或失败绕回旧值；缺失补 0；同 key 平台/周期漂移未检出；未来结果或 GPU 恢复回写旧 seq；NVML cleanup_pending/cleanup_error；新旧模型/平台混用；周期未知却宣称正式资格；旧 PID/包身份未切换；原始日志/实际评分改写；离线成绩被当成设备成绩。

## 独立审查要回答的问题

- TTO 是否只消费有证据的远端身份，自动选择是否会掩盖未知平台或缺项？
- CURVE 的资格和必需输入是否反映真实主板控制，而非为通过旧 AUTO 条件改标签？
- GPU 独立年龄与原子样本是否保持因果性，实时与回放是否使用同一逻辑？
- 四个特征配置、模型匹配和历史 schema 兼容是否完整，是否仍在 64 列内？
- 切分、训练、已发预测和未来评分的原有证据合同是否保持？
- 报告能否直接说明“连接成功但尚不能建模”的原因？
- 方案是否与 RM01OrinStatus 接口一致，验证是否覆盖实际安装包和用户批准的设备轮次？

## 参考资料

- 现有 `docs/contracts.md`、`docs/R1-R4-repair-contract.md`、`docs/R3b-report-eligibility.md` 继续作为原行为依据；新合同应明确补充和版本范围，不能把历史规则悄悄替换。
- [NVIDIA Thor GPU Management Tool](https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonThor.html#gpu-management-tool) 与 [nvidia-smi 文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html) 支持 GPU 采集入口和指标语义；不支持本项目模型精度或风扇控制收益结论。

- [NVML 查询接口](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)、[初始化与清理](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlInitializationAndCleanup.html)、[利用率统计窗口](https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlUtilization__t.html)：独立 GPU 年龄、worker 资源归属和有界等待的依据，不证明模型效果。
