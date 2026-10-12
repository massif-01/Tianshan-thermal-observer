# Orin / Thor / CURVE 候选合同

共同依据为`TTO-PLATFORM-CURVE-v2.0`最终方案。TTO 0.2.2、tegrastats-api 1.1.1；本轮限于本地与离线验证。

远端设备树compatible以NUL分隔，只有精确的`nvidia,tegra234`、`nvidia,tegra264`分别确认Orin、Thor。未知或冲突不猜型号。源telemetry_meta维持schema1；新增platform和gpu对象各为schema1。

统一gpu以schema_version标记。缺标记且没有任何新增字段才是legacy。新版缺项、错误版本、错误状态或新旧同源百分比冲突，只撤下该GPU输入，不补0、不退回旧值。有效0%保留。封存平台或GPU在同一stream/seq下变化，沿原身份冲突规则隔离整段；报告沿R3b调用链应用隔离，不改写历史日志。

Thor的官方nvidia-ml-py绑定为可选extra，版本按WS最终候选依赖锁核对。NVML只在明确启动的Thor reader线程调用；服务实现、依赖与退出证据由WS会话单独交付，本TTO包不替服务验收。单GPU索引0及UUID；多GPU、MIG、不支持或初始化失败明确不可用，初始化失败需后续新stream再尝试。单次读取失败可在下次周期恢复；不并发追赶。停止等待reader退出后才释放NVML； native调用不返回时退出报错，不并发shutdown。未做真实驱动兼容或设备查询。

TTO GPU年龄采用源封存年龄＋外层样本年龄，再增加本机单调历时。重复seq用既有下界推进与新下界的最大值，不生成起点。GPU历史左侧持有到有效期限截止，30/120秒窗口缺口不回填。GPU失效只影响选中gpu_busy组的M1；M0及未选GPU组的M1继续按自身合同判断。

原功耗current的mW转W、CPU聚合和TJ定义保持。Orin使用原rail/soc0/1/2；Thor保留vdd_gpu、vdd_cpu_soc_mss、vin_sys_5v0和soc012/soc345真实名称。四个静态profile的最大列数54、53、51、50，不建立全平台并集。

normal_auto维持原义。CURVE的control_eligible仍要求成功PWM、启用、无故障/保护/失温、新鲜fan/temp、有效且可信的实际温度来源、非人工模式；不要求gain。CURVE不输出AUTO固件预测、控制温度或自适应状态作为有效诊断。

input-profile.json在首次确认时写一次，Journal先保存它再写预测，文件计入预算及SHA索引；每起点保存当前profile、scope和input合同摘要。暂缺GPU周期及首次UUID补全不算设备切换；两次已知周期/UUID不同、平台或AUTO/CURVE切换留下永久mixed标记。正式建库、加载、切分检查、训练和评估入口都核对身份。unknown及无资格起点保留历史分母，不能参加已知profile的正式评分。

新生产采集和CLI demo显式用record/input/feature/model schema2。历史Journal/Engine API默认schema1，供冻结旧夹具与旧合同回放；生产入口通过engine_for显式分派。声明schema2但版本组合缺失/冲突，报告保留拒绝原因，不能退回旧评分。配置文件继续schema1，defaults.json与power_current_rails不改，旧模型离线保留；新run不启用schema1模型。

旧run正常report仍使用旧段号、起点与引用。`report --diagnostic-input-v2`在新输出路径附加生产Engine新版输入诊断，不替换保存预测/评分。JSON、Markdown、HTML共用同一结果。source状态、当前有效性、配置来源、实际来源和模型证据分别显示。

安装器支持原0.1.2 Conda前缀升级，保存local.json、模型、run和上次安装身份历史；Conda base不改。候选包身份必须以新wheel和实际导入文件核验。现场有效ExecStart、override、NVML驱动能力、N305资源和模型收益均待用户后续安排。


按合并最终稿，新结构由platform字段或任一统一GPU字段标识。带platform而缺gpu版本也不能走legacy。只有完全没有这些新增字段的旧结构，才保留旧GR3D百分比（包括0）并继续标平台未确认。unknown.identification_source为null。

新增telemetry_meta.source_sample_interval_ms取实际源命令；TTO独立副本采用wire周期，不改原配置。非空人工值冲突时报configured_source_period_conflict，保留TJ、停止模型并拒绝正式冻结。GPU周期/timeout在选定后端临时失败时仍固定；Thor默认独立1000ms，Orin等于源周期。输入profile同时记录source_period_basis和GPU timeout。同key周期变化在duplicate前触发身份冲突；同stream新seq改变platform/源周期/GPU调度设置为lifecycle_contract_change，隔离原段、断段并永久标mixed，不把新鲜TJ删掉。后续恢复段仍保留。

GPU四状态按最终第4节组合校验，error/unavailable的值、成功UTC、年龄均null；stale保留成功UTC及真实过期年龄，值为null。UTC只追溯，消费端年龄仍用单调下界。普通GPU版本/类型问题只撤该GPU输入，M0及未选GPU组的M1按自身合同继续；同seq改写GPU是样本身份冲突，语义不同。
