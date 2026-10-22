# RM01OrinStatus 自动识别 Orin 和 Thor 执行方案

状态：八项审查已合入唯一最终稿，用户已授权分仓本地实施。日期：2026 年 10 月 12 日。

目标是在同一份 RM01OrinStatus 软件中自动识别 Orin 和 Thor，按实际平台采集 GPU、温度和功耗数据，让 TTO 获得含义明确、时间可追溯的新合同，并保持现有主板客户端的正常 TJ 接收合同。保留现有解析器、HTTP、Socket.IO 和样本身份机制，只修改已确认的适配缺口。

用户现已授权本 WS 会话在现有 rm01OrinStatus 工作树接续本地实施和离线交付，TTO 会话只负责 TTO。新增接口唯一依据为同目录《TTO-Orin-Thor-CURVE最终执行方案-20261012.md》第4节，本共同段同步该最终稿。保留旧证据和已有改动；不连接设备、不安装到Orin、不部署/重启、不改天山OS/风扇、不开始新热模型项目、不提交/推送/创建PR。

## 已明确的需求和边界

风扇由 RM-01 独立主板控制，当前 CURVE 模式必须保留。RM01OrinStatus 只采集和发布计算模块状态，不接管风扇，不修改 PWM、温度绑定、功耗模式、频率、源采样周期或 GPU persistence mode。

平台识别在计算模块本机完成，不靠主机名、IP、用户手选或“GPU 字段为空”猜测。TTO 使用服务提供的平台身份，不在 N305 上识别远端 SoC。Orin 的现有数据合同继续兼容；Thor 使用 NVML 获取 GPU 利用率。温度和功耗保留硬件实际名称，不能为了兼容而伪装成另一平台的传感器或 rail。

未知平台、GPU 不支持某项指标和临时读取失败只影响相关指标的可用性。0% 是合法读数，不能用来填补缺失。不能把读取失败扩大成停止 TJ、CPU、温度和功耗采集，也不能把缺失状态写成正常。

## 现场证据和基线

| 项目 | 已核对的事实 | 对实施的意义 |
| --- | --- | --- |
| Thor 系统 | Jetson Linux R38.4.0，驱动 580.00，`INSTALL_TYPE=openrm` | 不能沿用仅靠 nvgpu 的采集假设 |
| 设备树 | `compatible` 包含 `rm01,rm01-thor`、`nvidia,p3834-0008`、`nvidia,tegra264`；model 为 `RM01-Thor V1.0 CVB` | 可可靠识别 Thor 家族；识别家族不等于证明某个商业模块型号 |
| 原始输入 | 实测帧有 `soc012`、`soc345`、`VDD_GPU`、`VDD_CPU_SOC_MSS`、`VIN_SYS_5V0`，该次帧无 GPU 利用率 token | 解析器不能凭空生成 GPU 百分比 |
| GPU 路径 | `nvidia-smi` 和已有 `pynvml` 均能读取 `NVIDIA Thor` 的 GPU 利用率；当前探测为 0% | 入口可用；尚未验证实际任务中读数随负载变化 |
| 当前解析器 | GPU 只匹配 `GR3D_FREQ (\d+)%`；温度和功耗保留真实名称 | GPU 后端要补充，温度和功耗无需改成 Orin 别名 |
| 已修复部署 | 仓库已有新版，但 systemd override 仍指向旧 venv 包和旧进程 | 本次已按授权更新实际 venv 并重启；后续发布必须核对有效 ExecStart |

实机安装源提交为 `ca690bdfbe5d21a0866fabafa70e79fae3860411`。本地审查仓库提交为 `d53edc444ac76e0aa36fedbfcca0a001f28fef5f`；已核对本地 Python 文件与实机安装源 Python 文件一致。提交标识和包版本号不能替代安装文件身份验证。

代码入口：`src/tegrastats_api/parser.py` 的 `start`、`_accept_line`、`get_snapshot`、`parse_line`；`server.py` 的 HTTP 状态路径和 `_update_data_thread`；`config.py` 的配置解析；`scripts/install.sh` 的安装和服务验证。

既有现场证据保存在 TTO 仓库 `evidence/device-install-20261012/`，重点为 `thor-raw-tegrastats.txt`、`thor-gpu-utilization.txt`、`thor-nvml-probe.json`、`orin-service-inspection.txt`、`orin-runtime-verified.json`。交接时同时提供这些文件；它们不是公开资料，也不包含 SSH 密码。

本次审查已离线复放两条 Thor 帧：当前解析器保留真实温度和 rail，主要提取缺口在 TTO；GPU 路径尚未新增。已复现 TTO 同 key 仅改 platform 仍返回 duplicate，以及 server 清理异常跳过后续组件；GPU 单槽覆盖是未实施设计的并发反例。原有 `tests/offline` 110 项通过，只证明现有修复基线，不证明新增 NVML 或设备验收。现场帧缺少 GR3D token 不等于所有 Thor 永远没有该 token。

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

### 第一步 固定识别规则和运行能力

启动时读取设备树 `compatible` 的 NUL 分隔 token，精确匹配 `nvidia,tegra234` 和 `nvidia,tegra264`。保留识别依据供诊断。model 用于展示，不用自由文本、hostname 或 IP 作主判据。标识冲突或不能识别时记录 unknown，不猜平台。

Orin 首轮保留现有 tegrastats 利用率路径；Thor 选 NVML，并核对目标设备上的指标支持。若实际 Orin 驱动不提供旧字段，应记录能力缺口，再由审查明确是否将 NVML 支持扩到该类 Orin；不要通过猜驱动版本构造多层 fallback。

平台及选定 GPU 策略在一次采集生命周期内固定：已识别 Thor 即选 nvml，即使缺绑定也不把 platform.gpu_backend 改为 unavailable。成功设备句柄的 UUID/名称和识别依据进入该生命周期的诊断记录。已确认单 GPU 才选择索引 0；多设备或 MIG 不明确支持时报告不可用，不默选、混读或新增自动选择链。硬件、后端和周期设置变更通过新 stream 生效，TTO 同步校验。小型识别函数和一个读取 worker 足够。

### 第二步 增加有界的 Thor GPU 读取

使用 NVIDIA 官方 Python NVML 绑定 `nvidia-ml-py`，在 Thor worker 内延迟导入 pynvml，声明 Thor 可选依赖；Orin 无绑定时包导入、CLI 和采集都正常。先记录有效服务解释器的 Python 版本、绑定发行包版本、NVML/驱动能力和实际设备身份，再锁定候选依赖；不能仅凭 import 成功或版本数字相似证明兼容。依赖缺失为 unavailable，初始化/worker 启动异常为 error，均不使 parser.start 或 server.start 因 GPU 问题退出。

Thor 默认读取调度周期固定为 1000 ms，独立于既有 tegrastats_interval；GPU timeout 固定为 max(5000, 3×GPU 周期) ms。Orin 从源行读取，GPU 周期等于实际源周期。源周期字段取最终 parser.interval，保留默认 1000 ms、合法 1000.0 归一化及 1=1 ms 的含义。若增加 GPU 配置项，沿用 Config.resolve 的 CLI > TEGRASTATS_API_* > 旧 TEGRASTATS_* > 默认优先级、合法值校验、预览和最终摘要；不改原源周期或重构 CLI。诊断分别记录调度设置、实测尝试/成功间隔与耗时，不称为 NVML 硬件统计窗口。

GPU 读取组件是本代 NVML 会话的唯一 owner；初始化和查询只在一个 worker 中执行，只有本代初始化成功才配对释放。线程构造/启动失败时取消本代启动归属，未初始化则不调用 shutdown；已进入 worker 的清理由原 owner 完成。shutdown 抛错保留本代资源归属，确认无执行中调用后才能由原 owner 重试。读取失败发布带完成时刻的 error 结果；之后每个既定周期至多尝试一次以允许恢复，不忙循环、不反复 init，不越过错误选旧成功值。初始化失败不后台无限重试。不支持指标为 unavailable，不修改驱动、MIG、功耗或 persistence 设置。

退出沿用 request_shutdown 意图与正常清理协作，停止事件唤醒周期等待；不在信号 handler 内同步 stop、join 或 shutdown。GPU join 按共同合同等待最多 2 秒，原生查询未返回时保留 owner/session，报告 cleanup_pending，并继续尝试源进程、未领取输出管道、数据广播及 model monitor 的清理。正常关闭错误在全部清理尝试后报告；启动失败时仍以原始启动错误为主，另记清理错误和未完成资源，错误状态及重复清理可重试归属保留。只修这些组件交接，不重构全仓 CLI。所有旧信号、输出管道、启动失败和重启回调回归均须保留。

### 第三步 保持样本提交的原子性

在源读取完成处保存单调时间 t 和 UTC；Thor 按共同合同立即取得符合 t 的结果副本，或从有界历史选择。缓存保存本代成功、错误和能力结果及完成时刻，容量在实现说明中列出；不能单存 latest 再在解析后过滤。Orin 直接解析同一行，不新增 GPU 缓存。_accept_line 校验 stream/运行状态，将解析数据、platform、GPU 全对象和真实源周期作为同一提交封存，再递增 seq。晚到结果留待后续源行；不存在符合条件的结果时为 unavailable，不能修正成零年龄。

get_snapshot 继续在数据锁内深拷贝数据与身份，HTTP/WS 发送在锁外。GPU 查询、长等待和资源释放不进入该锁；缓存选择只持短锁并生成副本。比较 HTTP/WS 同 seq 的封存内容，不要求不同响应的顶层 timestamp 或外层年龄相等。TTO 必须按 T2 增补 platform/周期校验，不能把当前未比较 platform 的旧指纹当作新增字段已受保护。GPU/平台初始化不填充 _current_data，首次有效源行之前仍为空和 503。

Orin 百分比直接来自该行时，GPU 年龄从该行的接收时间近似开始计算；不能宣称这是 GPU 硬件测量的精确时刻。Thor NVML 读数有独立采样时间，不能把 tegrastats 的 fresh 状态套给 GPU。

### 第四步 保留传感器和功耗含义

继续发布 `soc012`、`soc345` 和三个实测 rail。保留 `current`、`average`、`unit=mW`，不相加为总功耗，不把 `VDD_CPU_SOC_MSS` 改名为 `VDD_CPU_CV`，不拆分分组温度。

继续覆盖既有解析修复：RAM/SWAP 不能成为功耗；异常单位和冲突 rail 不产生有效数值；缺字段不能补 0。CPU 聚合和 TJ 接口保留既有合同。此次不因支持 Thor 重写整个正则解析器。

### 第五步 发布身份和安装检查

诊断列出识别依据、固定平台/后端、实际设备身份、指标支持、源/GPU 调度周期、耗时和失败/清理原因。新字段只在共同合同指定的完整状态及 tegrastats_update 中封存；分类 API 保留投影，health 保留存活语义。按新候选 Orin/Thor 报文重做旧 TJ 解析、Socket.IO 包大小和分片验证，不能沿用旧候选大小结论，也不宣称旧主板已能解释统一 GPU 字段。

后续发布入口必须安装指定的非 editable 候选 wheel 及锁定的 Thor 可选依赖；现有 scripts/install.sh 的 pip install -e . 不能充当候选发布验证。若继续使用安装器，仅补候选 wheel 入口和生效核验，不扩大 conda/系统重构。授权发布前核对 systemctl show 的有效 ExecStart、解释器、环境及 override；安装到该解释器对应环境。保留用户 override，环境不匹配时停止成功声明。授权切换后核对新 PID/启动时间、进程加载的模块路径和安装文件 SHA；systemctl start、磁盘已更新、短命验证 Python 或 health 成功都不能证明旧进程已加载候选。

新候选版本区别于现有 1.0.1，同时对齐 pyproject 分发版本、__version__、CLI 和运行诊断；当前 pyproject=1.0.1、内部 __version__=1.0.0 的差异纳入修复。保存提交、wheel SHA、模块文件身份、解释器和锁定依赖清单。授权发布前备份旧 wheel/依赖、有效服务配置及 override，写明恢复旧包和配置、授权重启、核对回退 PID/路径/SHA 的步骤。版本相同不证明代码相同；本轮构建和安装验证仅在本地隔离前缀进行，不安装到真实设备或执行设备部署/回退。

## 验证和验收

先执行 `tests/offline` 范围的测试，核对 fixture 和 subprocess/network 隔离。不要直接运行可能启动 tegrastats、网络或模型监控的其他测试。

| 层次 | 必须覆盖的情况 | 通过标准 |
| --- | --- | --- |
| 平台识别 | NUL 分隔 Orin/Thor token、自定义载板 model、缺失、未知及 tegra234/264 冲突 | 精确识别、冲突 unknown；保存已确认兼容串 fixture，不靠 hostname |
| GPU 数据 | 共同 T1/T5，Orin 正常 token、Thor 0/非零及失败恢复 | 新旧判别、类型及状态组合正确；GPU 问题不停止 TJ/其他采集 |
| 时间与身份 | 共同 T2/T3/T5/T7，包含覆盖反例、历史耗尽和消费者独立年龄 | 全对象封存、代际隔离、因果选择及重复校验正确 |
| 生命周期与入口 | 共同 T4/T6，CLI/server/parser/worker 的信号、异常清理及最终采集命令 | 原 R1/R2/F1/F2 保留，原始错误与剩余清理不丢失，周期毫秒贯通 |
| 解析回归 | Thor 实测温度和 rail、Orin 原有帧、RAM/SWAP、重复冲突 rail | 原有修复保留；真实名字和单位不漂移 |
| 包和服务 | 共同 T8，干净 wheel、无绑定 Orin、绑定替身 Thor、旧 override/旧 PID | 离线包验证通过；现场生效身份在另行授权后核对 |
| 实机只读检查 | 用户另行批准安装后，TTO 180 秒 doctor | 仅验输入合同、两路状态和资源；不替代完整过程、未来标签或模型精度验收 |
| 实际任务 | 用户正常任务期间与 NVML 参考同步比较 | 时间对齐后记录差异；取得真实负载响应证据，不能用空闲 0% 代替 |

新增 GPU 路径须记录服务 CPU/RSS 和采样耗时，并与更新前同类状态比较；没有现成资源门槛时先给实测结果，不凭空宣称低开销或达标。首次无需额外启动合成压力任务。

## 分阶段交付和停止条件

1. 本轮已获授权：先同步最终合同并交接仓库写入权，保存现有改动；仅实施 rm01OrinStatus，不改 TTO 生产代码或旧证据。
2. 按本次授权先实现小范围识别、GPU owner 与因果封存、异常清理和周期入口；新增 T1–T8 并重跑原 110 项及必要旧客户端回放。
3. 将同一合同版本的 Orin/Thor、错误/过期/旧结构 fixture 交给 TTO，TTO 实时与回放共用校验；两边分别完成非 editable 候选包、依赖及 SHA 证据。
4. 用户另行批准发布后，先验证服务实际进程身份与真实 HTTP/WS，再进行 TTO 输入 doctor；完整任务、采集及建模按原阶段另行安排。旧 override/PID、cleanup_pending/cleanup_error 或合同未对齐时不宣称部署成功。

同一 seq 内容被改写、同 stream 平台/周期漂移未检出、GPU 错误影响 TJ、未来结果入帧、NVML cleanup_pending/cleanup_error、旧 Orin 合同退化、旧进程身份未切换、平台无法可靠识别却被判为 Thor，均为阻止发布的问题。软件不支持的指标保持不可用；不能靠临时造值通过验收。

## 独立审查要回答的问题

- 平台识别是否有直接证据，未知平台是否保持诚实？
- GPU 合并是否遵守原子样本和因果时间，重复缓存是否仍可识别？
- 老客户端、TianshanOS 和 TTO 对新增字段、可用性及 payload 大小是否兼容？
- 选择的依赖和 NVML 接口是否适配目标 Python/驱动，失败与退出是否有界？
- 改动是否限于已确认问题，安装验证是否核对了实际运行路径？
- 交给 TTO 的接口是否与配套方案完全一致？

## 官方依据

- [NVIDIA Thor GPU Management Tool](https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonThor.html#gpu-management-tool)：官方推荐使用 nvidia-smi 监控 Thor GPU 利用率。
- [NVIDIA nvidia-smi 文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html)：指标含义、支持限制，以及面向工具开发优先使用 NVML/官方 Python 绑定的说明。
- [NVIDIA Thor 设备树资料](https://docs.nvidia.com/jetson/archives/r38.4/DeveloperGuide/HR/JetsonModuleAdaptationAndBringUp/JetsonThorAdaptationBringUp.html)：Thor 的 Tegra264 平台资料。具体设备识别以本机 compatible 为证据。
- [NVIDIA Orin 设备树资料](https://docs.nvidia.com/jetson/archives/r36.4.3/DeveloperGuide/HR/JetsonModuleAdaptationAndBringUp/JetsonAgxOrinSeries.html)：Orin 的 Tegra234 平台资料。

- [NVML 查询接口](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)、[初始化与清理](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlInitializationAndCleanup.html)、[利用率统计窗口](https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlUtilization__t.html)：查询不提供 timeout 参数，调用方 join 不能取消原生调用；GPU 查询周期不等于硬件统计窗口。
- [R38.4 tegrastats](https://docs.nvidia.com/jetson/archives/r38.4/DeveloperGuide/AT/JetsonLinuxDevelopmentTools/TegrastatsUtility.html) 与 [官方 Python 绑定](https://pypi.org/project/nvidia-ml-py/)：保留实际 token，依赖版本须经目标 Python/驱动证据核定。
