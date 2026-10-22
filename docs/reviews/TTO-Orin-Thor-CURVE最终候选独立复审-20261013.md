# TTO / rm01OrinStatus 最终候选独立复审

日期：2026年10月13日。依据：TTO-PLATFORM-CURVE-v2.0 最终执行方案。

## 结论

**整体返修。TTO 有三项必须关闭的问题；rm01OrinStatus 通过本轮离线代码与交付复审，未发现独立阻断项。** 服务端现有候选不需要因这三项问题一起重构或重新做 GPU 实现。此次通过范围不包含真实驱动/NVML、现场部署、目标设备资源与真实模型效果。

此次以 reviewer 身份重新检查方案、实际源码、wheel、Conda 包及两份证据 ZIP，没有沿用上一轮“全部通过”作为审批依据。没有修改生产代码、安装脚本、测试或候选包，没有连接设备、安装升级、部署或 Git 发布。仅对三个具体疑点进行了最小离线复现，没有重跑全仓、防御 fuzz、故障组合或模型搜索。

## 被审身份

| 产物 | SHA-256 |
| --- | --- |
| TTO 0.2.0 wheel | b439128bef648fb7455572f0ab9e17c3d4d268d8d721c471db537858538e638c |
| TTO 0.2.0 Conda ZIP | d09adddecdf67e02ce760be858389944a8711da3acb6eb9150b9536fa56f6547 |
| TTO 复审证据 ZIP | 237f932f10b4d2137d24ec56ecb3b28b544b4b7bee6a1e8ba318b84da51ac1e2 |
| rm01OrinStatus 1.1.1 wheel | 2309c819e3d42887261db718f3a6149edbdde1fb877cb4d5151b43a663b3c338 |
| rm01OrinStatus 最小证据 ZIP | 1bd92e22dc0588d3a562a8aadb63a4fe3dd3f2827dbb36c5247482c99e587175 |
| 共同 producer fixture manifest | 59798e9e93fdc6b9968ef6f2e88847fdd238514c52ed43eb50f06d02432aacf2 |

独立逐项检查：TTO ZIP 的257项SHA、服务ZIP的287项SHA均匹配；TTO Conda安装清单也全部匹配。两包源码与各自当前树一致。服务wheel与当前生产Python源码一致；TTO wheel有下面F1的一处差异。包内清单完整只证明各包内部没有损坏，不证明源码、wheel和核验记录是同一候选。

## F1：最终 TTO wheel 与最终源码不同，交付身份声明失效（P1，阻断批准）

位置：`src/tto/report.py:63-69`、`scripts/check_install_identity.py:23-25`、`evidence/platform-curve-v2/tto-final-installed-identity.json`。

wheel中的`operator_evidence()`在解析人工记录后直接返回文件SHA；当前源码新增了`files.json`声明SHA读取和`declared_index_sha256`、`index_matches`字段。这段新增逻辑没有进入被审wheel，Conda包继续携带该wheel。

现有核验JSON声明`source_equals_wheel_equals_installed=true`，但它登记的是较早的report.py身份。审查期间直接调用现有非editable Python3.10.18环境中的正式`check_install_identity.py`，以当前源码和同一wheel重新核验，在内容相等断言处退出1。已安装软件因此也不具备当前源码中新增的人工记录索引核对字段。

影响：不能以当前源码审查、185项源码测试或较早的核验记录批准实际安装包；实施报告“最终源码与wheel相同”的陈述不成立。该差异目前集中在人工记录索引追溯，不能夸大成整个模型实现缺失，但它明确违反S4/T8交付身份标准。

最小关闭条件：先冻结最终源码，再构建新的候选wheel与Conda包；在实际非editable安装环境重新做逐文件核验，更新报告、身份清单及证据包。保留被审0.2.0身份，不通过改写旧核验JSON消除矛盾。

## F2：TJ不合格的帧能掩盖同生命周期合同变化，旧段评分未被排除（P1，阻断批准）

位置：`src/tto/platform_quality.py:34-37,57-72`，下游`PlatformEngine.update_profile()`、`dataset.replay/build_dataset()`与`recorded_results()`。

根因：平台、源周期及GPU调度的生命周期校验依赖`Quality.accept()`先接受有效TJ。`stale_or_missing_tj`等结果会提前返回；因此具有明确当前stream/新seq身份的帧即使携带了变化的固定合同，也不登记违例、隔离事件或永久mixed标记。

固定合成反例使用同一stream的连续新seq：正常源周期1000ms → 周期3000ms且该帧缺TJ → 恢复1000ms。没有修改源服务、频率或真实数据；这是离线输入夹具。通过被审wheel的生产Engine/Journal记录后，再走正式report和build_dataset入口，得到：

- 中间帧仅报`stale_or_missing_tj`；`lifecycle_contract_change=0`。
- replay仍声明`mixed_profiles=false`，正式数据集创建成功。
- 报告保留132条当前有效方法×起点×时距评分，其中54条来自变化前的旧段；隔离事件为空、质量排除数0。
- 原始观测、预测与评分文件在report前后SHA未变。

影响：单条温度不可用能掩盖本应独立成立的输入身份违例，使不兼容合同的run被声明为单一合同，并漏撤下旧段评分。它违反第4节T2、第7/8节mixed_profiles与正式建库要求，以及R3b既有隔离结果的汇总语义。普通温度缺失仍可按原规则处理；不能把测量资格作为合同检查的前置条件。

最小关闭条件：对属于当前生命周期且身份已经核实的帧，独立处理固定合同证据与TJ可用性，沿用现有违例、断段、隔离和永久mixed语义；不让晚到/退休流回调改变当前状态，不新增更严的温度失效规则。保留上述反例，验证旧段退出有效成绩、恢复段可继续记录但整轮正式建库拒绝。

## F3：Conda运行入口可被旧PYTHONPATH覆盖，升级后静默运行旧版（P2，必须返修）

位置：`scripts/install_tto.py:37-43`生成的launcher；对应升级测试`verify_platform_upgrade.py:32-33,74`。

安装核验使用`python -I`并清除PYTHONPATH，但最终`~/TTO/tto`入口是`conda run ... python -m tto`，继承调用者模块搜索环境。安装验证与用户实际启动采用不同的模块选择规则。

对已验证的Conda升级目录只执行离线`--version`：不设置PYTHONPATH时返回0.2.0；将PYTHONPATH指向本仓保留的0.1.2基线源码时，同一个launcher正常退出0并返回0.1.2；`installation.json`仍为0.2.0。没有安装、启动采集或连接设备。

影响：测试者终端残留开发路径时，安装包核验虽通过，doctor/collect/shadow/report实际执行的却可能是旧实现。这会重新引入本轮已修功能缺失，同时用户手里的安装身份仍显示升级成功。

最小关闭条件：让最终launcher采用与核验一致的包选择规则，例如以隔离模式调用Python；补一条“保留旧PYTHONPATH也执行已安装候选”的真实入口回归。保留用户配置和TTO业务环境变量，不更改Conda base。

## 其余方案落实与证据评价

| 关键链路 | 审查结论 |
| --- | --- |
| 服务端平台识别、固定策略 | 设备树精确token、unknown处理、Thor独立1000ms与源周期分离，符合方案 |
| GPU因果合并、四状态与资源归属 | 结果有界且错误参与选择，源行解析前捕获，HTTP/WS不查NVML；唯一worker、pending/error与清理归属有生产链路和针对性证据；未发现离线阻断项 |
| TJ、具名温度/rail及旧客户端 | 原字段与TJ投影保留，单位/真实名字未做假别名；C客户端、代表性封包和4K/8K证据可查；真实设备接收仍未验收 |
| TTO统一GPU、独立年龄、四种profile与CURVE | 主链路符合方案，0有效、失败不fallback、GPU组与M0分开；需要F2补齐跨质量状态的生命周期检查 |
| schema1历史兼容、R1/R2/R3/R4/R3b主体 | 入口分派、模型验证、时间切分、分层公平集合、保存预测/评分关联与重定向策略仍在；本次未发现需要独立重构的缺陷。F2是新增合同传播到R3b的缺口 |
| 新模型、建库与匹配 | 静态列与组、训练侧选择/缩放、三时距、模型与入口校验均有实现；F2使“整run单一合同”的上游保证失效 |
| 包、安装、升级与报告 | 服务候选一致；TTO的F1/F3使其最终交付不能批准。两份ZIP内部SHA清单本身完整 |
| 实机与收益边界 | 两报告明确未连接/部署、未验证真实NVML/目标Linux资源/模型收益，与本轮授权一致；这些属于后续验收而非本轮返修借口 |

作者提供的185项TTO和168项服务源码/安装后日志已读取并核对候选对应关系，本轮没有把读取日志称为重新独立执行全量测试。服务包独立解压回放、安装升级、旧PID/override反例及固定fixture证据齐备；TTO原核验身份因F1过期。两仓`git diff --check`无输出。

## 独立复现记录

本次最小复现及正式派生报告保存在`/private/tmp/tto-final-candidate-review-20261013/`：`lifecycle-missing-tj.json`、`formal-report/`、合成`synthetic-runs/`、`identity-recheck.log`、`launcher-import-selection.json`。另一个三帧最小反例在`/private/tmp/tto-independent-review-ewgj1wka/`。使用现有已安装候选的Python3.10.18；没有为了复审重建包或替换源码。

建议有限返修只关闭F1—F3，然后以新候选身份交回复审。rm01OrinStatus保留当前1.1.1候选和证据。**当前整体不批准进入部署；此次审查到报告交付为止。**
