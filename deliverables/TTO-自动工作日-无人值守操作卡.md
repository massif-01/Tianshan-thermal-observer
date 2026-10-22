# 自动工作日：一页无人值守操作卡

**当前仅准备，未授权上线。用户无需2小时值班、22小时使用、YET或录像。**

**一次批准**：具体设备/热配置、主机/源端点、原驻留模型、无已知其他任务的使用窗口、目录/磁盘、程序/计划SHA、≤24h、≤600提交/≤5h客户端在途和停止负责人。只读与负载许可独立；首台自动2h检查，同窗最多24h、首批≤3台，不另加60秒。

**安装准备**：在新目录放本程序，保留原observe.2与全部旧环境；用原Linux x86_64/Python3.10、21个锁定依赖严格`verify-install --target`。不启旧execute。填configuration.template.json，使用新registration/session、observe preview的新只读grant、固定模型请求配置（stream=true/sampling={}）、随包executor/frozen-plan.json及新输出目录。安装不计入观察经过时间。

**预览与独立许可**（在program目录，绝对路径）：
```sh
"$PREFIX/bin/python" program.py preview --config "$CONFIG" > "$PREVIEW"
"$PREFIX/bin/python" program.py unit --config "$CONFIG" --grant "$LOAD_GRANT" --output "$UNIT"
```
根据整窗批准填写preview的负载grant模板，身份/SHA及带时区的起止精确对应。unit仅生成文本；获准后由既定推理执行方启动用户服务，并确保服务能在终端关闭后持续运行（必要linger纳入同一次许可）。Restart=no；无需Codex/浏览器在线。禁止设备使用self-owned-loopback测试标志。

**机器自动执行**：0—2h背景/自动检查；2—6h稀疏；6—8h讨论；8—9h有限批处理；9—10h回落；10—18h长休息；18—23:30混合；末30min无新增。386个机会仅单路，错过/暂停不追赶；沿用256 token/30秒协议。检查未保存不提交；真实条件暂缺暂停、连续60s停负载，观察可继续并注明模拟未完成。模型tracking或预测输赢不是许可；原TTL/5s确认/保护不变。

**随时控制**：
```sh
"$PREFIX/bin/python" program.py control --output "$RUN" pause
"$PREFIX/bin/python" program.py control --output "$RUN" resume
"$PREFIX/bin/python" program.py control --output "$RUN" stop
```
resume只限原窗且请求线尚未终止；STOP禁止新增，在途最多剩余原30s自然收尾。未知结束不恢复，不把客户端断开当GPU结束，不凭自身inflight=0判断整机空闲。

**到期与失败**：观察运行至86280s，预留120s停止/归档，许可UTC与单调截止取更早值，不延长。保存summary、自动检查、两进程资源、原始observe、请求/同run相邻事件及索引；observe内业务计数可仍unknown。归档最多60s且受剩余窗口约束，失败保留部分/错误，不重跑。仅清理本程序及子进程，不动模型/源服务/风扇。原observe预算不变，新增驱动与合计预算详见README；磁盘建议至少18GiB并计驱动证据≤256MiB。

**交回/回退**：查看summary与原生files索引，保留异常和全部数据；停止归档后保留新旧目录，不自动重开旧服务。未来按“真实设备＋自动构造负载”报告总体及分阶段覆盖/尾部，不称自然用户分布，不自动重训。
