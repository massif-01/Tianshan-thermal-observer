# TTO closeout.1：N305首次300秒只读诊断与停止时刻修订

**本次只读诊断已完成一次并正常到时结束；没有启动任何推理负载。** 运行段的测量、模型及控制上下文分别正常建立，HTTP 360次全部返回成功。末次precheck的ready=false发生在到时关闭Socket.IO之后，I-02撤回当前有效性；原记录保留，不能用最后一帧代替整段判断。当前证据支持交回主审评估下一步，不等于已授权mixed，也不证明历史超时根因已修复。

停止时间问题已在独立closeout.2副本修正并完成窄回归及目标环境自建服务验证；**未部署到N305，未热改本次closeout.1**。未改变AUTO、曲线、gain、保护、采样或TTL，未刷ESP32、未重启源服务。

## 1. 本次授权、安装与身份

- 当前用户明确回复“允许本次独立安装及300秒只读诊断”；来源与UTC落盘记录在installation/authorization.json，平台消息精确时间未知，未倒填。
- 设备：lpmu305 / 10.10.99.99，Linux x86_64，glibc2.39，既有CPython3.10.22可用venv/ensurepip；可用磁盘约916GB。系统PATH没有python3.10，使用既有 `/home/rm01/TTO-midload-0.2.4/conda-env/bin/python` 作新venv的基础解释器，没有安装或升级生产依赖。
- 独立prefix：`/home/rm01/TTO-field-closeout-1-diagnostic-20261019`。离线wheelhouse安装，verify-install --target前后通过，42项文件校验一致。基础解释器仍依赖原Python路径；后续不要删除原环境。
- 现场版本：tto-field-candidate **0.2.4+closeout.1** / native0.2.4。wheel 109,885B，SHA256 `56cbcb3ff9b06aa8cab55a70c31956c4ec7ca12a619bde91ef88d0f566e62d82`；原60,708,125B交付包SHA已核对。
- native源码聚合SHA `06d17ec5205cea268d4d42eeeb87169d3ca64c91a81acd0b4bdafe2f57e49806`。model `dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`；spec `2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`。
- 原TTO及0.2.4安装目录保留；两份原installation.json的SHA前后相同，未启动/重启其服务。旧SSH复用失效后，以本对话曾确认的相同ED25519指纹及独立known_hosts恢复连接，未修改用户全局主机密钥记录，未保存密码。
- firmware_identity仍未知；没有读取或伪造固件源码版本。native报告中的通用 `target_host_verified=false` 保留；本次Linux/Python/安装目标实际验证另见installation-identity.json，二者没有互相覆盖。

## 2. 当前配置与本轮唯一生命周期

从设备既有configuration/collection-config.json读取配置，新副本只改storage.data_root，来源SHA与差异保存在configuration-provenance.json。端点为Thor `http://10.10.99.98:58090`、主板 `http://10.10.99.97`；未使用examples占位地址。源采样字段沿用历史1000ms证据，本轮300条真实telemetry_meta均确认1000ms，平台识别为jetson_thor/tegra264、GPU来源NVML。

保持fan 1秒、temp 5秒、HTTP请求2秒、fan原始TTL2.5秒。原生独立端点轮询合同TTO-POLL-INDEPENDENT-v1：每端点在途峰值1，合计峰值2；这是已审候选的合同，不是本轮改采样/并发。没有继承旧override。

- 当前preview生成的新command_id：`diagnose-20261019-13242df2-9e02-4900-85db-fa3392d57d34`。
- config SHA：`2eec0dc0cd0202aed94b1a00e270677eef571ea91593291a4243fa295ac35164`；diagnostic binding匹配该现场preview和本次用户许可。
- 实际native run：`854efcfd-c498-4491-aba8-dd1564f05bf4`。
- 目录：`/home/rm01/TTO-diagnostic-closeout1-20261019/run`。
- UTC开始 `2026-10-19T08:54:59.609514+00:00`，结束 `2026-10-19T08:59:59.700251+00:00`；北京时间2026-10-19 **16:54:59.609—16:59:59.700**。实际入口持续300.091秒，native 300.008秒，结束原因diagnostic_duration / native duration，进程退出码0。
- 单一native UUID、单一collector/observer，共享同一quality engine；961次回调对应961次I-02预处理视图。Requester=0、请求执行器=0、协议推理请求=0，逐请求日志为空。未查询模型列表/metrics，未联系推理监控下发负载，未要求YET。
- 自己创建的异步任务剩余0，native在途0；post-check未发现遗留TTO进程。

## 3. 分层时间覆盖与最后一帧

以下按约0.1秒gate评估，将上一帧资格累计至下一帧；不是精确到微秒的源状态切换。总覆盖分母300.083秒；末帧之后不推算不存在的区间。

| 层 | 可用秒数 / 比例 | 首次可用 | 运行段最长不可用 |
|---|---:|---:|---:|
| TJ及独立rail测量 | 299.471s / 99.80% | 0.615s | 0.612s（开始建链） |
| 冻结模型可消费状态 | 290.461s / 96.79% | 9.626s | 9.623s（初始化） |
| 控制安全上下文 | 294.523s / 98.15% | 5.563s | 5.560s（确认窗口） |
| 三层同时可用 | 290.461s / 96.79% | 9.626s | 同模型初始化 |
| 成功PWM / temp上下文原始资格 | 299.775s / 299.775s | 见原始gate | 见analysis.json |

模型阶段：uninitialized 0.612s，provisional 9.011s，tracking 290.461s；未改冷启动规则或使用连续60秒旧门槛，没有训练/更新参数。

**末次diagnostic-precheck.current_measurement_model_context_ready=false如实保留。** 最后正常gate在t=299.986s，三层均true、tracking；native达到300秒后关闭连接，t=300.009s产生observation:961/socketio_disconnected；t=300.087s最后gate为三层false、unavailable。I-02按断开边界撤下当前资格，符合已审接口；该末帧之后没有继续诊断或新请求。observer复位后出现long_missing原因标签，不能据此倒推前面300秒一直缺测。时间覆盖是前帧积分，因此末帧没有单独时长；analysis.json保留末帧与最后正常帧以便复核，不删除、不改成ready=true。

全过程start_allowed=false：运行段原因仅缺少本轮负载许可/仪表锚点，收尾末帧另外含来源不可用。load_authorized=false、automatic_upgrade_to_mixed=false、field_proven=false均符合本次边界；schedule_completed=false也不表示diagnose失败，因为没有创建mixed调度。

## 4. 通讯、遥测与资源

| 读请求 | 成功/总数 | HTTP错误/超时 | RTT中位/最大 | 成功返回最长间隔 |
|---|---:|---:|---:|---:|
| fan | 300/300 | 0/0 | 18.50 / 56.88ms | 1.047s |
| temp | 60/60 | 0/0 | 26.02 / 64.81ms | 5.024s |

所有HTTP阶段均到complete，保留request_start/connect/connection_ready/headers_sent/response_headers及接收/字节信息；没有因无超时删除阶段原件。fan成功间隔超过2.5秒为0，poll missed/skipped/dropped为0。Socket.IO一次建链，收到300条原始源记录；唯一断开在到时关闭阶段，没有运行中重连。HTTP超时与设备温度过期独立判断，本轮二者均未观察到。**本轮正常只说明这5分钟的结果，不能宣称历史227次超时根因已修复。**

TJ范围45.375—45.656°C；GPU利用率0—3%，平均0.12%。独立rail平均：VDD_GPU 1.984W，VDD_CPU_SOC_MSS 5.964W，VIN_SYS_5V0 4.385W，分别保留，不相加当整机功率。成功PWM全程17%，AUTO 300条，gain 0.5435900092保持不变；fault/guard/temp_stale=true各0条。仅描述当前背景状态，不假设模型驻留或具备混合槽位容量。

资源295次记录：RSS均值74.62MiB、峰值76.18MiB；CPU单核等效平均2.83%，P99 4.92%，最高单次5.89%。均值低于5%目标但有单次超过，未把目标当严格峰值通过条件。完整run文件15,391,182B；末次资源快照field日志12,605,814B、native日志2,658,908B（收尾文件不含在该快照内）。保留resources.jsonl和CPU时间原件，没有以本轮指标推断高负载开销。

## 5. 停止时刻局部修订（独立副本，未部署）

修复对象：旧runtime外部调用stop时未传本tick时刻，Scheduler使用上一tick self.now，停止事件与drain起点记早。现在stop要求显式now，runtime传本次循环单调时刻；所有内部stop也传当前self.now。保持第一停止原因/时刻，拒绝时钟倒退。没有改变计划、TTL、退档、模型、保护或Requester。

新发行后缀closeout.2，wheel 109,897B，SHA256 `de1c67c143c97733b9c14501253ef0216157462c77eff7bbee2124e146d5d9db`。42项源码/数据对照只改变scheduler.py、runtime.py和版本声明；candidate-files随之重新封存，native源码、模型/spec、冻结计划、Requester及I-02 exporter均不变。N305仍保留closeout.1；小修仅在Mac独立源码和自建Linux容器验证，未连接真实推理端点。

- 4项确定性时钟回归通过：实际2.125s停止替代旧2.000s；drain从2.125s起算；重复通知不续期；省略/回退时刻拒绝；内部user_stop时刻正确。相同新增回归在原closeout.1失败，证明捕获旧问题。
- 新wheel在Linux x86_64 / CPython3.10.12离线安装并verify-install --target通过；相同4项回归通过。
- 原在途采集退出断言保留并加强：自建服务24次真实HTTP协议假请求，采集退出后无新调度提交、无新协议提交，事件单调；在途自然收尾，连接关闭、自己任务0、native在途0。这是loopback，不是GPU或现场负载。原始首次目标验证及本地28次假请求证据分别保留，不累加成实测总数。
- 初次无隔离wheel构建因缺setuptools失败，独立构建后成功；一次重复离线验证因已有输出目录拒绝覆盖，失败证据保留，新输出完成加强检查。**现场诊断只执行了一次**，没有为变绿重测设备。

## 6. 交付与限制

完整电脑侧原始run在diagnostic/run/，保留summary、diagnostic-precheck、resources、admission、states、native raw和各级索引；现场同路径亦保留。18项入口索引字节/SHA与7项native SHA核对通过；本包另附全文件SHA清单。安装身份、preview、binding、原配置来源及本次授权在installation/；局部patch、完整变更文件、新wheel、构建/回归证据在stop-fix/。

当前没有新增证据阻断“交回主审评估正式轮”，但正式mixed尚未放行。仍需主审核对小修及本次诊断，并由用户另确认当前窗口、驻模/空闲/槽位、YET测点记录与首锚点。不得从本次ready或正常HTTP自动升级execute。保持既定fixed-anchors计划，不重做三条任务，不把诊断当预测物理精度/控制收益证明。

本次已停止，等待复审；未提交、推送或创建PR。
