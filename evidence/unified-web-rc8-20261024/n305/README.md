# N305 observe.6 / Web rc8 短测

结论：本轮两项缺陷的真实安装短测通过。安装在 `/home/rm01/TTO-unified-rc8-20261024`，后端/Web 各自独立环境，`--service none --access local`；两场只读短测结束后停止全部本次进程和 SSH 转发，保留软件、原始账本及故障现场。旧安装、旧24小时记录与 rc7 未通过的结果未覆盖；未合并 PR。

正常 180 秒：唯一 collector/observer，180 个合格 TJ、575 帧发布，发布/模型/回调无错误或丢帧、poll_missed=0。Web 带 SSE 退出0.114秒，断开10秒时 states/predictions继续增长，恢复原21个ID及值/时间。正常结束实时 source_epoch=2 保持真实；history_identity 指向真实有正式预测的 epoch=1，三组各34条，共102条正式预测/评分与账本逐ID核对一致。15/45/90秒成熟样本31/25/16；独立从原始scores重算页面MAE/P95/最大低估一致（见 archive-verification.json）。账本另有6条provisional，保留归档、不进入正式页面统计。Web 冷启动后完整记录及统计一致，真实浏览器刷新后评分仍显示，当前预测撤回。

故障 45 秒：在全新 pub-failure 下创建 `predictions-final.next/` 目录，实际触发 IsADirectoryError，只阻断最终文件写入；没有修改安装代码或用假DTO。后台采集正常结束、预测/评分已落盘、21文件索引完整，发布错误被记录，描述文件 publication_failed=true/ended=false/prediction_final=null。原 Web 和全新 Web 都识别failed，API不宣称完整；实际页面刷新后明确显示“发布失败 · 最终结果未确认”，三组当前预测均为破折号，无pageerror。

数据保真：源码录制回放与真实现场分别核对，发布未改写预测值、ID、时间、来源或评分。预测口径：浏览器不预测、不选实测评分；页面统计与后台同组正式记录一致，后台含provisional的全账本汇总不是页面分母。180秒短测处于低负载，误差不是模型能力结论。

资源：正常场后端/Web 单核CPU采样均值7.24%/7.87%，RSS峰值77.31/49.02MiB（含启动、网页访问和重启）。无关闭发布的同机对照，不能据此给出增量成本；没有新增采集器或模型，正常场未见丢帧/漏轮询。终态历史组仅在结束编码时选择，错误路径只有一次失败登记，无重试循环。

归档：正常/故障各21个会话索引项已核验；完整记录ZIP共84个文件逐SHA核验并取回本地，含两场原始账本、发布状态、日志和终态响应。ZIP SHA256 `1829ccb2c3e62ca144c67ce4dce2683612216fd07a587723798e7c7823b5147e`；本地位于主工作区 `evidence/n305-unified-rc8-20261024/short-test-records.zip`，远端新prefix同名。Git只保存精简报告、验收脚本、截图和校验结果，完整数据不重复提交。

过程记录：短测脚本最初在 Web 安装尚未完成时提前运行，读取配置失败，未启动采集或Web；原失败保留于归档validation/preflight-before-install-completed与本目录preflight-script-failure.json。等待安装完整结束后另建会话完成验收，未删除或覆盖失败记录。

限制：未测断电/文件系统完全失写、长期运行或高负载下的增量资源。整个目录不可写时，失败描述也可能写不出，只能保留后台错误和撤回实时值，不能保证页面持久提示。页面恢复范围为最近60分钟最后一组正式历史，不是整轮历史数据库；旧24小时缺原最终summary/index的问题仍保留，未改成成功结论。
