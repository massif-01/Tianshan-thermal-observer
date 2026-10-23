# 后台统一预测：本地验收

最新审查返修见 [review-fixes/README.md](review-fixes/README.md)：修复晚到评分增量遗漏、发布者切换后的终态恢复、空假设编码和标签清理测试。当前软件身份为 observe.5 / ledger.2；下文保留初版 observe.4 / ledger.1 的验证与成本记录，当前结果以返修报告为准。

范围：后续分支 feat/backend-prediction-ledger 基于 PR #16 修复头 8f577a67。PR #16 仍未合并；本 PR 以它的分支为 base，单独交付。已读取最新 origin/main 59d9f827（新增路线图文档），未改动主目录未提交工作或 Cloud 的前端工作树。

后端版本 0.2.4+observe.4，Web Python 源码版本 1.0.0rc6+ledger.1，软件身份发生变化。冻结模型、质量处理、采样、5秒签发调度、实测匹配评分算法未改；scores增加结算单调时刻与实测接收UTC。未连接N305，未安装或启动Web，未合并。浏览器frontend与static文件不改。

## 方案独立审查

审查结论：补充约定后可执行。采纳：Web/账本 run与model身份显式映射；Consumer.emit写入成功后单点更新读视图；分页只确认实际已收修订；advisory也使用当前预测资格；撤回后旧ID不能复活；结束先提交评分、写正式终态快照、再标ended。未增加第二观察器、磁盘重扫兜底或备用预测。

前后端约定：[给Cloud Sonics5.5](../../docs/后台统一预测-前后端接口约定.md)。前端需按forecast资格与latest_prediction_ids显示，调整更新时间/目标时刻；现有前端的当前TJ等时筛选尚未接入新约定，因此本轮不宣称浏览器结果已验收。

## 实现与文件

- observe_predictions.py：保留原签发/评分算法，补充结算时刻与实测UTC。
- observe_runtime.py、prediction_view.py：正式账本成功提交后维护60分钟紧凑G2读视图，保留原prediction_id；5秒节奏和原observer复用。
- web_publication.py：实时快照与独立只读分页查询分开；正常结束保存正式终态快照。编码、socket和补取不进入采集回调。
- Web Python state/source/predictions/server：删除solver、生成预测与匹配实测逻辑；按修订补取、覆盖、按后台评分给出API统计；当前展示资格与历史评分分开。正常结束后历史时间轴停在结束点。
- API schema、版本/候选清单和操作说明同步；已有Web预测测试改为验证接收协议，新加两条生产提交→真实socket→接收/API与60分钟/撤回验证。

## 本地验证

- [源码回归](pytest-source.log)：46 passed；[独立安装后端wheel回归](pytest-installed.log)：46 passed。
- [Web非服务组件](pytest-web-components.log)：61 passed，3 deselected；另未运行HTTP/SSE服务、CLI启动、Web安装测试文件。实际API handler在进程内调用，不创建Web监听端口。
- 独立审查员另行串行运行真实socket→State→实际API三种交付条件及原curve/advisory单例，共4 passed；没有collector或HTTP服务。
- [回放](replay.json)：5572条公共模型与原状态记录一致；1065条G2预测和1065条评分按原ID对应，两端355个起点。页面正式阶段集合1059条；provisional仍留档，不进入正式页面统计。相同筛选集合下再比较分数，不沿用先前Web自行计算的分数。
- 故障验证：发布队列丢帧、非读socket、Web状态丢失/重建、多页补取、评分修订去重、生产者新run/新publisher、设备撤回后旧预测不可复活、投影失败、发布线程异常退出、正常终态恢复。沿用原collector故障用例证明native/states/predictions/scores继续，原frozen mismatch用例覆盖新live/terminal入口。
- API当前参考、图中forecast节点和advisory使用同一资格；advisory剩余期限同时受forecast/model/protection约束。预测跨度不能充当展示TTL。

## 软件身份

后端候选清单68项，SHA256 `998eb8f1476bb44d373027cf8d5d7af61aa29eadc67e4026ca30758ae299f85b`；后端wheel SHA256 `03f90db7a03956ad90c4d612214d66d81209d24abe76b7f50c308bd39c0bfb86`。

Web源码清单68项，SHA256 `5831e6256770337be6578a8f48da29f432fec6fbaad6f19e58e7e30943efcb20`；仅源码身份，未构建、安装或启动Web。[安装身份核验](installed-identity.json)通过，target_environment_checked=false。旧sealed候选/发布物没有覆盖。

## 本地开销

[cost.json](cost.json)、[cost.log](cost.log)：每模式3次、每次10秒，独立进程串行；相同数值库预热。CPU包含本地假源，回调含原Consumer.on_record及快照成本；ledger-client每0.5秒补取。测量时未并行本任务的测试或采集进程。

| 模式 | 单核CPU中位数 | RSS采样峰值中位数MiB | 回调均值中位数ms | 回调P95中位数ms |
| --- | --- | --- | --- | --- |
| 发布关闭 | 2.353% | 71.95 | 0.953 | 2.547 |
| 开启无人连接 | 4.325% | 72.25 | 1.206 | 2.707 |
| 开启但实时客户端不读 | 4.262% | 72.62 | 1.183 | 2.536 |
| 开启并订阅预测账本 | 4.770% | 72.34 | 1.158 | 2.362 |

12次均无原生/模型丢帧、模型错误或发布错误，线程正常退出；短测含调度波动，只证明本地开销量级，不能外推N305的CPU/RSS预算或长稳。

[完整窗口组件测量](window-cost.json)、[复现脚本](measure_window.py)：使用实际回放中最长的条件元数据形状生成一小时规范账本，未运行模型或设备；只测新增预测视图与Web预测缓存，不包含已有原始/模型历史或整进程RSS。

2160条预测、17页；最大JSON页 196945 字节（低于512KiB），正常终态 3300166 字节（低于4MiB）。视图+Web预测缓存的递归Python对象大小约 12.04 MiB；补取阶段tracemalloc峰值 7.88 MiB（包含新接收缓存，不应与前值相加），JSON/缓存处理 381.1ms，含tracemalloc追踪开销，是本地组件参考值，不是实际HTTP或现场延迟。

复现：

```text
PYTHONPATH=experiments/mainline_observe_v2/src /private/tmp/tto-publication-env/bin/python -m pytest experiments/mainline_observe_v2/tests -q -o asyncio_default_fixture_loop_scope=function
/private/tmp/tto-publication-env/bin/python experiments/mainline_observe_v2/scripts/validate_publication_replay.py --run evidence/formal-collection-20261013/run-2026-10-13T022246.369032_0000-c1a1bd6a --output /tmp/FRESH-REPLAY
/private/tmp/tto-publication-env/bin/python experiments/mainline_observe_v2/scripts/measure_publication_cost.py --output /tmp/FRESH-COST.json
/private/tmp/tto-publication-env/bin/python evidence/backend-prediction-ledger-20261023/measure_window.py --replay-session /tmp/FRESH-REPLAY/session
```

测试解释器仅本地安装了后端wheel；复用现有固定数值依赖及pytest/jsonschema插件路径，Web源码通过本工作树导入，没有安装Web包。

## 最终独立复审

结论：**可以推送**，限本地Python接收与进程内API验证。审查员独立运行4项接收/API与建议期限用例，并核对最终源码/安装回归、Web组件日志、回放、12次成本样本、完整窗口大小及两份68项身份清单。复审发现的advisory期限、读视图故障隔离、发布异常退出的终态认定已从根因修复；新补取/终态入口同样检查固定模型/spec。对应强化原有用例，不新增备用计算、磁盘重扫或重试读视图。

另核对本轮backend_scoring回放摘要与PR #16的原基线完全相等；冻结模型、research、frontend、static的diff为空。没有把本地组件结果当作浏览器、设备或部署验收。

## 边界与未验证

未验证浏览器、Cloud前端集成、Linux CPython3.10、N305 CPU/RSS与权限、长期运行、部署或现场表现。异常进程退出可能没有正常终态快照，保留已落盘账本，不伪造最终评分或自动续接旧观察器。全轮档案留在原session，页面补取限定本次观察最近60分钟。

实时发布可丢弃；账本读视图来自已提交记录，丢帧后通过修订游标补取。发布/查询失败不影响既有采集与正式记录。查询客户端最多与发布客户端共8个处理任务、每页128条且512KiB以内，慢查询/补取不能占用记录器锁。完整60分钟组件内存/补取量级见上；现场预算仍未验证。
