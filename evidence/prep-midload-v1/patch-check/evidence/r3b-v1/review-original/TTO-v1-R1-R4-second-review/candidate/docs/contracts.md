# TTO v1 数据、模型与切分合同

依据：TTO-PLAN-v1.0；主方案是本轮实施范围，handoff/reference 仅追溯，不执行旧 WS/风扇修复。

## 两路输入

Orin 使用 python-socketio 5.13.0 / Engine.IO 4 客户端，path `socket.io`、namespace `/`、事件 `tegrastats_update`。默认 WebSocket；显式选择 polling 才允许必要 GET/POST 传输。客户端没有业务 emit/call，也不监听模型服务日志。指定 origin 之外的请求及重定向被拒绝。传输接收上限为业务64KiB加1KiB协议空间；JSON对象重序列化再检查64KiB，不称原始 WS 字节抓包。库的底层网络缓冲仍有开销，不声称应用层上限等于零额外分配。

ESP32 仅 GET `/api/v1/fan/status`、`/api/v1/temp/status`，HTTP200和整数API code=0共同成功。fan默认1秒，temp默认5秒，一个在途；初始同时到期fan优先，此后最早截止优先避免temp饿死。完成后跳过漏期，不并发追赶；统计漏期和HTTP RTT，RTT不是控制耗时。更改配置只能放慢轮询，不改源采样。

fan：从 `data` 单对象或 `data.fans` 唯一选择 `id=0`。`duty_valid=true` 且有限0..100的 `duty` 才是成功PWM；0有效，`target_duty=70,duty=37`只使用37。未知输出、故障、保护、失温、非AUTO保留记录并撤下正常模型资格。RPM保留原值但不进入特征。

已核对固定参考及本地源码：`temp.status` 用 `temperature_c/temperature_01c/valid/timestamp_ms`，附 `manual_mode/active_source/preferred_source/bound_variable`；另一状态形态 `current_temp_c/current_valid/current_timestamp_ms` 显式识别。ESP32更新时间属于本机时钟域，不能与观察器UTC相减。正常资格要求新鲜fan、有效非测试temp、来源agx或绑定variable；绑定/模式/故障/测试变化断段。温度状态最长年龄 `max(7.5秒,temp周期+请求超时)`，是观察资格，不延长源TTL。

输入meta schema1、collector_receive定义、running/fresh、正seq、非负年龄和正过期界限明确检查。未知版、0seq、缺TJ或错误数值对象只诊断。完整样本身份 `source_id,stream_id,seq`；新身份同数值仍接受，重复身份不增加起点，源fresh=false立即断段，重复不能恢复，需有效新身份。

重复的本地年龄下界推进为 `max(已有下界+经过单调时间,新报告年龄)`，不包含未知在途时间。UTC跳变不参与年龄。旧连接epoch/退休stream拒用，seq倒退拒旧行并隔离原段，之后新seq可重新预热；同身份数值冲突隔离原段、重复不恢复。离线建模隔离已知冲突/倒退段的既有标签，不能取最后对象悄悄替换。最多记128个源生命周期，异常风暴达到上限停止观察器。

## 因果特征、标签与资格

每份有效新TJ进入同一 Engine/Features；每5秒最多一个真实起点，不能根据缓存插行。起点存不可变特征和原始引用，fan/temp只有当时已返回的快照能进入，`available_at=origin_t`。正常范围的连续模型历史预热180秒，B0无需预热，B1需要30秒窗口内至少10秒跨度。

M0：当前TJ、5/15/30/60/120/180秒as-of滞后差、10/30/120秒左侧持有时间加权均值差与简单端点斜率。窗口不跨许可空白。180秒边缘最多保留 `min(5,max(2,2×源周期))` 秒的因果as-of锚点；它只实现允许的滞后容差，切分使用实际最早引用并至少180秒支持区间，不能把锚点漏出purge检查。最多4096历史样本，超限停止观察器。

M1另加成功duty当前/30/120秒均值/30秒差与gain；可选测点相对TJ及30/120秒均值、有效核心聚合usage/freq和报告核数、GPU忙碌百分比、三条独立current rail W。GPU名gr3d_freq不是MHz；CPU核不依赖物理编号。缺失不补0，rail须声明mW，未知rail不自动进入。GPU温度缺失正常。可选原始字段的三个变换作为一组，仅训练完整起点可用率≥95%且当前值非全常量才选择。全列最多54，少于64限额。

各h独立直接拟合ΔTJ，不读取未来负载/PWM。每episode等权、有效起点因果时间权重最多5秒；加权均值/方差仅在共同训练起点拟合。Ridge SVD，alpha=lambda×sum(weights)，lambda四项0.001/0.01/0.1/1；按验证45秒episode宏平均MAE选择，≤0.01°C差选更强正则，同lambda用于三个h。M0/M1共同训练及验证起点公平比较，另给M0更多可用起点覆盖。BLAS线程1，独立训练子进程10分钟/2GiB监测，超限只终止它自身。

首个同段新样本在目标时间或之后≤`min(5,max(2,源周期))`秒作标签；不找目标之前旧值，不填充真值。断段/异常期间不评分；未来数据只改变追加评分。待评分起点最多20个，每个h分别到期，结束保留cross_segment状态。

## 冻结与报告

run不是episode。默认每轮episode来源未知，明确用户场景分组后仍标operator_named_process。至少三个不同时间完整过程，按早到晚整体分组；五个以上保留至少两个测试过程。探索单过程保留支持区间空白，报告仅同过程外推。切分冻结源文件SHA、原始引用、范围、来源、分区和丢弃理由；所有分区无相同引用、同run支持区间不重叠。标签支持到90秒加容差，最长滞后锚点纳入实际支持。完整性SHA是可重算校验，不是数字签名。

模型JSON≤5MiB，有合同、列顺序、缩放、范围、三组系数、训练/验证/切分哈希。只读固定模型，不在线训练或热替换。选中字段缺失M1不可用，降级实际方法另记；M0/基线不充当M1。外推不裁剪，有范围标记，无自造置信概率。

评估预先写test-used登记，失败也保留使用记录。比较四方法共同可评分交集，覆盖另外列总起点、预热、输出、fallback、无标签、跨段、可评分数及每episode/五分钟区间。MAE/RMSE/P95/偏差/欠预测/过预测均有全量及episode等权汇总，15/45/90秒全保留；阶段/≥60°C区间只是显式诊断阈值，不改控制。固件45秒趋势单列诊断，不是标签或风扇因果效果。相邻样本不视为独立实验，不给未经分组的总体置信区间。

## 资源与存储

队列256项/8MiB；对象64KiB；单原始文件64MiB；单run2GiB（包含元数据；预留最多8MiB用于有限收尾）；保留磁盘1GiB；最长4小时。达到预留边界提前停止原始日志，汇总及索引仍受整个run上限约束。记录不循环覆盖，文件轮转不制造episode。丢弃标记写进原始对象记录，实时和回放共用同一断段。写盘在单个线程顺序执行，网络回调只打时间、检查大小、入队；断网重试默认1..30秒抖动，总尝试10次。单用户本机锁在不同数据目录也阻止两路重复连接，进程退出自动释放锁。文件系统不返回的内核I/O不能靠Python保证即时中断，正常慢盘通过有限队列标缺段或停止；不写“所有磁盘故障均已实测”。

资源监测100%=一个逻辑核，记录RSS、CPU、峰值/P95、消息率、漏期、队列和丢弃。实时prediction_ms包含特征与记录写入，独立推理benchmark单列。当前主机模拟与N305预算分列，未测N305不预报通过。

官方实现参考：[python-socketio](https://python-socketio.readthedocs.io/en/stable/client.html)、[aiohttp](https://docs.aiohttp.org/en/stable/client_reference.html)、[Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html)。版本以依赖锁与实际测试为准。

2026-10-11：0.1.1返修后的跨run时间校验、三层共同集合及实际旁路报告，以`R1-R4-repair-contract.md`补充为准；其余冻结合同不变。旧四方法交集不再是所有价值判断的唯一入口。
