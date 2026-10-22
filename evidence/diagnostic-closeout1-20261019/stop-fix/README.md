# 停止时刻局部修订：closeout.2（未部署）

根因：runtime观察到collector/共享stop时，Scheduler.now仍是上一tick；旧stop把事件和drain起点记早。现在所有stop都必须显式传入当前单调时刻，runtime传本次循环now，tick内部传当前self.now。拒绝回退时钟；重复通知不重置首次停止时间/原因。没有改计划、TTL、保护、模型或Requester。

`stop-clock.patch`以已封存closeout.1的source为基线；`changed-source`为局部完整文件；新wheel与42文件清单匹配，目标Linux/Python3.10安装身份在target-identity.json。本轮N305仍运行原closeout.1诊断，未安装该小修。

确定性回归检验：stop事件从旧2.000s纠正为实际观察2.125s；drain从2.125s起算；重复通知保留首原因；省略/回退时钟拒绝；内部user-stop时刻正确。基线失败日志保留。真实Requester仅访问自建127.0.0.1服务，检查采集退出后自然收尾、无停止后调度或协议提交、事件时序单调和session/task全部关闭。原断言保留并加强，没有以事件行序替代时间断言。

初次本地无隔离构建因缺setuptools失败，随后使用独立构建环境成功；一次离线容器重复执行使用了已有输出目录而拒绝覆盖，失败日志保留，改用新输出完成验证。这些均不是现场诊断重跑。

本包不重复依赖wheelhouse；需要以后安装时，使用原closeout.1归档的相同依赖，单独替换新版本候选wheel并重新生成wheelhouse SHA清单。必须另获现场安装许可，不在本轮运行目录热改。
