# TTO Web UI v1.0 实施与验证报告

交付日期：2026-10-20。软件候选：`tto-web-ui 1.0.0rc1`；内含最小发布扩展的field版本：`0.2.4+web.1`。工作目录：`work/webui-v1`。

**已实现可安装、可运行的59009只读Web候选，包含紧凑指标、三大趋势、A事件、B来源折叠、完整C/D/E、真实只读G2-HOLD发布与成熟评分、follow/observe、访问保护和独立安装/回退。34项本地测试及最终离线安装后的浏览器检查通过。** RPM无可信测速证据，当前显示未确认；没有核实的现场建议曲线，默认建议PWM为null；没有任务runner时任务/并发未知。没有结构传感器、校准置信度或自动控制。**未连接设备、部署N305、发真实负载、重训、推送或创建PR；Linux开机恢复、N305资源与现场模型能力等待独立复审后另行授权核验。**

## 1. 实施与基线

完整阅读并保存附件README、00–05、contracts及reference，附件合同样例仅用于验证，没有接入生产默认页。用户本次明确的只读和现场边界优先于附件中的历史许可、旧效果图或示例数字。

原仓库HEAD为`97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。本任务没有切换分支、复位、清理、覆盖原工作区，未提交。全部新增实施在独立`work/webui-v1`；原有dirty工作、研究结果与CPU专项保留。适配选择依据与字段映射见`adapter-baseline.md`。

实际复用accepted `0.2.4+closeout.2`原wheel（SHA256 `de1c67c143c97733b9c14501253ef0216157462c77eff7bbee2124e146d5d9db`）。原件与逐文件身份保存在`baseline/`、`baseline-identities.json`。本次vendor仅三处差异：collector新增可选内存journal/continuous/信号拥有权；field runtime新增非阻塞公开发布及runner事实钩子；field软件版本更名。默认原采集调用不改变。差异逐文件SHA及patch见`evidence/accepted-source-comparison.json`、`patches/accepted-field-to-web.patch`。

冻结模型：`dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`。
冻结spec：`2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`。
原observer、spec与模型文件字节不变。没有重新开展拟合、CPU先导、模型选择、增益或控制策略实验。历史`candidate-files.json`原样保留，新软件身份使用独立`web-candidate-files.json`，没有修改旧清单掩盖差异。

## 2. 可运行链路与拥有权

后端aiohttp、前端TypeScript/ECharts，编译资源随wheel内置；运行不需要Node/CDN/外网、数据库、开发服务器或额外daemon。服务固定59009，先占端口再启动source；占用时明确退出，不停止其他程序。未配置来源也能打开等待页面，不启用样例。

`follow`消费已注册descriptor和同目录Unix socket；校验Linux boot/host-monotonic域，绝不扫描最新run或目录mtime，不额外访问设备。`publish-field`通过原field授权入口，将同一个engine/projection/observer的输出非阻塞发布；任务事件只消费原runner事实。Web启停不停止外部field。

`observe`在显式原生配置下取得原`/tmp/tto-observer-UID.lock`后创建唯一collector/quality/observer；同一用户的collect/shadow/field共用该锁。无Requester、模型列表GET、SSH或推理POST。collect结束/冲突有准确原因。Web关闭只停止自己创建的observe，信号不再被collector覆盖。未经共享锁的其他用户/旧软件不得并行observe，已有现场采集优先follow。

本地验证真实执行了：自建SocketIO/ESP GET端点 → 原native collector → 一次engine.process/I-02 → accepted projection/observer → allowlist adapter → Unix publication → **离线安装后的**HTTP/SSE → Chrome。测试值明确显示“本地回放样例（非实时设备）”。端点只在loopback，不含设备地址/凭据；没有推理model请求。macOS无法提供Linux boot身份，测试显式使用test boot并强制test_replay，不能借测试配置连接live。

## 3. 页面与数据能力

| 项目 | 已实现与含义 |
|---|---|
| 指标/三趋势 | 10个紧凑指标；温度、两rail功率、PWM各全宽；默认10分钟，可选5/30/60；缺口保留，同值新样本保留；图例、共用缩放/光标/事件范围；tooltip保留每系列实际样本时间 |
| A / B | 事件带按密集位置合并标签，可点击看时间/原因/次数；来源/事件/字段抽屉默认收起；重复事件计数、质量变化明确提示；逐核、内存、其他rail可搜索 |
| C 模型节点 | 固定G2的10节点与合同拓扑；TJ虚线表示测量校正；实线表示模型依赖；有效关系才流动，暂停/后台/减少动效停止动效；节点来源/状态可查；Ts/E均明确模型内部态 |
| D 预测对照 | 15/45/90秒分别真实传播并发布，目标时刻对齐预测与首个合格实测；MAE/P95/max低估/匹配及应到期数；待到期、缺标签、晚发、不可比单列；当前未来参考与历史评分分开 |
| E 运行语义 | 观察对象与TTO主机分开；热模型身份、过程/epoch、持续时间、Jetson RAM、Web自身CPU/RSS；standalone无任务记录时明确未知；field可接任务登记、阶段/槽位/客户端在途，服务端执行/排队仍未知 |

**真实RPM能力：**原源报数没有足够测速valid证据。`rpm=0, running=true`反例当前value仍为null、unverified；原0可作为上次观测查阅。不推断停转，不由PWM换算。未来接受可信RPM需新的证据/合同，本版未伪造。

**单位与质量：**rail current mW÷1000为W，average独列且平均窗未知，不合成整机总功耗；RAM/SWAP沿用MB。NVML独立sample ID/年龄/有效期限，不因新CPU/WS包续龄。普通有效0保留、缺失不补0，新invalid立即撤旧valid，不回捞旧缓存。源失效即撤当前，心跳不续TTL；跨run/epoch曲线断开、误差不混合。

**结构测温与置信度：**未新增结构传感器；Ts不叫结构温度、E不叫室温。没有校准概率、95%置信带或模型驻留推断。平稳需求无合法provider和固定参考，明确“本轮未计算”，index不冒充PWM。

**PWM建议：**仅实现`CURVE-REFERENCE-v1`只读provider：经核实的设备/fan0/温源/源配置SHA/曲线SHA，配合当前valid TJ、+45秒HOLD、正常模式与保护上下文，在原曲线域内插值。未知/缺失/不匹配/域外均null及原因，不外推、不加控制阈值，不写设备。没有现场曲线供验证，**本次没有产生可当现场依据的建议PWM数值**；数值分支只在合成单元测试中验证，未把主板target_duty当建议。

## 4. 预测provider与成熟规则

Tf起点锚定当时合格TJ，Ts/E来自同一因果观察器；两rail及conditional PWM按HOLD情景冻结。直接复用accepted `ThermalObserver.mean_step`矩阵指数，不改θ、数值模型或CPU先验。每个新有效TJ最多每秒一次，三种时距各算一次。

origin是观测起点，issued记录实际计算/发布时间，target=origin+horizon；input cutoff可查。发布晚于目标不能计作在线预测；test replay与live明确区分。未来输入扰动不能修改已发布值。标签为同run/source epoch/model/spec的目标后首个有效accepted TJ，最多+2秒；误差=predicted−observed。迟到/缺标签/不可比不偷偷进入同一个分母。丢发布帧导致可能错过首个标签时，已有pending标为不可比；不把下一帧伪装为首个合格标签。

滚动统计严格同horizon/model/spec/run/epoch/HOLD/窗口。增量返回只缩减records，summary仍用整个窗口集合；标签更新保留±2秒覆盖。未把tracking当准确率，未沿用离线Ridge或oracle成绩。数值测试以独立solve_ivp对照三时距（1e-8容差），实际安装API三种时距均有成熟记录；**这些合成误差只证明软件流程，不证明现场预测准确或控制收益**。

## 5. 资源与N305开销

使用单进程aiohttp；无React常驻服务、数据库、原始日志副本或定时训练。数值库在来源就绪时才加载，等待页不加载NumPy/SciPy；数值线程限制为1。显示1Hz，质量过期检查0.1秒；新数据/显示周期/到期才重建快照，原源采样/调度/TTL完全沿用。多浏览器只加显示流，不加采集器/观察器。

显示队列8、SSE最多4、重连历史64；源回调只入有界deque，不等待socket/浏览器。历史最长60分钟且每序列18002项，预测11070项、事件1000项，标签随预测出队清理。浏览器只增量请求曲线/预测；暂停只冻结画面。observe内存journal不产生无限原始日志；systemd错误日志限流，无访问日志。不清理原实验数据，Web版本目录仅保留供人工管理/回退。

性能修复及负面证据保留：早期全量历史传输/完整预测复制导致CPU与RSS增长；第一次独立Web计量1057秒，CPU均值5.495%单核、RSS峰值180.91MiB，未完成30分钟且CPU超预算，**不算通过**（`resources-installed-before-delta.json`）。随后改增量传输、只复制6条当前摘要、延迟数值库和单线程；发现并修复环形预测淘汰时标签元数据残留。第二次计量778.52秒CPU均值4.626%、RSS峰值97.03MiB，尚未满30分钟，仍不算完整通过（`resources-installed-before-refresh-gating.json`）。其CPU随历史上升，进一步定位到每0.1秒无条件重建整份快照：改为新数据、1Hz显示或质量截止时才重建，期限检查仍为0.1秒，GET快照仍实时刷新；新增测试验证无源安静期不重复重建且到期及时撤值。所有修复针对开销根因，没有降低源采样、放宽TTL或改模型。

30分钟持续计量完成：1800.85秒、1779次采样、0错误；**Web新增follow进程平均CPU为3.434%单核等效，RSS峰值97.5MiB**，达到本机5%/192MiB预算。证据为`resources-installed-final-30min.json`，主机/口径为macOS ARM64、一个现有Chrome页面、独立自建native source；不包含Chrome/原生观察器成本，不是N305成绩。初始RSS44.20MiB，末值97.5MiB，随着保留历史增长仍有明确上限；30分钟不代表无限长期稳定。

透明版本边界：这轮计量使用最后的快照/增量/缓存算法，随后修正E模块runner分支文案、补healthz PID与安装器就绪核验，清理未引用旧构建文件，并修复启动时TCP地址复用选项。来源、冻结数学、TTL、缓存、刷新与预测代码不变；当前无runner场景文案输出相同。差异与测试版本身份在`evidence/resource-tested-identity.json`、`evidence/resource-final-equivalence.json`及patch中逐项列出。相同数据运行实现的两分钟复验为120.20秒、111采样、0错误、CPU均值2.242%、RSS峰值82.06MiB；之后唯一运行文件差异是CLI增加SO_REUSEADDR启动选项，模型/数据路径与前端完全相同。最终wheel完成完整34项测试、真实CLI快速启停/占用端口回归，并实际测得无源等待60.19秒、60采样、0错误、CPU均值0.638%、RSS峰值40.16MiB。**不把不同构建轮次合并声称同一轮30分钟计量**。

本轮构建检查还发现setuptools保留了5个旧前端构建文件，已清理本任务自己的build目录，并增加wheel成员必须与新清单完全相同的校验；最终无多余/遗漏文件，wheel为507216字节。

前端本地静态资源gzip合计357337字节（约349KiB），低于3MiB预算；原JS约1MiB的Vite chunk提示保留，构建成功。wheelhouse包含cp310 Linux x86_64和本次主机cp312 macOS ARM64的离线依赖，不需要N305构建前端。安装器不升级Conda base/原TTO环境。原生观察器、外部field和浏览器开销与附加Web分开看；本次持续预算计量为follow新增Web进程，未做observe合并进程的30分钟成本拆分，也未计远端浏览器。上述本机结果不能外推N305。

## 6. 实际验证与未执行项

最终完整测试：`34 passed, 6 warnings in 14.42s`，见`evidence/tests-final.log`。6条是aiohttp测试app使用字符串key的NotAppKeyWarning，不是运行错误。未重复整个历史研究测试，不把验收条目数当测试数。`frontend-build-final.log`为TS类型检查和生产构建；`build-candidate-final.log`为真实wheel与依赖打包。

离线临时prefix实际安装/升级并加载61个新身份文件与编译静态资源，通过`identity.verify`；运行入口来自prefix独立venv。默认system unit自动enable/restart命令与用户/目标构造做mock测试；安装器再核对本机healthz PID与该unit MainPID，Type=simple的active不再被当作端口就绪。就绪检查不继承HTTP代理，并在HTTP前确认配置地址属于本机；错误PID必须失败，临时unit已生成；本机macOS未提供可执行的Linux/systemd验证环境，**未执行Linux systemd语法工具/开机/用户登出恢复**。不能把模板或mock当实际Linux启动证据。快速重启真实检查复现了旧进程退出后TCP连接状态占用监听端口的问题（`port-restart-diagnosis.log`：无监听者时普通bind报EADDRINUSE、SO_REUSEADDR可绑定）。已增加该启动选项；真实CLI连续启动/退出两轮，并在每轮验证第二实例仍拒绝占用，纳入最终34项测试，未用睡眠或kill他人规避。临时prefix服务none的真实启动、访问、升级/回退另有证据（`install-final.log`、`install-rollback-upgrade.log`、`install-rollback.log`，回退实际校验旧版60文件，新版61文件）。Linux CPython3.10/x86_64依赖也完成仅离线解析dry-run，21个包均可从wheelhouse满足（`linux-wheel-resolution.log/json`）；这是依赖解析，不是Linux二进制执行。

最终安装浏览器1440/1920/390截图与检查：10指标/10节点、默认折叠、暂停稳定、15/90时距、节点详情、逐核搜索、减少动效、无整页窄屏溢出、C/D/E保留、全屏均通过。额外实际点测5/60/10分钟范围、事件点击详情、tooltip样本时间和重置缩放通过且无pageerror（`browser-extra-interactions.log`）。截图为合成软件链，醒目标记非实时设备；没有拍真实设备效果。浏览器源码文本经转义，公共DTO只allowlist，没有raw binding/header/prompt/回复/私有路径。

| 验收项 | 本轮结果 / 证据 |
|---|---|
| U01–U02 | 本机浏览器通过三宽度与紧凑单位；`output/playwright/*-final.png`、browser-installed-final-checks.log |
| U03–U05 | 共用图组与各自时间、暂停/全屏/图例、固定拓扑/减少动效；浏览器交互及源实现。非人工验证所有物理数据的时间同步能力 |
| U06–U08 | 等待/降级/无任务/无建议均保持CDE，抽屉/逐核字段搜索；schema及语义测试、等待/断源截图 |
| D01–D04 | 单位、NVML独立期限、有效0、RPM反例、新采样vs缓存：test_semantics.py |
| D05–D06 | 断连/epoch/模型SHA/外层clock/未知域拒绝：semantics、service、field_hook |
| D07–D10 | 三时距独立数值/因果/标签/误差/分母/晚发/回放：semantics、boundaries；实际安装DTO |
| D11–D13 | 仅合成合法曲线数字；现场映射缺失明确null；Ts/E/需求/置信度与runner事实语义测试。真实建议与测速仍待证据 |
| S01–S02 | 原生自建端点→quality/observer→API/SSE→最终安装浏览器；follow生命周期不停止外部生产者 |
| S03 | observe共享原锁；冲突测试0网络；无Requester；实际自建集成 |
| S04 / S08 | 有界队列、慢客户端resync、SSE Last-Event-ID、无新数据按TTL撤值；service/boundaries |
| S05 | 临时prefix离线安装/真实入口/静态身份；端口冲突；回退/升级本机测试。Linux/systemd真实开机待验 |
| S06 | 本机默认、LAN匿名拒绝/登录退出、Host/Origin/业务写入拒绝、秘密allowlist；本地API测试 |
| S07 | 资源策略、负面证据与最终持续计量单列；N305/更长实际运行待验 |
| S09 | 墙钟跳变事件不参与单调计算；时钟域拒绝；独立新身份和accepted patch；没有重写历史身份 |
| S10 | 所有活动限本机/自建端点；无设备、真实推理、CPU先导、部署、Git发布 |

**源请求次数未随浏览器增长：**真实native observe集成测试在4个SSE客户端下仍仅1个SocketIO连接，约6.4秒fan GET为6–8、temp GET为1–2，与原1秒/5秒调度相符；第五SSE拒绝；POST/model GET均0。共享锁与follow不拥有生产者分别验证。30分钟计量源完整生命周期（含准备/收尾）为fan GET 1912、temp GET 383、推理POST/model GET/发布丢帧均0，保存`installed-chain/counters-30min.json`。最终短测源总计另存`installed-chain/counters.json`，不将这份软件端点计数当真实设备记录。

保留测试中的失败和修复日志：早期端口/路径/浏览器窄屏问题、在已有自建观察锁运行时误跑collector测试导致冲突，以及macOS SciPy1.15.3 wheel的dlopen失败。最后改用与本机accepted环境一致的Darwin SciPy1.14.1；Linux锁仍为accepted wheelhouse1.15.3，未在本机宣称执行过Linux二进制。

## 7. 安装候选与复审入口

交付ZIP包含：独立源码、vendor/accepted patch与原wheel身份、编译前端、Web wheel/离线依赖与锁、实际DTO/schema、安装/服务/回退脚本、测试与截图、原始PRD与基线。`candidate-identities.json`逐项校验安装内容；外层交付清单和ZIP SHA另附。排除开发venv、node_modules、临时私人配置、工具缓存；没有打包真实凭据。ZIP同目录提供`.zip.sha256`；`delivery-receipt.json`为外部封包读回结果。

推荐复审顺序：先首屏能力/未验范围 → `adapter-baseline.md`与accepted patch → `state.py`的发布/标签/统计 → `source.py`拥有权和背压 → installer默认服务命令 → 最终测试/实际DTO/资源 → 三宽度截图与一页操作卡。源码全部在独立目录，未推送或创建PR。

本轮交回软件候选后停止。独立复审通过不自动授权设备连接、N305部署、启动真实负载或改变天山OS风扇/曲线/gain/保护/采样/TTL。后续由用户决定现场安装与监看。本任务创建的本地服务、合成源与浏览器会话已停止，59009没有监听者，见`cleanup-receipt.json`。

页面证据：[1440](output/playwright/1440-final.png) / [1920](output/playwright/1920-final.png) / [390](output/playwright/390-final.png) / [最终断源撤值](output/playwright/source-disconnected-final.png) / [最终等待页](output/playwright/waiting-final.png)。
