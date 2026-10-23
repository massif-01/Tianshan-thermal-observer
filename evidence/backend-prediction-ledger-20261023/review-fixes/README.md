# PR #20 审查返修

本版 11def662 随后被发现引入旧版结束描述文件 P1；下文“可以推送”的就绪结论已撤销。最新修复与验证见 [生命周期收敛报告](../lifecycle/README.md)，本文件保留当时的结果与边界。

修复基于 PR #20 原头 1b4208a4，base 仍为 PR #16 的 8f577a67。未改采集、模型、签发或评分算法，也未改 frontend/static。后端版本为 0.2.4+observe.5，Web Python 源码为 1.0.0rc6+ledger.2。

## 四项修复

| 问题 | 根因修复 | 原有测试强化 |
| --- | --- | --- |
| 后台早已结算、Web 晚收到的评分被页面增量漏掉 | records_after 按 Web 收到新 revision 的时间筛选，内部元数据随窗口/发布者清理；保留原始后台时间，同一 revision 不重复记更新 | test_prediction_delta_preserves_whole_window_denominator_and_recent_label_updates：调用实际 API handler，按 ID 合并增量后与完整结果相等，覆盖旧评分、首次补回的旧记录和重复修订 |
| 新发布者在 Web 断线期间运行并结束，旧实时帧阻塞终态恢复 | 实时与预测通道共用 begin_publication；更换已绑定发布者时统一清理实时上下文与预测缓存；旧响应/断开不影响新发布者，同一发布者重连保留历史 | test_committed_socket_recovery_terminal_scores_and_new_producer：两个通道同时 follow，真实 Unix socket，已有旧帧的接收器与全新接收器均恢复新终态；旧连接消息不能覆盖或断开新上下文 |
| 模型失败时 conditional_assumptions=[] 违约 | 仅发布编码将空列表转为 null，保留正常对象与原始账本 | test_encoder_unavailable_is_renderable_and_deadline_never_renewed：真实 Ledger → PredictionView → State，校验两份预测定义及运行时完整 snapshot；验证正常对象保留 |
| 标签清理测试从未把标签送入 State | 标签先进入接收缓存并验证存在，再推进保留窗口 | test_prediction_window_eviction_removes_inline_label_metadata：过期标签消失，窗口内标签保留，返回记录与 labels 的 ID 集合一致 |

仅强化这四个既有测试函数，未增加重复测试函数；未引入备用预测、重扫磁盘或额外重试。共用清理逻辑也用于原有 run/epoch 切换，避免重复 reset。跟随通道始终携带连接所属的发布者身份；原 boot/model/spec/origin 校验保留。

## 本地结果

- [后端源码](pytest-source.log)：46 passed。
- [独立安装后端 wheel](pytest-installed.log)：46 passed；只安装到 /private/tmp 的新测试 venv，没有安装 Web。[安装身份](installed-identity.json)核验 68 项通过，target_environment_checked=false。
- [Web 非服务组件](pytest-web-components.log)：61 passed、3 deselected；未运行服务、CLI 启动和安装测试。实际 API handler 在进程内调用，没有启动 HTTP/SSE 服务。
- [最终复审针对性验证](pytest-final-review.log)：5 passed（原 socket 用例有两种参数），覆盖四项问题与新旧发布者隔离。警告仅为既有 aiohttp 字符串 AppKey 用法，本轮不改。
- [回放](replay.json)：5572 条模型状态与原有编码结果一致；1065 条预测、1065 条评分按后台原 ID 一致，两侧均 355 个起点。backend_scoring 与初版验收摘要完全相等；正式页面集合仍为 1059 条。
- 同一筛选集合的 15/45/90 秒已评分数为 350/344/336，MAE 分别为 0.555783/1.392588/2.769418°C。它们是本次录制数据回放结果，不代表设备现场分数。

源码和安装包采集故障测试曾被并行启动，源码四项遇到“另一个TTO观察进程正在运行”的原生锁冲突；确认原因后串行重跑源码全部通过，没有放松锁或增加生产兜底。当前日志为最终通过结果。

两份 schema 的预测记录定义均通过校验。历史 requirements schema 的完整快照尚缺既有 model.remaining_valid_ms 定义；本轮未修改这一历史差异，完整快照按运行时 schema 校验。

## 身份与开销

- 后端 68 项清单 SHA256：89daf0bbdb87c56286a6b143a4e98b30f09cc5068df12c5cd07322cac02d7e6d。
- 后端 wheel SHA256：0e20d6cae125bca68e43d8f7892ad6833f95d136d75a8291900d12be62389e4f。
- Web 源码 68 项清单 SHA256：6d690623e0127ec967ff27a30b2abd117c6de77ed2eacf14a4b734ca9afdfb18。未构建或安装 Web。

新增更新时间表仅位于 Web 内存，不进入 observe.2 的采集回调；后端本次仅调整可选发布编码中的空假设表示。[一小时窗口组件测量](window-cost.json)含 2160 条记录、17 页，最大页 196952 字节、终态 3300169 字节，仍在原协议预算内。更新时间表纳入后的相关 Python 对象总量约 12.14 MiB，其中新增表约 101 KiB。测量只含视图/预测缓存，非整进程 RSS，也不是 N305 性能结果。本轮未重新测量采集 CPU；初版四模式短测保留为历史参考。

## 最终审查

结论：可以推送，限已验证的本地 Python 接收与进程内 API 范围。重新审查最终运行路径、四项验收对应关系、身份清理、修订幂等、缓存界限和软件清单；针对性五项再次通过，git diff --check 通过。没有发现阻塞本轮交付的问题；这不等同于浏览器或设备验收。

未连接 N305、未安装或启动 Web、未部署、未合并。浏览器/Cloud 前端集成、Linux CPython3.10、N305 CPU/RSS、长期运行和现场短测仍未验证，继续等待归档完成后的另行授权。
