# TTO Orin / Thor / CURVE 适配实施与验证报告

日期：2026 年 10 月 12 日
候选：TTO 0.2.0
唯一接口合同：TTO-PLATFORM-CURVE-v2.0

## 结论与复审边界

TTO 0.2.0 已完成本仓库的 Orin / Thor 输入适配、GPU 独立新鲜度、CURVE资格、schema1历史回放兼容、schema2数据建库训练评估和报告改动。原88项回归加93项本轮回归在 Python 3.10.18 通过；最终 wheel 以非 editable 安装重跑181项通过。Conda 安装器在新临时前缀安装、升级和旧模型评估均通过。

这份交付是TTO consumer候选。WS会话已冻结监控服务1.1.1 producer fixture：manifest SHA-256 `59798e9e93fdc6b9968ef6f2e88847fdd238514c52ed43eb50f06d02432aacf2`，16个JSON逐文件SHA均核对通过。新增消费者回归将固定fixture经过Quality、Engine、Journal和正式report入口；另以本仓loopback服务验证Socket.IO/HTTP采集。fixture中的GPU、平台和时钟均为合成替身，不代表设备读数；monitor wheel producer验收由WS会话单独完成。

**TTO本地适配与离线验证完成，待独立复审；对冻结producer fixture的消费端交叉核对完成；实机验证未执行，真实预测效果待验证。** 没有真实数据和时间留出模型效果结论。

## 起点及边界

TTO起点 HEAD 为 `97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。开始前已保存源码SHA清单、Git状态、差异及源码快照于 `evidence/platform-curve-v2/before/`。未reset、clean、覆盖旧0.1.2 wheel/Conda包或旧R1-R4/R3b证据；现场原始run及其SHA收据保持原位。

最终方案SHA-256：`6f3acdf0f75904c828c182551da4e0f3e855d94dc20c19f13bca1cde1ba537ea`；两仓共同接口段SHA-256：`95be0c15fe2e2b440529c6896475e8e41d3b746bdfa330a623ba5aa7e5189b54`。原0.1.2 wheel与Conda安装包身份继续作为历史资料保存。新增候选SHA只使用0.2.0 wheel和本报告所列Conda ZIP。

不连接真实设备、不运行 `doctor --live`/真实collect/shadow、不部署、不重启源服务、不改风扇、绑定或源采样频率、不运行CUDA，不提交或推送。网络测试只连测试创建的loopback，信号测试只发给自己的测试进程。

## R01—R08处理与证据

| 项目 | TTO改动与修复前后结果 | TTO证据状态 |
| --- | --- | --- |
| R01 实际控制温度资格 | `normal_auto`保留旧义；CURVE独立使用成功PWM，不要求AUTO gain。source=default、valid=false、manual/off、保护及故障均留资格原因。读取preferred配置不冒充active来源。 | TTO生产Engine/CURVE正反例通过；原现场温度资格仍为0，保持阻塞 |
| R02 新旧GPU区分 | 旧格式只读取legacy gr3d百分比并标平台未确认；任一platform或新增GPU字段进入新版校验。新版缺标志/类型错误/非法读数撤下GPU，保留TJ；0仍是合法值。 | 0、legacy、缺字段、bool/float/未知版本、错误状态、同源冲突、非法值回归通过 |
| R03 样本身份及生命周期 | Quality先核验完整platform、source周期和GPU对象，同key字段改变不按普通duplicate放过；同stream变化周期/超时设置触发生命周期事件、隔离前段、清历史并标mixed。外层sample_age增长不作测量冲突。 | 实际Engine/Journal/report日志关联正反例通过；生命周期设置变化报告和R3b门禁通过 |
| R04 GPU因果年龄 | TTO把GPU基准年龄、外层样本年龄和本机单调时间按既有锚点推进；重复身份不生成起点。30/120秒GPU保持值在到期边界截断，缺口不由恢复值回填。 | 4500ms + 外层1000ms阈值反例、重复、UTC跳变、短读恢复与窗口缺口通过 |
| R05 新旧记录回放 | schema1显式分派到冻结旧Engine/Features，旧run段号/引用/标签保持。schema2缺合同拒绝评分并给独立报告诊断，不退回旧逻辑。旧run新版输入诊断写新目录。 | 实际旧现场run先以HEAD源码报告，再用新wheel报告；raw SHA保持，旧0.1.2冻结模型升级后仍能离线评估 |
| R06 配置升级 | 配置文件维持schema1，`features.power_current_rails`保留兼容。新版周期使用线上`telemetry_meta.source_sample_interval_ms`；不改用户配置。人工非空周期与线上周期冲突时保留TJ、标配置冲突并拒绝正式冻结。 | 正常配置、unknown/1/1000/3000ms、冲突与升级反例通过 |
| R07 平台和profile | 四种固定profile：Orin/Thor × AUTO/CURVE，列数54/53/51/50。首次profile只写一次；起点另记profile/scope/contract hash。unknown前导保留但不进入已知profile模型。平台、已知周期或UUID不兼容切换保持mixed。 | 四种真实Engine→Journal→split/train/evaluate→report模拟链路与 A→B→A 反例通过 |
| R08 AUTO诊断 | CURVE不把gain、auto_state、自适应预测和固件预测当有效控制证据；AUTO原语义保持。源状态、当前GPU有效性、配置来源、实际来源分开显示。 | CURVE no-gain/duty=0及AUTO regression通过；HTML/Markdown/JSON共用同一结果 |

未合入其他独立问题：监控服务原始运行记录的`files.json`中`operator-records.jsonl`声明SHA与原采集收据不一致（声明`b739f29c…`，原收据`b367761b…`），其余7个原始文件的SHA匹配。记录已保留，影响及服务侧归属由WS会话核验；本轮没有修改这份原始记录。

## 测试及数据

最终源码命令为 `.venv310/bin/python -m pytest -q tests`，结果 **185 passed**（旧88项＋新增回归97项）。安装后非editable wheel重跑位于 `/private/tmp/tto-platform-curve-v2/tto-final-installed-verification-producer/`，包含全部185项；同一入口另跑离线doctor、demo模拟训练/留出、CLI训练、离线信号、R1-R4及R3b正式report、loopback协议和自身进程退出。源码pytest日志与JUnit XML见 `evidence/platform-curve-v2/tto-final-producer-tests.log` 和 `tto-final-producer-tests.xml`。

实施期间保留了三类失败记录及修正：早期合同回归暴露字段状态/fixture假设问题，修正后全量回归通过；首次Conda升级复验把ZIP当作已解压目录传入，升级验证入口改为接受并解包该ZIP后，旧版到0.2.0升级通过；证据包初次patch往返发现无末尾换行的fixture会被patch工具规范化，最终改为对冻结fixture逐字节复制并单独SHA核对，最终patch往返和包内SHA清单全通过。完整失败/成功日志均保存在证据包`logs/`。

模拟R3b报告由安装后正式入口生成：

- 正常：510条历史评分，510条有效；
- 同身份冲突：510条历史评分保留，510条排除，其中直接争议标签12条；
- 冲突后恢复：816条历史评分保留，510条隔离段排除，306条恢复段有效；
- 序号倒退：相同现存隔离粒度及新测试fixture的schema2生命周期变化亦有明确原因。

四类R3b数据与模型全部为合成。source run 的预测/评分只读；报告运行前后的日志SHA一致。模拟链路证明软件路径，不代表实机收益。

原现场run报告的旧/新对照都关联同一 `observer_run_id`。旧源码报告显示196条有效新TJ、38个起点、0个正常AUTO起点、15/45/90秒标签数为0。新报告仍显示CURVE 38起点、控制资格0、有效温度状态0/40、GPU有效样本0/196，并列出Thor具名rails/分组温度的输入覆盖诊断。原始文件SHA逐项与采集收据相同，见 `saved-run-preservation.json`。不把无效绑定解释为固件接错，也不提出降风扇档位结论。

最终 wheel 干净非editable安装在 Python 3.10.18/macOS 27 ARM64；wheel内`tto/*.py`与工作树、安装路径逐文件相同。新增producer fixture路径回归在已安装wheel验证中通过。Conda安装/升级在新的临时前缀使用Python 3.10.22，非editable核对通过；旧配置、冻结dataset/split/model、旧run原始日志和原安装身份哈希升级后保持不变，旧报告有效预测记录和质量隔离逐条相同。Conda base 516个文件/执行文件指纹不变。安装器回归10项全通过，包括新安装、重复升级、旧安装保留、半安装重试、Tampered wheel拒绝、无Conda、占用目录拒绝及不创建采集run。

上述Conda验证主机是macOS ARM64，不是N305/Linux；不代表目标系统发行版、架构或本地Conda缓存已现场验收。N305 CPU/RSS/P99稳态资源和Linux离线wheelhouse仍待目标设备/系统环境确认。

## 候选身份

wheel：`tianshan_thermal_observer-0.2.0-py3-none-any.whl`，SHA-256 `b439128bef648fb7455572f0ab9e17c3d4d268d8d721c471db537858538e638c`。

Conda安装包：`TTO-v1-0.2.0-Conda便捷安装包.zip`，SHA-256 `d09adddecdf67e02ce760be858389944a8711da3acb6eb9150b9536fa56f6547`。

源码/实际导入核对JSON：`evidence/platform-curve-v2/tto-final-installed-identity.json`。Conda升级finding及10项安装器finding分别位于临时验证目录的final-conda-upgrade-verified/findings.json和final-installer-regression/findings.json；最小证据包中保留其报告与日志。

交付包重跑入口为zip内的`REPRODUCE.md`。通过`incremental.patch`将更新应用到`baseline/tree`后会逐文件核验after SHA。0.1.2旧wheel及旧Condа安装包仅为升级基线，单独放在baseline目录；新候选只标为0.2.0。

## 待交叉确认和未执行事项

producer由WS会话独立完成并交付：`tegrastats_api-1.1.1-py3-none-any.whl` SHA-256 `2309c819e3d42887261db718f3a6149edbdde1fb877cb4d5151b43a663b3c338`，源码、wheel与独立解压回放各168项通过；其独立证据包 `rm01OrinStatus-Orin-Thor-最小证据包.zip` SHA-256 `1bd92e22dc0588d3a562a8aadb63a4fe3dd3f2827dbb36c5247482c99e587175`，包内287项SHA已核验。以上服务端证据由其仓库报告和证据包自证；本报告只记录固定manifest交接与TTO消费端验证，不把服务侧测试当成TTO测试。

真实NVML/驱动、Thor/Orin端点、当前服务实际安装包及systemd `ExecStart`、现场温度有效性、部署/重启和真实模型收益均未执行验证。目标Linux安装器/CPU资源验收留待现场授权。复审前不进入真机阶段。
