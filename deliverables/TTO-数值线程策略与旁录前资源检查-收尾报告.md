# TTO-数值线程策略与旁录前资源检查-收尾报告

已在独立候选 **0.2.4+cpu.3** 补齐数值启动合同：两个实际现场CLI在数值库首次导入前把继承的冲突配置归一为1，再核验本进程中NumPy/SciPy的实际线程池；不能核验就在网络前拒绝。旁录前新增原链资源准入，原生链已经超预算或资源未知就不启动旁录，原生诊断仍有界完成。

本地最终安装、同进程线程取证、全193条原记录数值等价、36项相关回归及实际CLI自建服务验证通过。**尚未连接、安装或复测N305；现场唯一根因仍未确认，不进入12请求。** 默认线程造成大开销的机制证据成立，不把本机数字当N305修复验收。原cpu.2与失败记录不改。

## 1. 已确认问题与未确认的现场原因

完整阅读本包01独立复审、02指令、04来源身份，接受真实run `80938521-b659-4160-a7b2-5fdfb6ebc197`的失败及模型线有限负结果。

原observer-spec声明`CPU_BLAS_threads=1`，实际cpu.2入口/launcher未强制落实，也未保存失败进程的实际数值线程池。事后另一个shell的env=null不能替代失败进程证据；旧166%是N305接收/估计进程自己约1.66核心等效消耗，不是全机或Thor的利用率。

本轮不开展系统性能普查。已按同记录、同解释器/数值依赖复现默认与单线程差异，优先修启动合同。没有采集旧现场进程的栈/线程池，不能写成“现场166%的唯一根因已经证实”。

## 2. 实际修改与边界

运行清单50项，相对cpu.2仅8项新/改文件：

- `numeric_policy.py`：共用早期初始化与取证。记录候选版本、PID/host/解释器、导入前环境、应用时刻、最终策略、NumPy/SciPy版本及扩展模块、实际已加载BLAS库路径/版本/pool数及两库分别覆盖、核验时刻和结果。`threadpoolctl.threadpool_info()`仅用于取证，不靠后设环境或动态threadpool reset伪装提前加载的库已受控。
- `cpu_cli.py`、`cli.py`与`identity.py`：两个安装后CLI及验证入口共用该实现；共用runtime再次核对同PID策略，并把`thread-policy.json`写入实际run。CLI启动失败时在`OUTPUT.startup/thread-policy.json`保留同进程失败回执。预览/验证进程回执不能替代实际run回执。
- `receiver_resources.py`与`runtime.py`：复用原1秒进程user+system差分/RSS；在启旁录前作一次资源判断，明确记录`baseline_receiver_resource_budget_exceeded`或`baseline_receiver_resources_unavailable`。资源读取失败写unknown，不借旧好值通过；启动后的资源不可读也会停旁录。未改原单核等效分母或资源阈值。
- `__init__.py`、`cpu_pilot.py`：声明cpu.3，并要求后续能力回执与本候选版本相符，旧cpu.2许可不能跨版本自动复用。

原生TTO全部文件、`cpu_source.py`、`cpu_transport.py`（含有界SSH）、I-02、投影、Requester、调度器/冻结计划、热模型与observer-spec逐字节保持；详见source-identity.json。没有修改Web UI、采样/TTL、fan/temp轮询、推理payload、活动阈值或科研旧成绩。

只约束本候选进程的数值池，未把Python及所有工作线程强制为一个线程；未使用CPU affinity，不编辑系统环境、.bashrc或其他程序。本候选明确支持可取证的已锁定OpenBLAS组合；未知/不可核验后端（例如本机另一套Accelerate安装）拒绝，不扩展为所有后端兼容平台。

## 3. 资源准入的预登记定义

实现/测试之前已保存`docs/baseline-resource-contract.md`：

1. 第一个t≥30秒的runtime tick，在任何旁录启动调度前，读取最新的原1秒进程资源区间。资源记录先落盘，再判准入。
2. 区间起点≥1秒（排除导入/启动和首个无差分样本），跨度0.5–2秒，结束不晚于决策、年龄≤1.5秒；CPU/RSS必须有限、非负。不是事后调出来的平均窗口。
3. CPU≤8%单核等效、RSS≤128MiB才可启旁录；无可靠区间、未知、陈旧均拒绝。只检查最新可靠定义的区间，不声称整个基线历史都低于门槛。
4. 判定只做一次，不重试、不延长；失败不停止原生诊断的有界归档，也不变成温度保护或负载许可。启后的原CPU/RSS/源预算与撤销/回收仍保留。

用原失败记录的同分母不会因模型phase available或温度正常就通过；温度保护、测量/模型资格和用户授权仍分别判。

## 4. 同进程实际线程回执

使用**安装后的真实console entry**，不是另一个shell代查：

|场景|实际结果|
|---|---|
|干净环境`tto-cpu-pilot verify-install`|两OpenBLAS池均1，50项身份通过|
|继承五个相关环境项均为8|原8记录在回执，候选内归一1，两库路径分别覆盖且实际均1|
|共用`tto-field`入口继承8|同实现核验通过，两库分别覆盖且实际均1|
|测试sitecustomize提前加载NumPy|网络前明确拒绝，记录已加载模块，未创建run、无网络尝试|
|测试后端取证只返回一个库的池|网络前明确拒绝，未用环境值1冒充verified|

最终真实CLI自建服务进程PID **53570**，`run/thread-policy.json` PID与summary时钟PID一致。NumPy2.2.6的OpenBLAS0.3.29和SciPy1.15.3的OpenBLAS0.3.28各1线程；真实动态库路径在回执。导入前继承8、策略应用和最终核验时序均在同进程保存。

本地是macOS ARM64 / CPython3.12.3。原本的Accelerate库不被当成可核验OpenBLAS；在独立测试venv中安装同版本、面向较早macOS部署目标的OpenBLAS wheels进行验证，没有改变基础环境或现场锁定依赖。Linux x86_64 / Python3.10目标尚未执行；本地`--target`仍按原边界拒绝，没有绕过Python/平台检查。

取证接口依据[threadpoolctl官方说明](https://github.com/joblib/threadpoolctl)；本报告的池数/开销结论来自本轮实际进程回执，不从文档推断现场行为。

## 5. 同事件离线对照与数学等价

两独立子进程均为Python3.12.3、NumPy2.2.6、SciPy1.15.3、psutil7.0.0；同39条原始事件、按原12秒节奏回放engine→I-02→Pipeline→原ThermalObserver→证据序列化。默认子进程从精确cpu.2 wheel加载代码；cpu.3子进程使用安装后的新候选入口初始化策略。没有网络/旁录/设备。

|本地配置|实际NumPy/SciPy池|累计进程CPU|墙钟|单核等效CPU|
|---|---|---:|---:|---:|
|默认|14 / 14|32.641327s|12.005055s|271.897%|
|cpu.3策略（继承8）|1 / 1|0.111127s|12.005051s|0.926%|

两次都有逐线程CPU增量、RSS、callback P95/max与真实池信息；完整JSON随包提供。所有科学状态与原保存值相符，最大差约4.97e-14。默认和单线程CPU差异是当前本地机制证据；没有用它估算N305收益。

另全193条紧循环回放核对全部嵌套state语义，包含Tf/Ts/E、协方差、阶段、有效性/来源/截止、撤销和cold_starts，检查11054个数值字段，最大差3.84e-13 < 1e-8，非数值字段/阶段无差异。**紧循环CPU接近100%只用于数学等价，不是实时性能指标。** 未重训/重新打分，也未改旧模型线任何产物。

单线程局部回放与实际自建服务未显示持续高开销，故没有触发本轮“若仍显著高开销再本地profile”的后续条件；不扩大排查。

## 6. 最终安装后自建服务与有限回归

最终wheel的实际CLI运行60.081902秒：前30秒原生、后30秒旁录，t=30.067727启旁录、t=60.075190正常收尾。1个collector、1个估计器、0个Requester/模型GET/推理POST，退出后自有async任务0，150个原始wire包。

|实际阶段|接收进程CPU均值|CPU最大|RSS最大|
|---|---:|---:|---:|
|启旁录前|2.476%|3.299%|69.578MiB|
|实际旁录期间|2.432%|3.229%|70.438MiB|

退出后的资源样本为0，单独保留空集合，不捏造“after”均值；这是按实际start/stop分组，不将30秒后的所有时刻无条件叫旁录。

源是明确合成/proc文件fixture，包含计数重置/核offline故障，用真实序列化/接收代码生成；其`cpu_measured`检查因有意无效窗口为false，完整软件流程不被误写为现场qualified=true。原资格规则保留，不为了绿色删除失效样本或另跑fixture。

相关安装后回归**36 passed**，覆盖基线超CPU/超RSS/资源未知不启旁录、正常基线只启一次、后续CPU超限及时停止；保留STOP/截止（含挂起SSH子进程）、自有回收、latest-invalid撤销、冻结12请求虚拟等待/未知结束规则。全部使用自建服务/假流/模拟子进程，不向推理监控派发负载。

本机另有观察进程持通用native锁；没有终止它或删除锁。测试专属sitecustomize/fixture只把锁映射到独立路径，仍保留flock互斥，发布代码没有私有锁开关或互斥绕过。实际时钟/资源值未替换；五类分支用确定性资源/缩放测试时钟的证据另标，不能作为性能数据。

早期失败日志保留：隔离测试环境缺依赖、通用锁冲突、沙箱拒绝自身逐线程取证、测试中读到旧安装副本和缩放假流不匹配；最终对固定wheel安装副本重新验证。没有把这些失败藏成现场结果或通过放宽预算解决。首轮本地CLI与最终CLI验证分别存放，交付结论只引用最终identity/SHA和installed release suite。

## 7. 可安装交付与下一步

- 新wheel：`tto_field_candidate-0.2.4+cpu.3-py3-none-any.whl`，127193字节，SHA `a9f0394097180c952d8b7f4e1cebac65fe7f2cc612c7f7189dfac6566502c9be`。
- 仅新增`threadpoolctl==3.6.0`纯Python wheel，18638字节，SHA `43a0b8fd5a2928500110039e43a5eed8480b918967083ea48dc3ab9f13c4a7fb`；原20个target依赖字节未变，无NumPy/SciPy升级。
- `target-wheelhouse-release/SHA256.json`已在本地组装核对21个依赖+唯一cpu.3候选；最小包不重复55MiB旧依赖，提供增量、原依赖SHA引用及组装脚本。原安装器保留，新prefix/target verify逻辑不去掉。
- 局部patch、源码清单、同进程取证、数值/停止证据、实际阶段回读器和一页操作卡随包。旧cpu.2 wheel与原始回放输入按原身份保留；新派生结果在独立目录。

现在停止交回复审。之后只有在新候选获审、用户另批当次范围后，才独立安装并作一次原60秒能力复核；目标同进程池数、资源预算、真机时窗/完整取数仍需现场证据。能力通过也不会自动进入12请求。没有设备/SSH连接、部署/重启、jtop/YET、风扇/保护/采样/TTL变化、模型研发或GitHub动作。

最终发布payload已独立解包复验：193条、11054数值字段与全部语义通过，最大差仍小于1e-8；对应wheel SHA与解包脚本SHA在`verification/independent-release-package-replay.json`。开发中间回执另置`verification/development/`，主验收仅引用`release`回执，避免同一候选开发过程的旧副本混入最终身份。
