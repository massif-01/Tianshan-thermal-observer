# TTO Web v1 适配基线

2026-10-20；本任务目录 `work/webui-v1` 是原仓库内独立工作目录。未切换/覆盖原工作区；不使用public main冒充当前候选。

- 原Git HEAD：`97546ba3b403c02d1b9f81aa9fa50276355a4fd3`，原工作区大量未提交修改均保留。
- 实际复用：本地 `evidence/fixed-anchors-closeout2-20261019/candidate/tto_field_candidate-0.2.4+closeout.2-py3-none-any.whl`，完整SHA与各源文件身份见 `baseline-identities.json`。`cpu.2`存在但不作为本次热模型或采集行为升级。
- `tto.collector.collect`拥有唯一native `engine_for(record_schema=2)`；`engine.process`只执行一次。`CommunicationBridge.PreparedEngine`仅复用结果；`SavedStream.feed`与`ThermalObserver.step`属于相同拥有者，冻结theta和spec不改。原外层现场clock `clock.observer_input_mono_s/generated_at_mono_s/model_consumable_until_mono_s`提供真实时钟；内部`offline_virtual_observer_clock`文字不作为时钟依据。
- 本次standalone observe复用同一组class，发布外层host-monotonic时刻，Linux `/proc/sys/kernel/random/boot_id`约束同主机时钟域。macOS受沙箱限制不能读取boot identity，仅自建测试显式设置`TTO_WEB_TEST_BOOT_ID`且强制`test_replay`，不能借此接live。
- 公共排他锁：原生`/tmp/tto-observer-UID.lock`（flock，不删除inode）。原collect/shadow、field和新observe使用同一锁；field原另有`/tmp/tto-field-entry-UID.lock`。未参与此锁的其他用户/旧软件不能并行observe；操作卡明确要求同一用户，已有现场程序优先follow。
- 新增发布入口：`tto-web publish-field`把经过原field授权校验的运行入口接入只读发布钩子，不重做quality/observer。descriptor指向同目录`publication.sock`，唯一publisher持`publisher.lock`。生产者回调只往8项deque插入，Web follow只读有界Unix流，0设备读取。未扫mtime或最新run目录。
- observe使用原网络调度与源TTL（fan 1s/temp 5s、fan raw 2.5s、temp raw 7.5s、WS/NVML原源期限）；新增可选continuous等待及MemoryJournal，不写无限raw日志。不改原默认有界collect。continuous诊断统计deque 4096项，projection quality保留128项。关闭Web只停止其创建的observe；follow关闭不停止外部field。
- 源→DTO：TJ/CPU/GPU/SoC温区原值；两rail current mW/1000→W，average独列平均窗未知；逐核usage/freq保留%/MHz，在线有效核心均值/最大值注明覆盖；RAM/SWAP保留原MB；NVML独立sampled_at/age/timeout，重复缓存不得续期限；duty使用原successful_duty及raw_valid；target_duty另列；主板flags/mode/gain/slope/predicted_temperature/cooling_response经明确allowlist。
- I-02显式撤销优先于projection旧TJ缓存；新invalid不回捞旧valid；公开ref为run别名+摘要。header/binding/SSH/prompt/绝对路径不发送浏览器。
- RPM：附件核对摘要记录的2710份原档rpm=0/running=true，无独立测速valid。候选原报数在last_observation展示，当前value恒null/status unverified，不推断停转，不插入demo RPM。
- 冻结预测：原`observer-spec.json.evaluation`规定Tf锚定当前有效TJ，Ts/E来自当时observer；复用`ThermalObserver.mean_step`的精确矩阵指数；15/45/90 HOLD同两rail与conditional_inputs。每个新有效TJ起点最多1Hz；origin/issued/target独立，输入截止不借未来信息。标签窗同epoch目标之后（含）首个有效accepted TJ，最多+2s。旧Ridge评分不作为该provider成绩。
- 能力限制：standalone observe没有任务登记，task与并发为null；field hook消费原runner登记事件，区分客户端在途/槽位与未知服务端状态。未提供实时demand参考、可信测速或设备匹配的本地曲线。保留C/D/E与建议区域；不猜百分比、任务状态、置信度、物理Ts或环境温度。CURVE-REFERENCE-v1仅配置有效hash/绑定/设备/config_sha256证据时计算，不自动查询设备曲线，不增加阈值。
- 软件候选新增`1.0.0rc1`独立wheel，原研究permission/deployable字段仍保留，软件安装授权不被用作设备动作授权。服务默认本机59009，LAN需显式origin与只读口令；业务API只有GET，登录/退出是唯一POST/DELETE。

- 资源策略：无React/Node常驻，无数据库/原始日志复制；数值库在来源就绪时加载、CLI限制数值线程为1。浏览器每秒增量拉取曲线/预测，统计分母仍为整个选择窗口。history最长60分钟且每序列18002项，预测11070项、标签随出队清理、事件1000项、显示队列8项、SSE最多4客户端。没有降低原源频率或更改TTL。
- 快照到期检查维持0.1秒，新数据/1Hz显示/到期才重建，减少无条件深复制；GET snapshot按请求时刻刷新，不让静默源延长资格。
- follow的Web数值对象只调用冻结mean_step做预测传播，不调用step/KF，不创建第二份估计更新链。
