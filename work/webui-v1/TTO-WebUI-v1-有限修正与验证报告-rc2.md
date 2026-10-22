# TTO Web UI v1 · 六项有限修正与验证报告

2026-10-21，候选 **1.0.0rc2**。本轮完成 R1–R6 的本地修正与有限验证，交回独立复审；不自动进入 N305 安装或现场监看。产品结构、59009、紧凑指标、三大趋势和 C/D/E 保留。

## 候选身份与范围

- wheel：`dist/tto_web_ui-1.0.0rc2-py3-none-any.whl`，509462 bytes。
- SHA256：`d035bd24da55450f28f37bd8bc40d50c00b401e3e425632f5d67ced9f518ca70`。
- 新安装身份清单 `candidate-identities.json` 覆盖 120 项；运行清单 62 项，wheel 恰有 63 个非 dist-info 成员（含清单），无额外静态残留。
- G2 模型 SHA256 `dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`；spec SHA256 `2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`，均与 accepted 基线一致。
- accepted 43 项中 40 项字节不变；仍只有 `tto/collector.py`、`tto_field/runtime.py`、field 版本文件三项变化。`patches/accepted-field-to-web.patch` 已更新。field 标识为 `0.2.4+web.2`，历史 field 清单不重新冒充新身份。
- 原 rc1 ZIP 和 wheel 保留；原始 ZIP SHA256 `53502eea9ba618db117b939f6e533e2996f1e475defd771216658b4eaf70046c`。修前源码/报告/wheel 另存 `baseline/rc1-before-review/`。

本轮不连接 N305/Thor/ESP32，不部署设备、不发真实推理负载、不开展 CPU 先导或模型训练，不改变天山 OS 风扇、曲线、gain、保护、采样或 TTL，不推送、不创建 PR。

## 修正及证据

| 项 | 最终行为 | 必要验证 |
|---|---|---|
| R1 展示隔离 | 原 quality/observer/evidence/latest/callback 提交先完成；可选展示编码与发布有独立边界。`memory=null` 映射为不可用，保留原值为零的真实含义。展示故障保留最多 32 个异常类名并发布无载荷/无异常正文的 gap，撤销显示资格；下一次成功带 gap。原链的真实错误仍按原规则失败。 | 同一 native accepted TJ、无/有 hook 的 memory=null 均完成；注入编码异常不影响 callbacks/latest；故障 gap 撤值、恢复带 gap；原 evidence 异常仍抛原包装错误。fan.data=null 的旧行为排除本轮。 |
| R6 持续 observe | Web 停止信号与单轮 collector 停止信号分开，始终 await 并读取旧轮结果。只有 `reconnect_attempt_budget` 触发 1–30s 可取消退避；旧轮收完、释放原锁后再创建唯一新 run。STOP、授权/配置/处理失败、锁冲突不重启。 | 真实 collect/observe/server，设备传输与锁为受控替身；保留每轮 10 次预算，只缩短测试等待。开机不可达和十次连接后断线均从 10→11 次连接恢复；锁峰值 1、两轮 run 不同，停止后不复活。原实际共享锁冲突用例仍零网络。 |
| R2 有效性 | GPU 直接沿用 native quality.gpu 的值、原因、年龄和截止，同 sample 截止只能缩短，invalid 不恢复旧值。两 rail、逐核/聚合 CPU、RAM/SWAP 映射已有 outer 源龄。 | base 2s + outer 4s 保持 invalid/gpu_effective_stale；base 2s + outer 2.5s 剩余约 0.5s，0.6s 后撤值；同源年龄与原源龄相符。GPU 利用率不进入 G2。 |
| R3 同步撤值 | 后端提供模型、建议和保护上下文剩余资格；前端统一处理断流/本地到期，更新指标、phase、数值、节点、动效、健康文案及建议。当前未来参考由快照同步渲染，不依赖预测 HTTP 成功。暂停只冻结画面，恢复沿用原快照接收时刻。 | 真实 Chrome + 最终安装 wheel：SSE 断开、仍有 heartbeat 但快照停更两个场景，预测 API 同时故意 503；当前显示全部撤下，历史配对保留。暂停冻结通过。合成合法曲线建议先显示 34.3% 后撤下，仅用于验证分支，未安装为现场曲线。 |
| R4 事件归属 | 事件携带 service/run/epoch；V1 切换清理旧过程事件并重置去重。全局事件无设备 elapsed，API/前端均筛选所属身份。切换清除已选详情。 | old run 20s 任务事件不进入新 run 30s；同 run 的 epoch 切换也清除。真实浏览器点击旧事件后切换，详情收起；再向 events 响应注入旧身份，前端事件带保持空。 |
| R5 首标签结算 | 先消费/匹配有序源包，再按源流进度越过 target+2s 结算 missing；页面时钟不永久封口。合法结算按结算时刻进入增量响应，避免 HTTP 增量漏掉延迟更新。预测值不可变、首条有效标签、同身份和 gap 不可比规则保留。 | 真实 Unix Publication→follow→State.accept，接收时钟为明确受控替身：target24s，源标签25s，Web26.2s 接收；Web26.1s 仍 pending，之后 matched，records/summary 分母一致；超过 +2s 的源标签仍不配对。 |

## 最终 wheel 验证

- **41 passed，6 warnings，15.80s**。原 34 项 + 本轮 7 项（含参数化）。用开发 pytest 驱动、`PYTHONPATH` 指向独立安装的 wheel，`TTO_WEB_TEST_INSTALLED=1` 禁止 conftest 注入 src/vendor；日志中的模块位置为独立 prefix。CLI 两次启动/停止和占用冲突也来自 wheel。六个 warnings 为已有 aiohttp AppKey 建议。
- Linux 独立复审指出的 UID501 夹具已局部补模拟用户名；未改变生产安装权限判断。
- 运行依赖和 wheel 均 `--no-index`，在独立 `/private/tmp/tto-web-rc2-final` 离线安装成功，release 为 `1.0.0rc2-b28b105d`，62 项运行身份核验通过。未修改原 TTO/Conda base。
- 真实浏览器使用上述同一 SHA 的首次独立安装。第一次安装的 release 目录仍带 rc1 文本，已修正安装器版本标签并在新 prefix 重做离线安装；目录名差异不改变 wheel。新 prefix 又完成真实 CLI follow 短运行与身份检查。
- 浏览器仅增加 R3/R4 对应场景，没有重复整个原视觉矩阵。截图已人工查看。控制台断流/503 是故意故障注入；最终场景无意外 400。测试控制接口只存在于单独 loopback harness，不进入生产 wheel。
- 新 runtime schema 加入 `model/advisory.remaining_valid_ms`、`health.protection_remaining_valid_ms`、可选 `forecast.settled_elapsed_ms`。原交接 contracts 原样保留在 requirements；原 examples 仍按原 schema 验证，实际输出按 runtime schema 验证。后端决定资格，前端不猜设备 TTL、不重算热模型。

证据均在 `evidence/repair-20261021/`：`old-repro/`、`final-wheel-tests.log`、`final-wheel-recovery.log`、`final-wheel/observe_recovery_result.json`、`browser-results.json`、`browser-checks-final.log`、`offline-install-final.log`、`final-identity-verification.json`。浏览器截图为 `output/playwright/rc2-*.png`。

保留了开发失败轮次：最初 schema 尚未扩展、测试断言边界错误、工具身份未重封、CLI/浏览器同时占端口等日志。端口冲突保护未被放宽；顺序重跑通过。旧 TS 反例保留，未把“旧缺陷仍成立”作为修复通过条件。

## 资源与剩余边界

运行方案仍为单个 Python aiohttp 服务、静态 TS/ECharts，无 Node/CDN/数据库常驻；不引入新轮询、线程池服务或依赖。新增异常缓存最多 32 项；原历史、预测、事件和队列上限保留；恢复等待可取消，最多一轮采集器。页面本地资格检查沿用 200ms，后端按期限/1Hz刷新，不恢复高频完整重建。

最终 rc2 wheel 的一次短测：**120.83s，120 次采样、0 错误，单核等效 CPU 均值 2.753%，RSS 峰值 81.11MiB**（首样本 70.22MiB，末样本 81.11MiB）。macOS ARM64 上独立安装的 Web follow 进程，单个真实 Chrome 页面，原生合成来源在另一进程；不含 Chrome/原生观察器成本，不是 N305 成绩。此短测在 5%/192MiB 开发预算内；不据此承诺无限期内存稳定。证据 `resources-final-wheel-120s.json` 和 `installed-process-final.json`，实际 wheel SHA 与本报告一致。

原 30 分钟结果 **1800.85s / 单核3.4339% / RSS97.50MiB** 只属于旧构建身份，原证据与失败轮次保留；不称为 rc2 的 30 分钟成绩。本轮没有 Linux/CPython3.10 或 N305 执行环境：复审包中的 rc1 Linux 离线安装与 systemd 静态核验属于主审历史证据。rc2 的 Linux 实际安装、systemd 启用/重启/开机、现场断源恢复及实际资源仍需下一阶段另行安排。

RPM、结构测温、置信度、未登记任务状态、未核实现场曲线建议均继续按不可用说明展示。完成本轮后停止测试服务与浏览器，等待独立复审。
