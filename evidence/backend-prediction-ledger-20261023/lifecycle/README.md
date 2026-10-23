# PR #20 发布生命周期收敛

针对 bot 的 P1：旧版 Publication 正常关闭写出的描述文件没有 publisher_id。11def662 在识别结束状态之前读取该字段，KeyError 导致整个 follow 退出，下一发布者无法连接。强化原有旧版测试后，修复前可复现这一失败。

## 实现与删除项

Web Python 版本为 1.0.0rc6+ledger.3；后端仍为 0.2.4+observe.5，本次后端 src 字节未变。未修改旧版发布器的启动/退出行为来回避问题，也未改 frontend/static。

- source.publication_descriptor 是唯一描述文件解析点，按运行、正常结束、发布失败区分字段要求。运行态需要身份和固定 socket；带最终账本的结束态仍需要身份；旧版匿名结束单独识别，不补造身份。
- source.follow 是唯一生命周期负责人：取消并等待旧接收任务退出，再处理新描述状态、切换身份和启动接收。两个子任务只接收数据，不读取 active.json、不做身份切换。
- 删除上一轮 State.accept/disconnect 的 publisher 参数及分散的旧消息判断；预测接收任务也不再重复解析描述文件、判断结束或忽略旧任务错误。保留数据自身的 boot/model/spec/origin/publisher 校验。
- 入口负责发布切换后的状态快照，移除 begin_publication 中的额外 refresh 和结束路径的重复 refresh。原 run/epoch 清理逻辑保留。
- 子任务的意外异常由入口观察并向上传播；入口退出前回收其他任务并撤销当前参考。不增加捕获 KeyError 的兜底、无条件重启或后台守护循环。

## 完整生命周期验证

只强化三个既有测试函数，其中账本 socket 用例原有两个参数；没有增加平行的同义测试函数。

| 输入/转换 | 验证的接收结果 | 原有用例 |
| --- | --- | --- |
| 启动时描述文件缺失 → 旧版运行 | 保持等待，发布器注册后接入；不生成 Web 预测 | legacy_publication |
| 旧版运行 → 描述文件消失 → 同一发布者恢复 | 撤销当前显示后恢复，同一 run 保留 | legacy_publication |
| 旧版实际 __aexit__ 写无身份 ended → 下一旧版发布者 | 原接收任务仍存活，新发布者连接成功，模型/预测参考撤销 | legacy_publication |
| 从旧版无身份 ended 启动 → 后续有效注册 | 新建接收器保持等待，随后接入同一新 run | legacy_publication |
| 非对象/缺少运行身份/错误 boot/非布尔 ended/无身份最终账本 → 有效注册 | 等待有效描述文件；两个接收器均未退出，不宣称账本完整 | legacy_publication |
| 新版运行 → 同一发布者重连/Web 状态重建 | 原 ID 的预测、评分与已提交账本相等，多页补取未跳过 | committed_socket（两种参数） |
| 新版正常结束 → 从终态启动 → 下一发布者 | 最终评分恢复，时间轴冻结，当前参考撤回 | committed_socket（正常参数） |
| 新版发布失败 → 下一发布者 | 标记状态未知/记录不完整；记录器继续落盘，再接入新发布者 | committed_socket（失败参数） |
| 真实查询回复被延迟 → 新发布者结束、没有实时帧 | 旧查询任务退出在新 begin_publication 之前；原接收器和全新接收器恢复相同最终记录 | committed_socket（两种参数） |
| 新版无账本发布的订阅者重启、生产者重启、TTL 到期 | 按真实 run 切换、旧值到期，不引入预测 | actual_follow |
| 接收子任务意外 RuntimeError | 主任务观察异常、退出前撤销当前值，不留下静默死亡的子任务 | actual_follow |

上述缩写分别对应 test_legacy_publication_does_not_invent_unrecorded_predictions、test_committed_socket_recovery_terminal_scores_and_new_producer、test_actual_follow_disconnect_subscriber_restart_producer_restart_and_expiry。用例使用真实新旧发布器写描述文件和 Unix socket；延迟用例在真实查询完成后暂停返回，检查取消与身份切换顺序。复审中删除了该测试跨轮切换时对同一 State 重复启动 follow 的代码；原有接收器由同一个任务贯穿 B→C，只有用于对照的全新 State 有自己的独立任务。

## 本地结果

- [后端源码](pytest-source.log)：46 passed。[独立后端安装包](pytest-installed.log)：46 passed；沿用仅安装后端 observe.5 的 /private/tmp 测试 venv，没有安装 Web。
- [Web 非服务组件](pytest-web-components.log)：61 passed、3 deselected，包含前四项修复。HTTP/SSE 服务、Web CLI 启动和安装测试不运行。
- [最终独立审查复验](pytest-final-review.log)：上述三个既有函数的四项参数化执行通过。git diff --check 通过。
- [录制回放](replay.json)：5572 条状态/编码一致，1065 条预测和 1065 条评分按 ID 一致；仍只有一个有状态观察器。backend_scoring 与上一版完全相等，正式阶段集合仍为 1059 条。
- [完整跟随组件短测](follow-smoke.json)：原成本复现脚本改为使用唯一 follow 入口，4 秒本地假源运行中 native/model 丢帧和发布错误均为 0，发布线程正常停止。该客户端模式现在同时消费实时和账本，与旧版仅账本客户端模式不作直接性能对比；短测不是 N305 或长稳结论。

Web 68 项源码清单 SHA256：678d197b8741a1c7c27f7725903302212b740462037a66cfcc9482dd60c3e269。后端源码/包身份未变，沿用前次报告中的 observe.5 清单及 wheel。没有增加 observe 的采集/模型回调；描述文件读取从两个接收通道收拢到一个入口。本轮不重新给出设备 CPU/RSS 预算。

## 最终审查与边界

结论：可以更新 PR，限已验证的本地 Python 与进程内 API 范围。按描述文件形态与生命周期转换重新审查，不复用上一版“已就绪”结论；重点核对唯一入口、取消并回收旧任务的顺序、匿名结束不虚构账本结算、子任务异常可见性及既有保真/过期逻辑。没有发现阻塞本次交付的问题。

未连接 N305，未安装或启动 Web，未部署或合并。未验证浏览器/Cloud 前端集成、设备权限、Linux CPython3.10、N305 CPU/RSS 或长期运行。未知编程异常会显式传播并撤销当前显示，不承诺吞错后自动恢复。历史 requirements schema 与运行时完整快照的既有 TTL 字段差异未扩大处理。
