# observe.3 发布接口：本地验收

基线：`origin/main` 的 `822d6dc`（已包含 Web UI PR #15）。分支 `feat/observe-publication`；只修改后端候选、其验证和说明，不混入界面改版。版本 `0.2.4+observe.3`；冻结模型、原生 collector、quality、投影算法、预测账本算法未修改。当前软件身份不同于 observe.2。

边界：仅 Mac 本地源码、后端 wheel、录制回放和自建 loopback 服务。没有连接 N305，没有安装或启动 Web，没有部署、现场短测或长期运行。Web 验证直接调用仓库现有 follow/State，不启动 HTTP 服务。

## 独立方案审查与实施中审查

独立审查结论为“补充后方案可执行”：在已有 states 提交后，转交独立快照给有界发布线程；复用现有投影和模型状态，只编码，不再创建有状态观察器。丢帧/错误须撤销编码缓存；模型不可用时公共模型字段补 null；不能因发布延迟续期；boot 时钟和进程时钟必须分开。

实施中独立审查发现把冻结模型字面标签误记为进程时钟域，已修正为真实 Clock.domain，并增加最终 socket 包与 states.jsonl 逐条相等的断言。冻结标签另存 `frozen_state_clock_literal`。

故障测试还暴露并修正了两个具体问题：过小的客户端队列会把初始突发误判为慢客户端；首次 latest 必须在注册客户端前排队，避免重排。Python 3.12 的 Server.wait_closed 会等现存连接关闭，收尾必须先中止客户端、再等待 server；非读客户端使用 transport.abort，避免排空发送缓存拖住收尾。这些是测试期间修复的问题，最终通过结果见下。

最终独立提交审计结论：**可以推送**。审查员检查全部 tracked/untracked 交付范围，另行运行纯发布/socket/follow 测试（9 passed、6 deselected），重算67项文件身份、回放摘要和9次开销样本中位数，并检查 git diff --check；未发现本轮阻断问题。审查未连接设备、未重跑采集/开销实验。分开维护编码白名单的未来漂移风险由逐包回放对比约束；现场和浏览器仍未验证。

## 修改文件

- `observe_runtime.py`：快照、states 提交后的发布钩子、独立生命周期/错误统计；`observe_cli.py`：可选 `--publication-descriptor`。
- 新增 `web_encoding.py`：纯字段编码；新增 `web_publication.py`：有界发布线程、描述文件和 Unix socket。
- `__init__.py`、`pyproject.toml`、`candidate-files.json`、seal/assemble 脚本：observe.3 软件身份及构建一致性。
- 新增 `test_web_publication.py`、replay/cost 验证脚本；原授权合同测试随当前版本取值。
- 操作卡、发布协议说明和本目录：使用方式、验证结果、限制。

## 数据保真

[replay.json](replay.json)、[replay.log](replay.log)：使用交接指定的 30 分钟录制数据，5572 条原始记录，通过真实 Consumer.on_record/_work；使用显式虚拟接收时钟，保留原始 mono_s，等待每帧处理结束，因此这是无强制丢帧的离线编码保真验证。生成 5572 条真实 states 记录，只有一个后端有状态 observer。

- 5572 个公共包与现有 Web Adapter.encode 白名单和值逐包相等；排除编码实际时间、记录 deadline 表达和新增软件版本字段。
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

- [pytest-source.log](pytest-source.log)：41 passed。
- [pytest-installed.log](pytest-installed.log)：独立后端 wheel 环境 41 passed。
- [pytest-identity-final.log](pytest-identity-final.log)：补充最终 model/spec/process clock 身份断言，1 passed。
- [installed-identity.json](installed-identity.json)：observe.3、67 项源码文件哈希核对，原生版本0.2.4；NumPy2.2.6/SciPy1.15.3及其单线程数值池通过核验；target_environment_checked=false。
- 构建 wheel SHA256：`24a8f0eec56d72a5435145af0782029803d93d3828c47d39de83ec3a34fc8181`；候选清单 SHA256：`0ee6ea4f29a4f8a99368d037a3c9edcd8b41a060d9cbb0c5d07f701388654692`。wheel 只在本地构建和安装验证，未发布二进制。

故障覆盖：真实 follow 订阅断开和重新建立、全新订阅 State、生产者新 run 重启、旧包过期、发布队列溢出、真实非读 socket 写压、编码异常、JSON NaN/超大包、publisher 锁冲突、启动/入队/退出失败。包含失败后恢复包的 publication_gap 和旧 fan/source_health 缓存撤销；启动、编码、入队、退出故障下实际 loopback 原生采集和 states 均继续，单观察器、无原生丢帧、无设备写入/推理请求。测试时的 fixture boot 身份只用于本地测试，未伪称验证了 N305 boot_id。

## 开销

[cost.json](cost.json)、[cost.log](cost.log)：方法：每种模式3次、每次10秒、各自独立进程顺序执行，预先一致加载数值库；发布关闭、开启无人订阅、开启订阅但不读。CPU为整个进程（含本地假源），RSS为周期采样峰值；callback耗时只含原有 Consumer.on_record 及新增快照成本，不包括此前原始写盘。没有同时运行其他本任务的性能或采集测试。

| 模式 | 单核CPU中位数 | RSS采样峰值中位数 MiB | 回调均值中位数 ms | 回调P95中位数 ms |
| --- | --- | --- | --- | --- |
| 发布关闭 | 1.673% | 72.98 | 0.719 | 1.674 |
| 发布开启，无人连接 | 2.562% | 73.11 | 0.729 | 1.284 |
| 发布开启，客户端不读 | 2.559% | 72.25 | 0.758 | 1.358 |

9次运行均无原生/模型丢帧、模型错误或发布错误；开启时发布线程均正常退出，非读客户端被识别并断开。RSS差异小于这些短测的进程间波动，不能据此断言内存减少。

无 socket/编码等待进入采集回调；额外 raw/processed 快照、JSON 编码和线程竞争有成本。10秒本地合成测量不能证明24小时稳态，更不能证明N305的5%/8%CPU或128MiB预算。

## 未验证及部署前决策

未验证：N305/Linux x86_64 CPython3.10实际运行、真实boot/目录权限和服务用户、目标机CPU/RSS预算、浏览器实际显示、部署/故障跨服务运行、长时间稳定性。没有执行目标安装或现场授权流程。

部署前需用户确认原测试归档完成，授权新版本安装与新观察窗口，并确认生产者/Web用户、私有描述文件路径、独立Web prefix及运行方式。页面预测继续现有独立计算还是未来直接显示后端账本，是另一个产品决策；本 PR 保留现有行为，部署时应如实标注口径。没有尚未决定的本轮代码实现选择。

复现命令和协议细节见 [发布接口说明](../../experiments/mainline_observe_v2/docs/发布接口.md)。
