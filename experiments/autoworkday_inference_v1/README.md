# 自动工作日请求线：离线交付

2026-10-22 · TTO-AUTOWORKDAY-REQUESTER-v1 · 未授权现场执行。

1. **交付内容**：`runner.Runner(clock, requester, plan, admission, emit, control)`、固定种子完整计划/8类非敏感任务、原样Requester和Adapter、实际emit样例及有限验证。总控在同一监督进程调用本组件；本组件不创建collector/热观察器、不轮询测量、不查询模型。具体接口见API.md。

2. **实际实现**：seed20261022冻结386个机会，单客户端、每请求256 token/30秒，最多600提交（失败/取消同样计数）、18000秒累计客户端在途。前7200秒背景、9—18小时回落/长休息、末1800秒无新增。忙碌/暂停/迟到的机会跳过，不排队追赶、不延长总窗。预留完整30秒再开始请求，限额更严时停止后续；不将不足预算改成更短超时。唯一Requester复用连接，休息不重载模型。pause不强断在途；STOP阻止新增，已提交者在原剩余30秒内自然收尾；队列中未提交者立即取消且不伪造提交/取消事件。未知完成停止后续，无恢复/重试。run不能再次调用。

3. **证据**：16项有限测试通过；使用与observe.2同一本地Python3.12.3安装prefix。完整24h虚拟钟+内存假SSE，实际原样Requester解析386份响应，386提交/386协议完成、1158个Adapter事件，峰值客户端在途1、累计1158秒，虚拟期末86400秒；墙钟约2.78秒。这不是24小时实测，也不是GPU在途/忙碌时长。实际日志在evidence/full-day/{protocol.jsonl,workload-events.jsonl,summary.json,receipt.json}；真实代码emit节选在sample-actual-emit.json。覆盖暂停/60秒有限等待、背景检查待定、STOP自然收尾、观察器退出、超时/截断未知、预算、尾部、忙碌无追赶及计划/身份拒绝。STOP排队竞态修前1条越界提交、修后0条的反例保留；最初测试严格相等断言对1毫秒轮询偏差失败的日志也保留，最终接受边界为60秒至下一次1秒检查，未放宽TTL。未重新跑历史事件/模型/O1/O2/CPU支线。

4. **限制与责任**：总控负责observe.2状态/保护/TTL/5秒确认/独立许可/2小时检查、资源/磁盘和生命周期；本组件仅消费allow/pause/stop。前两小时health_pending不消耗请求准入的60秒额度；明确stop在背景也生效。原observe.2 wheel不变，原execute不调用、不修改、不设formal=false。新profile前向替代旧“先停observe”接续：同一持续只读observe+一个外部Requester。observe业务计数可继续unknown；相邻workload_event流按真实session/native UUID/device/config/clock域关联，初始UUID未生成时不能伪造后启动。原Requester的4MiB单响应上限保留，总控磁盘预算仍优先于计划。此次测试是macOS ARM64/Python3.12.3本地候选，不能代替Linux目标验证、实际资源成绩、真实热数据或最终联合放行。

5. **交回后停止**：把本目录/API/代码身份交“实际安装与测试”汇总并做必要联合验证。总控保留前2小时自动检查、独立负载许可，24小时包括归档；其预留120秒清理的方案在86280秒令admission=stop，随后归档，不修改冻结时序。未来一次批准具体设备/会话/模型/计划/窗口及暂停方式才执行，不需逐阶段聊天确认。CPU12仍暂停，本轮0模型查询、0真实请求、0设备连接、0部署。预测器不读取冻结计划/seed/未来提示词，normalized事件只发布真实已到达部分；raw审计流包含计划时间，禁止送入预测器。

本目录是新独立候选，旧交付和源码均保留。`source-identity.json`列代码SHA、来源SHA和计划canonical/file两种SHA；`SHA256.json`列整个封存包成员身份。

离线复核（在本目录；不会建立网络连接）：

```sh
python3 -m unittest discover -s tests -v
python3 verify_offline.py --output /private/tmp/tto-autoworkday-new-fixture
```

输出路径必须不存在，避免覆盖证据。现场RealClock不可缩放；VirtualClock仅在fixtures/tests/verify_offline中。没有单独的现场CLI，唯一现场总控入口由测试线交付。
