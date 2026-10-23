# observe 发布与后台统一预测验收

## 当前版本及范围

PR #16：唯一 observe 采集/投影/模型/预测账本，Web follow 只展示；发布是有界可丢弃旁路。运行代码位于 `experiments/mainline_observe_v2/src/tto_field/`，接收与页面位于 `work/webui-v1/`，契约见 [前后端接口](../后台统一预测-前后端接口约定.md)。

本地清理候选为 observe.7 / Web rc9：合并初始化与换发布者时的预测状态重置；复用同一个 forecast 默认值；移除无用导入、无效局部变量及重复构造；把重复的采集保全测试纳入现有故障矩阵。没有删除缺口撤回、身份校验、有界队列、超时或异常隔离，也没有新增兜底路径。旧Web的observe入口仍可通过配置使用，其发布器和编码路径为兼容功能，保留，不将它们当作死代码删除。

N305 实际安装并短测的仍是 observe.6 / Web rc8（提交 `01caaa52`），目录 `/home/rm01/TTO-unified-rc8-20261024`。本轮清理未连接、安装或重测 N305，不能把 rc8 现场结果称作 rc9 现场验证。

## 验证结论

清理后：后端49项、Web源码77项、最终安装wheel77项全部通过；5572条状态/编码、1065条G2预测及评分按ID一致，355个起点、1059条正式页面记录保持一致。两个安装清单各68个文件与最终源字节核对一致。命令沿用 `pytest experiments/mainline_observe_v2/tests`、Web的 `pytest tests` 和 `validate_publication_replay.py`；日志只保留本地，不再逐轮复制进PR。

最终独立复核：可以推送，限本地清理范围。初始化、同一发布者重连、新发布者切换、终态历史和失败状态仍由原生命周期回归覆盖；未发现本轮清理引入的阻塞问题。实际N305版本及未测范围如下。

rc8 的两项现场缺陷已经修复并验证：正常停机保留真实实时 epoch，并单独指定最后一组正式历史身份；最终文件先保存成功再登记 ended，失败则登记 publication_failed，页面明确提示最终结果未确认。

| rc8 实际检查 | 结果 |
| --- | --- |
| N305 正常180秒 | 唯一采集器/观察器，575帧无发布/模型错误或丢帧，poll_missed=0 |
| Web 带SSE停止、断开10秒、重启 | 退出0.114秒；后台持续落盘；原21个ID及值/时间恢复 |
| 正常终态与冷启动 | 实时epoch2、历史epoch1；102条正式预测/评分逐ID一致；页面刷新后评分保留，当前预测撤回 |
| 页面统计 | 15/45/90秒成熟样本31/25/16，MAE/P95/最大低估与原scores重算一致；另6条provisional仅归档 |
| 独立45秒最终写入故障 | 真实文件路径冲突产生IsADirectoryError；原/新Web及页面刷新均明确失败且不宣称完整，原始账本正常落盘 |
| 收尾和归档 | 两场各21个会话索引项一致，完整84文件归档取回本地逐SHA核验；本次进程/端口/SSH关闭，旧服务inactive、旧配置未变 |

rc8 正常场单核CPU采样均值：后端7.24%、Web7.87%；RSS峰值77.31/49.02MiB。没有同机关闭发布的对照，不能宣称增量开销为零。短测处于低负载，不作模型能力结论。

## 历史保留与限制

PR 不再重复提交各轮日志、安装清单、回放JSON、一次性现场脚本和截图。88份原件完整保存在本地主工作区 `evidence/pr16-history-20261024/validation-history.zip`，逐文件SHA核验；ZIP SHA256 `e5d8517fa132e031d1ee1e485aa7b8c0db0c916af2e6be0bcafecd6b94bea15f`。同时仍可在祖先提交 [4ddcb6a3](https://github.com/massif-01/Tianshan-thermal-observer/tree/4ddcb6a3/evidence) 查看，不改写Git历史。

[rc8完整现场报告与截图](https://github.com/massif-01/Tianshan-thermal-observer/blob/4ddcb6a3/evidence/unified-web-rc8-20261024/n305/README.md)；[rc7未通过记录](https://github.com/massif-01/Tianshan-thermal-observer/blob/39e2d3de/evidence/unified-web-rc7-20261023/n305/README.md)。rc7终态查询缺陷、旧24小时缺原最终summary/index、安装未完成时提前启动脚本的预检失败均保留，不改成通过。完整N305原始短测记录另存本地主工作区 `evidence/n305-unified-rc8-20261024/short-test-records.zip`，SHA256 `1829ccb2c3e62ca144c67ce4dce2683612216fd07a587723798e7c7823b5147e`，远端原件也保留。

仅恢复最近60分钟最后一组正式历史，不是整轮历史数据库。若整个发布目录无法写入，失败登记也可能无法持久化；后台错误和实时资格撤回仍有效。未测断电、长期高负载或发布增量预算。本轮不合并PR。
