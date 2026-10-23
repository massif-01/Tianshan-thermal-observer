# TTO CLI 使用卡

所有输出目录/文件必须是新路径；不会覆盖旧证据。`--help/--version` 不读配置、不联网。默认doctor离线。只有collect、shadow、带--live的doctor联网，均有duration上限4小时；填写端点不等于授权助手运行。`doctor/collect/shadow` 可用 `--deployment-record 本机JSON`登记用户提供的最终包/配置证据；不远程验证，未完整填写仍为未核对。

|命令|输入|输出/条件|
|---|---|---|
|doctor|--config，可选--model|配置、模型完整性、周期证据；不联网|
|doctor --live|--config --duration 180|两路限时原始记录和数据入口质量；安装包身份仍需用户记录|
|collect|--config --duration 1800 --episode 短场景词|新run、原始对象、质量、基线预测及追加评分|
|summarize|--run|控制台JSON，质量、缺项、资源和下一步|
|split|--runs 多个run --output 新目录|dataset.json+split.json冻结；单过程可加--exploratory|
|train|--dataset --split --output 新模型.json|CPU子进程、冻结JSON及.resource.json；不自动激活|
|evaluate|--dataset --split --models 新模型.json --output 新目录|一次性测试登记、四方法完整比较、JSON/Markdown/HTML；省略models仅基线|
|report|--run --output 新目录|JSON/Markdown/自包含HTML，无CDN|
|shadow|--config --model 真实冻结JSON --duration|与collect同采集器，只观察；模拟模型拒用|
|demo|--output 新目录|完全模拟的采集、切分、拟合、评估和报告；所有页面显式模拟|

配置优先级：显式CLI > 以下TTO环境 > JSON > 内置默认。非法被选值拒绝，不回退；未知JSON键报错。时距、方法、特征版本、安全策略冻结，不能通过改配置绕过合同。未实现的扩展不静默接纳。所有源/配置变更需新run、分段和评估。

|环境变量|字段|CLI覆盖|
|---|---|---|
|TTO_ORIN_URL|orin.base_url|--orin-url|
|TTO_TIANSHAN_URL|tianshan.base_url|--tianshan-url|
|TTO_DATA_ROOT|storage.data_root|--data-root|
|TTO_DURATION_S|run.default_duration_s|--duration|
|TTO_SOURCE_INTERVAL_MS|orin.source_sample_interval_ms|--source-interval-ms|
|TTO_SOURCE_INTERVAL_EVIDENCE|orin.source_interval_evidence|--source-interval-evidence|
|TTO_ORIN_HEADERS_FILE|orin.headers_file|JSON配置；本机文件600权限|
|TTO_TIANSHAN_HEADERS_FILE|tianshan.headers_file|JSON配置；本机文件600权限|

doctor无duration覆盖时用run.doctor_duration_s=180；collect/shadow用生效的default_duration_s。TEGRASTATS_*、.env、任意环境变量不参与TTO。凭据内容、完整环境及模型服务日志不进入manifest/HTML，错误只保留类名或不含选中值的配置解释。

当前工作区可直接用 `.venv310/bin/tto`；转移到N305按README创建本机隔离环境并安装交付wheel，不依赖此绝对路径。依赖准备可使用本机wheelhouse；`scripts/reproduce_offline.py` 从已安装wheel运行，仅loopback测试，不连接设备，不运行tegrastats、SSH或服务管理工具。

0.1.1返修：`split/train/evaluate`共同检查完整跨run时间/过程顺序；不连续复用过程名需确认，不能静默回训练。旧dataset缺时序锚点时明确拒绝严格未来留出，派生路径必须新建，真实测试使用状态不重置。

`evaluate`输出基线/M0/M1三层同起点结果；`report --run`自动区分采集质量与已保存shadow。旁路统计不接收新模型参数，不重新计算历史预测；缺日志或尚无评分会明确提示。详见`R1-R4-repair-contract.md`。
