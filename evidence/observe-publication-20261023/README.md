# observe.3 发布接口：本地验收

基线：`origin/main` 的 `822d6dc`（已包含 Web UI PR #15）。分支 `feat/observe-publication`；只修改后端候选、其验证和说明，不混入界面改版。版本 `0.2.4+observe.3`；冻结模型、原生 collector、quality、投影算法、预测账本算法未修改。当前软件身份不同于 observe.2。

边界：仅 Mac 本地源码、后端 wheel、录制回放和自建 loopback 服务。没有连接 N305，没有安装或启动 Web，没有部署、现场短测或长期运行。Web 验证直接调用仓库现有 follow/State，不启动 HTTP 服务。

## 独立方案审查与实施中审查

独立审查结论为“补充后方案可执行”：在已有 states 提交后，转交独立快照给有界发布线程；复用现有投影和模型状态，只编码，不再创建有状态观察器。丢帧/错误须撤销显示缓存；模型不可用时公共模型字段补 null；不能因发布延迟续期；boot 时钟和进程时钟必须分开。

实施中独立审查发现把冻结模型字面标签误记为进程时钟域，已修正为真实 Clock.domain，并增加最终 socket 包与 states.jsonl 逐条相等的断言。冻结标签另存 `frozen_state_clock_literal`。

故障测试还暴露并修正了两个具体问题：过小的客户端队列会把初始突发误判为慢客户端；首次 latest 必须在注册客户端前排队，避免重排。Python 3.12 的 Server.wait_closed 会等现存连接关闭，收尾必须先中止客户端、再等待 server；非读客户端使用 transport.abort，避免排空发送缓存拖住收尾。这些是测试期间修复的问题，最终通过结果见下。

初版独立审计漏掉了下列三项问题，原“可以推送”结论撤回。原测试通过不能代替对应故障场景的证明。

## Reviewer 复查修复

- GPU 生命周期与显示缓存分离：同一 sample_id 的最早期限、撤销状态跨发布缺口/模型重置保留，固定只存一份可信样本记录；error/unavailable 空样本和不可信时间戳只撤销旧样本，不覆盖其身份与期限；新可信 GPU 样本或新 source_epoch 可以恢复。
- 溢出用例先建立 fan/GPU 有效缓存，再阻塞编码、让 fan 撤销帧真实丢失；在实际 socket + State 接收端断言 GAP、publication_gap、旧 fan 撤销、旧 GPU 过期/撤销后不可复活，以及新样本/新 epoch 恢复。两种条件参数化在原用例中，并串入 error/unavailable/畸形时间戳三种中间状态，覆盖 A→无可信样本→同 A 不得复活。
- 删除 Publication.start 的重复异常捕获。原初始化故障用例替换为真实 threading.Thread.start 失败，验证外层只记录初始化失败，publication=None，无后续入队或二次关闭错误。
- source_reset 统一由编码器执行；仅复制 processed.quality，在原实际采集/socket 用例中放入不可深拷贝的无用输出，验证它不会被复制、quality 则保持独立快照。

[review-mutations.json](review-mutations.json)：分别临时禁用 `_gap`、在 reset 时丢弃 GPU 样本记录、让无可信样本覆盖旧身份，强化后的现有用例均拒绝了对应变异。变异只存在于独立本地进程，没有改动仓库实现。新增测试函数数量不变，溢出用例增加一组独立有效性条件。

回放还暴露了原验证驱动的遗漏：它直接调用编码器，没有模拟生产发布器原有的 source_reset 清显示上下文行为，最后一条断连帧的 platform/observed_device/source_health 比较因此失败。修正验证驱动，在旧 Adapter 参考端施加相同生产者生命周期后重新对比；没有修改原生处理或模型去迎合旧参考缓存。

最终独立复审结论：**可以推送**，限本轮本地后端修复范围。审查员独立运行纯发布/socket/follow 10 项通过，正常采集与线程启动失败两项串行重跑通过；此前这两项并行尝试因争用原有唯一采集锁失败，已确认并纠正测试调度。另核对最终源码/wheel 各42项回归、67项文件身份、回放结果、9次成本样本与 git diff --check，未发现本轮剩余阻断项。未验证目标机、浏览器和长期运行，页面预测方式保持原状。

## 修改文件

- `observe_runtime.py`：快照、states 提交后的发布钩子、独立生命周期/错误统计；`observe_cli.py`：可选 `--publication-descriptor`。
- 新增 `web_encoding.py`：纯字段编码；新增 `web_publication.py`：有界发布线程、描述文件和 Unix socket。
- `__init__.py`、`pyproject.toml`、`candidate-files.json`、seal/assemble 脚本：observe.3 软件身份及构建一致性。
- 新增 `test_web_publication.py`、replay/cost 验证脚本；原授权合同测试随当前版本取值。
- 操作卡、发布协议说明和本目录：使用方式、验证结果、限制。

## 数据保真

[replay.json](replay.json)、[replay.log](replay.log)：使用交接指定的 30 分钟录制数据，5572 条原始记录，通过真实 Consumer.on_record/_work；使用显式虚拟接收时钟，保留原始 mono_s，等待每帧处理结束，因此这是无强制丢帧的离线编码保真验证。生成 5572 条真实 states 记录，只有一个后端有状态 observer。

- 5572 个公共包与现有 Web Adapter.encode 白名单和值逐包相等，参考端使用相同的生产者 source_reset 生命周期；排除编码实际时间、记录 deadline 表达和新增软件版本字段。
- 5572 份公共 model 与对应落盘 states 的 model 完全相同；model_id/spec_id、input_mono_s、source_epoch 均核对。
- JSON 序列化后交给现有 Web State.accept。
- 另用真实 loopback collector + Unix socket 测试最终收到的包与落盘 states 的模型、有效 TJ、run/epoch/model/spec、真实进程域、截止时间，补足回放直接编码不经过 socket 的边界。

## 页面预测口径

共同起点配对的 984 个 G2-HOLD horizon 预测最大绝对差为 **0 °C**。这不意味着两套完整账本一致：后端 355 个起点，Web 1635 个；后端 stride=5s、Web 最短1s；后端允许 provisional、Web 只允许 tracking/degraded。签发时刻和断开后的可比性也各自独立。

| horizon | 后端已评分 n / MAE °C | Web 已评分 n / MAE °C |
| --- | --- | --- |
| 15s | 352 / 0.55336 | 1622 / 0.58447 |
| 45s | 346 / 1.38504 | 1593 / 1.45601 |
| 90s | 338 / 2.75370 | 1556 / 2.81608 |

以上均为本次虚拟时钟离线回放，各自全部可评分集合，**不能作为 N305 实时分数，也不能跨集合比较优劣**。交接文档旧 MAE 不是验收阈值。本 PR 不追平旧分数、不改变冻结模型、不改变 Web 预测方式。页面当前不直接展示后端 B0/B1/G2 预测账本。

## 回归、故障和安装身份

- [pytest-source.log](pytest-source.log)：42 passed。
- [pytest-installed.log](pytest-installed.log)：独立后端 wheel 环境 42 passed。
- [installed-identity.json](installed-identity.json)：observe.3、67 项源码文件哈希核对，原生版本0.2.4；NumPy2.2.6/SciPy1.15.3及其单线程数值池通过核验；target_environment_checked=false。
- 构建 wheel SHA256：`bf7f6591502909d65e368db07d228e88c208e1c17e1ee52d3272bcac527c6233`；候选清单 SHA256：`1da3b4a077fd05b219eade1ef0a358e32d6d493e122f198bf06c00dd204eb0ff`。wheel 只在本地构建和安装验证，未发布二进制。

故障覆盖：真实 follow 订阅断开和重新建立、全新订阅 State、生产者新 run 重启、旧包过期、发布队列溢出、真实非读 socket 写压、编码异常、JSON NaN/超大包、publisher 锁冲突、启动/入队/退出失败。包含失败后恢复包的 publication_gap 和旧 fan/source_health 缓存撤销；启动、编码、入队、退出故障下实际 loopback 原生采集和 states 均继续，单观察器、无原生丢帧、无设备写入/推理请求。测试时的 fixture boot 身份只用于本地测试，未伪称验证了 N305 boot_id。

## 开销

[cost.json](cost.json)、[cost.log](cost.log)：方法：每种模式3次、每次10秒、各自独立进程顺序执行，预先一致加载数值库；发布关闭、开启无人订阅、开启订阅但不读。CPU为整个进程（含本地假源），RSS为周期采样峰值；callback耗时只含原有 Consumer.on_record 及新增快照成本，不包括此前原始写盘。没有同时运行其他本任务的性能或采集测试。

| 模式 | 单核CPU中位数 | RSS采样峰值中位数 MiB | 回调均值中位数 ms | 回调P95中位数 ms |
| --- | --- | --- | --- | --- |
| 发布关闭 | 2.032% | 72.09 | 0.865 | 1.707 |
| 发布开启，无人连接 | 2.771% | 74.30 | 0.755 | 1.871 |
| 发布开启，客户端不读 | 2.809% | 73.89 | 0.825 | 1.625 |

9次运行均无原生/模型丢帧、模型错误或发布错误；开启时发布线程均正常退出，非读客户端被识别并断开。这些短测存在进程间波动；回调均值的下降不能解读为发布减少了采集开销，RSS也不能据此外推长期内存占用。

无 socket/编码等待进入采集回调；额外 raw/processed 快照、JSON 编码和线程竞争有成本。10秒本地合成测量不能证明24小时稳态，更不能证明N305的5%/8%CPU或128MiB预算。

## 未验证及部署前决策

未验证：N305/Linux x86_64 CPython3.10实际运行、真实boot/目录权限和服务用户、目标机CPU/RSS预算、浏览器实际显示、部署/故障跨服务运行、长时间稳定性。没有执行目标安装或现场授权流程。

部署前需用户确认原测试归档完成，授权新版本安装与新观察窗口，并确认生产者/Web用户、私有描述文件路径、独立Web prefix及运行方式。用户已确认页面预测需要可追溯到后台记录；具体方案留待本轮修复后讨论。本 PR 保留现有预测行为，部署时应如实标注口径。没有尚未决定的本轮代码实现选择。

复现命令和协议细节见 [发布接口说明](../../experiments/mainline_observe_v2/docs/发布接口.md)。
