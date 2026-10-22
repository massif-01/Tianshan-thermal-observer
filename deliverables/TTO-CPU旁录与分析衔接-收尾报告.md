# TTO-CPU旁录与分析衔接：收尾报告

2026-10-20｜TTO-CPU-PREP-CLOSE-v1.0｜仅离线/自建服务；交回独立核对，不授予现场许可。

**R2已实现有界异步启动：** cpu.2不再让SSH复用检查阻塞唯一时钟循环，STOP/截止仍能执行。检查/源执行子进程、取消、退出及失败证据均纳入本轮自身生命周期，没有终止SSH master、改全局SSH或新登录回退。

**R1由模型线维护唯一桥接：** 完整联合样例来自实际`cpu_source.read_cpu/utilization/stream → 子进程stdout → Sidecar.receive → 原样arrival/wire → 唯一bridge → 原冻结Activity/evaluate_stream`。原生collector/state属于同一个合成run，包含真实Socket.IO断连/恢复；不是双方各造一套模型FRAME。

**本轮验证范围：** cpu.2源码与隔离安装wheel均通过48项文件身份及23项局部测试；完整样例150包，0 Requester、0模型查询、0推理POST。模型线参数、热θ和旧成绩保留，原CPU版未胜HOLD/CORE=MEAN的负结果未改。联合模拟只证明衔接与撤销，不是CPU先导、预测收益或控制通过。

**仍缺的环境证据：** 本轮没有完成新的Linux x86/Python3.10安装测试：Docker socket不可用，本机也无可启动的OrbStack/Docker应用。保留了失败尝试，未安装新运行时或绕过目标检查。本机macOS arm64/Python3.12.3代码安装和测试使用已有依赖，SciPy1.14.1与目标锁定1.15.3不同，不能替代目标安装；cpu.1的3.10收据不充当cpu.2成功。真实安装身份、源窗、jtop关系及开销仍需未来单独许可核对。

## 1. 本线有限变更

独立目录`experiments/cpu_activity_pilot_closeout_v1`与新候选`0.2.4+cpu.2`，没有热改cpu.1或任何设备安装。基于已交cpu.1 wheel（SHA `3a0d118a50a93a8d77a3dc714a546bd98d28f7b9254acb69084da9806628ac92`）逐字节比较：48项中仅4个文件变化：版本、cpu_pilot版本绑定、cpu_transport启动/证据/清理、旧cpu_interface失效撤销。native、runtime唯一循环本体、I-02、Requester、采样/HTTP/TTL、原12请求计划保持字节不变。

旧cpu_interface明确标为已弃用的fixture helper，真实文件转换统一走模型线bridge；其保留兼容函数也改为先选最新已到达语义状态，再判断valid/期限。因此10.00有效42%、10.30显式invalid，10.50不会重新取旧42%；合法新窗再恢复。没有新增第二种活动算法。

源侧200ms目标、源CPU5%/64MiB、接收8%/128MiB等原预算不变；原payload/256token/30秒SSE、单客户端、6孤立+6连续、1200秒硬上限及1080秒后不启动工作均不变。能力许可和负载许可仍分别判断，旧override禁止；当前没有设备/12请求授权。

## 2. R2为什么有界

`tick`只创建启动任务并检查状态，不等待SSH子进程。后台步骤为socket存在核对→本轮`ssh -O check`→原SHA bootstrap/源进程。预登记mux wait≤1秒、启动步骤总计≤3秒，真实源进程启动后首包≤1秒；时间均消耗原60/1200秒，不另延长。

check进程和source客户端均立即登记为本Sidecar自己的子进程。取消或失败先停止这些子进程；退出时TERM等0.5秒、必要时KILL再等0.5秒，并记录未确认回收而非冒充成功。启动任务取消和读流回收各有0.5秒等待边界；不等待master，不访问其他连接。缺失/失败拒绝，源SSH仍有ControlMaster=no、BatchMode=yes、ProxyCommand=false，禁止新TCP认证回退。

每条原始输出先写`cpu-sidecar-wire.jsonl`，原字节base64、线序号、实际接收时刻、接收域、run/command保留；通过验证才进arrivals。被拒行及错误阶段/类别/说明保留，不能进入有效分析。每个子进程stderr只保留前4096字节，同时登记总量/截断、进程阶段和退出码；异常不只剩ValueError。

实际本地子进程证据`fault-evidence/`保存非法UTF-8行、stderr截断，以及源启动退出码7。它们明确标“本地子进程，无原生run”，没有冒称新的TTO实验。确定性进程替身验证了永不返回、STOP、截止、失败返回和正常启动；另有真实本地睡眠子进程验证超时回收。没有执行真实SSH命令或连接设备。

## 3. 联合输入与时间资格

完整样例`joint-sample-complete/`：native UUID `b1a4248e-7274-4991-91ce-d8d61644006b`，150包，约60秒无负载诊断。source-config、原始native/state/launch、wire/arrival、事件/stderr、summary/files和source/receiver代码SHA齐全。CPU累计计数由合成/proc后端驱动实际源代码，源开始后7秒回退、9—11秒在线核切换、随后合法新窗恢复；原生服务约40—43秒断连、重连，撤销粗来源资格。全部是自建合成，源/接收主机为本机，不冒充Thor/N305测量。

初次试构`joint-sample/`失败原样保留：Linux源的ru_maxrss单位在Darwin测试后端未换算，触发原64MiB限额；刻意直接移除rail也触发原投影退出。没有放宽预算或返修原采集器；第二次仅修合成后端单位，改用原正式断连边界制造不可用。正式联合验收仅用完整150包，原失败不删。

源host/boot/session、原累计计数与每核在线集/窗原样保留。接收方有实际received_at、decision_generated、receiver_domain/host；本机boot未知如实null，不造N305身份或零延迟。相对sidecar事件时间以同run state中精确session_origin映射回本进程单调域，不将Thor钟与接收钟直接相减。

唯一bridge采用明确的接收顺序研究资格，CPU最早在decision生成后可用，支持截止严格不晚于真实received_at+1秒，沿用1秒无包预算，既非精确源年龄也非生产TTL修改。原生GPU/两rail保留原来源/update_id/available/期限；新CPU包不续龄。源查询窗/生成身份未知的GPU/rail只进诊断。最新counter_reset/offline/断连/epoch等撤销旧CPU资格，之后等合法新窗恢复，不向前回找旧valid。

温度起点仍每个原有效TJ最多一个，但记录真实状态已生成的decision时间，原measurement_received另存，防止倒填状态。新接口另冻结；旧1秒adapter与旧评分不改。每秒选择最后一个200ms计数窗输出只是交付节奏，不是重建了1秒积分窗。15/45/90秒标签各自资格独立，短样例缺45/90答案不会编造。

## 4. 安装与复验边界

新wheel和原安装器实际可取得。最小包不递归复制旧55MiB依赖；`assemble_wheelhouse.py`核旧清单、只复制原字节依赖并以cpu.2替候选，再由原安装器使用全新prefix。原cpu.1完整ZIP身份与依赖清单随附。未来获许可后仍必须`verify-install --target`，不能用本机3.12收据绕过Linux3.10要求。

23项源码测试与同23项安装wheel回归均通过。唯一runtime实际循环测试让mux检查永不返回，分别在约0.2秒触发STOP/诊断截止，回收所有自建子进程，自有任务剩余0；没有Requester。这些是合成时钟/自建服务测试，不是现场60秒通过。Python3.10语法解析另存，不能叫3.10运行测试。

CPU侧代码身份、模型适配最终身份、独立联合复验和具体CLI记录见本包清单与联合核验回执。安装/模拟/科学证据分开，旧Linux容器6条后超8%CPU的负证据仅按cpu.1原包引用，未提高预算重跑覆盖它。

## 5. 停止点

本轮不重训、不重做45分钟/42次拟合/I-02，不连接设备、部署、重启、发12请求、改风扇或发GitHub PR。先交回复审；如后续获准，也仅先核一次约60秒无新增负载能力，不能从能力核对自动升级为12请求。操作卡随包。

## 6. 总控独立联合核验与冻结身份

测试总控从独立副本实际调用模型线CLI及14项回归，通过。150条wire逐条解码与source对象/实际接收时刻一致，342个事件帧、56个原TJ decision起点进入原Processor/evaluate_stream；不是手工模型FRAME。5份适配产物与模型线最终结果逐字节一致；11份模型联合产物结构/引用/状态/计数一致，按1e-8浮点容差复核，最大差0。

| 分支 | ACTIVE帧 | UNKNOWN帧 |
| --- | ---: | ---: |
| BASE | 314 | 28 |
| MEAN | 214 | 128 |
| CORE | 214 | 128 |

这些是合成事件帧计数，不是识别正确率。撤销ledger含计数回退1次、在线集切换2次、native epoch切换5次、源初包缺窗1次、停止1次；后续合法窗恢复可追溯。实际评价入口分别保留15/45/90标签资格：15秒只有1个合格共同答案，45/90没有合格答案，不伪造新温度成绩。原阈值/未来输入转换与热模型完全未改。

唯一适配目录：`experiments/thermal_cpu_activity_bridge_v1`，版本`cpu-arrival-bridge-1.0.0`。适配器SHA `8d6fe5f013e67d2a26c192419b0b82f29a4c1aa794ddd598e2f6ba33a45045e3`；interface-freeze SHA `9278f1a6db1e0e9bc4ee488bb2958168799733a0d884f1ef771ddf57313c38dd`。活动candidate SHA `89ae53229af3e84b3bae1140a1ce013d6bf16e374cd5d3ffcde6fc7d28b78831`、analysis-spec SHA `df26198dd631a45564d88c10b7b30433ab8b272cb4cf5d3726d7be6eacbab716`不变。原热模型dff52c…、observer spec2080ad…也逐字节保留。

模型离线核验环境Python3.12.14/NumPy2.2.6/SciPy1.16.3；现场候选依赖仍是原Linux3.10/SciPy1.15.3。模型`requirements.txt`用于离线分析，不得拿它升级现场环境。新源/接收样例版本与bridge版本分别登记，不能只按候选名字认身份。

包内可直接复核的相对调用（输出目录必须全新）：

```sh
python model-adapter/bridge.py --run-dir field-evidence/joint-sample-complete/run --source-config field-evidence/joint-sample-complete/source-config.json --output NEW-ADAPTED
python model-adapter/joint_check.py --adapted NEW-ADAPTED --run-dir field-evidence/joint-sample-complete/run --output NEW-JOINT
python model-adapter/replay.py --output NEW-REPLAY
```

回执入口：`field-evidence/checks/independent-joint-verification.json`、`independent-model-semantic.json`；模型归属/交付由`model-adapter/model-handoff.json`、interface-freeze与模型线收尾报告登记。测试线source/docs/cpu2.patch给运行增量；source/config/startup-budgets.json给边界；candidate给可安装wheel/原安装器/依赖组装与旧依赖身份引用。旧大包不递归打包。

最终wheel为123392字节，SHA `b265045129c67f62fd28bdb15f5f6288a29ef5a682a54175c1e998529bfe35fa`。本轮完成有限代码和联合衔接收尾，但cpu.2的Linux3.10安装与全部真实能力仍未核对；停在独立复审点，绝不自动现场。

模型线最终独立交付为627579字节，ZIP SHA `5500ad25357c86bdb53dca7d3d6067d5d397e875e8d85a278f113ae2f6eeabff`，代码和必要成果已直接纳入本次统一包，不递归嵌套ZIP。统一包暂存目录另完整复跑14项适配测试和真实150包联合链通过，5份适配输出完全一致、11份派生输出语义一致，浮点最大差0。
