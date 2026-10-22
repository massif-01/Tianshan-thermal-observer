# TTO fan/status 根因与本地候选 R2 报告

本轮：TTO-REVIEW-R2-20261018 / Issue #9。结论：**离线调查与诊断候选准备完成；现场227次超时的根因仍未定位，不宣称现场已修复。** 没有证据支持直接改超时、TTL、缓存、锁或风扇行为。本地候选只补齐客户端取证缺口，不能当作吞吐改善补丁。

## 1. 授权、隔离与基线

本次R2从未开始状态独立执行，不恢复历史live授权或旧M override。已读README、00、02、04、05及此前独立复核；GitHub Issue #9正文和评论只读回读，未修改Issue。Issue维持开放含义，不因patch存在视为完成现场验收。

全部新增文件在 `investigations/issue-9-r2-20261018/`；原脏工作区未stash/reset/clean。两个独立本地checkout为 `work/TTO-reference` 和 `work/TianshanOS`，另在 `work/runtime-024/tto` 保存**匹配现场包的隔离运行源码候选**，没有用当前main覆盖它。

- 本地TTO Git参考：`97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。现场不是此commit的声明：Y/M manifest均为已安装0.2.4，source identity `a6f98d9761b0f7efafea9ba642bd83e1afa5723c7bee1815dbd0be4303457664`。
- Y vendor内22个Python源码逐一与manifest核验通过；候选wheel的原collector与现场collector相同，SHA `d08c1f0b6187831e728420094137afa070f328d9b0252f3662a992443b2b0b5b`。两轮source identity完全相同。
- 固件代码参考为本机仓库只读clone的 `88dd98079ce14d2180afef8efc41d742735568da`。只读查询的远端main为 `002d3a7b8ddb75d5a43c0046382d1335f49fbfc0`；二者都**不能冒充现场固件**。两个现场manifest的firmware_identity均null。
- 交接包28个清单文件SHA/字节核验通过；Y/M/候选原ZIP与SOURCE-MANIFEST一致。原始数据不改写。见 `analysis/runtime-source-verification.json`。

本轮没有设备连接、SSH、真实推理、部署、刷机、重启、控制设置更改、模型拟合、提交、推送或PR。外部访问仅GitHub只读与本地测试依赖下载，HTTP测试全部绑定127.0.0.1临时端口。

## 2. 从原件复算的事实

| 指标 | Y / 1ae9a7d7 | M / 637f114b |
|---|---:|---:|
| fan请求/成功/TimeoutError |1256/1029/227|2508/2508/0|
| fan成功RTT p50/p95/max，ms |30.570/1676.155/1995.733|11.555/14.066/85.535|
| fan失败RTT min/p50/max，ms |2000.522/2001.272/2007.880|无|
| fan相邻成功观测间隔>2.5s |349|0|
| fan成功间隔最大，s |4.039387|1.074843|
| temp请求/成功/失败 |370/370/0|503/503/0|
| temp成功RTT p95/max，ms |42.848/89.910|13.072/31.051|
| fan调度跳过slot |591|0|
| 成功fan中的temp_stale=true份数 |3|1|
| 队列丢弃/峰值项数 |0/2|0/2|

两轮request_timeout=2s、connect_timeout=5s、fan周期1s、temp周期5s相同。总超时2s包含连接/排队等，connect配置5s不会使总预算变成5s。connector为每endpoint独立一个，最多两条ESP HTTP并行；不是配置legacy max_inflight=1就全局串行。没有自动重试；下一轮周期请求不是隐式重试。错过slot跳过，不追赶。

成功响应的**重新序列化JSON大小**：Y fan456～514字节，M471～515字节，远小于65536字节接收上限；原始wire大小未记录，不把重序列化字节当wire证明。成功JSON字段/duty_valid未被更改。Y原quality账本为1843个new_samples、3个duplicate；未把重复传输当新TJ。

请求发出相对计划时刻的Y p95仅2.201ms，最大191.254ms；失败总RTT集中在约2s。CPU单核采样峰值Y5.99%、M7.99%，队列未丢弃。它们不支持“整段主机持续过载”作为现成结论，但低频采样不能排除瞬时卡顿。

所有227次超时都落在**最近temp请求发出后1～2秒的整数分箱**；此箱370条fan中227次超时。0秒箱369条、4秒箱368条均无超时。0条temp请求时间区间与fan失败区间相交。见 `fan-temp-phase-association.json`。这是同主机时间关联，**不证明temp请求因果，更不证明UI在刷新**；两个周期及跳slot本身也影响分箱。

首次fan超时在UTC `2026-10-17T16:32:08.143912`。首条推理之前已有26次fan超时；227次中18次与模型请求区间相交、209次不相交。不能把问题直接归因于推理负载。仪表、浏览器操作、板端任务竞争没有足够同步台账。

349个间隔与227个错误不是相同事件，不相加。成功间隔这里用observation mono，endpoint received mono相差微秒级，均保存原字段；不能将2.5秒后的未知尾部解释成硬件停转。完整逐请求时间线见 `Y-http-timeline.csv`、`M-http-timeline.csv`。

## 3. 原因分级和链路追踪

**已证实**：Y出现endpoint选择性HTTP总预算超时和成功PWM新鲜度空隙；源代码、超时配置与M相同；错误日志只保存异常类和总RTT，缺少连接、响应头、正文阶段。现场227次不能事后分配阶段。temp_stale成功快照与HTTP失败是不同现象。既有独立核对中的349/227/3等数字复算一致，未推翻其原结论。

**源码/模拟支持、现场未证实**：

1. 客户端 `sessions()` 使用独立连接池并复用keepalive；pool等待、建连、等响应头和读正文都可能耗尽total预算。取消/超时后async context负责释放；当前没有证据证明连接泄漏。
2. ESP-IDF 5.5.2参考的 `httpd_main.c` 在同任务枚举session并调用 `httpd_sess_process`，后者同步 `httpd_req_new`/delete。慢handler或未完成读/写可能阻挡其他连接；host串行资源锁能复现队列超时。**模拟锁不是板端真实mutex复现**。
3. `ts_webui_api.c` 同步调用 `ts_api_call` 后序列化、发送；API注册表锁在取出handler后释放，不能先认定全局API锁覆盖整个handler。
4. 参考 `api_fan_status` 读取fan后调用 `ts_temp_get_status`。`ts_fan_get_status`逐字段读缓存，没有可指认的长I/O；`ts_temp_get_status`以portMAX_DELAY取温度mutex并复制状态。等待机制存在，但同轮temp全成功，未见板端锁等待时间，不能认定此锁导致227次错误。
5. WS订阅代码也可调用同一API，HTTP发送可占单任务；无现场UI/连接日志，不认定“手动刷新冲突”。

**未知**：当时ESP32固件SHA/IDF配置、是否TCP重传或连接重建、请求是否抵板、板端handler排队/锁等待/发送时间、并发UI/WS会话、无线链路变化、body是否部分到达。当前源码的fan逐字段读取也不能据此宣称具备跨字段原子快照；本候选不触碰状态快照或锁，因此不引入“半更新换提速”的改法。

## 4. 最小候选：只补取证，不伪装修复

`deliverables/collector-diagnostics.patch` 只修改匹配0.2.4的 `tto/collector.py`，新增每次poll的 `poll_diagnostics`：last_phase、同机单调事件时间，以及成功完整读取后的response_bytes。

阶段包括request_start、connector_queue/acquired、dns、connect/connection_ready、connection_reused、request_headers_sent、response_headers_received；进入read后为response_body，JSON成功解析后为complete。response_headers_received不是首TCP包；request_headers_sent仅说明客户端发送完成，不证明服务器已经进入handler。

原来都只能标TimeoutError的反例：延迟响应头与正文半包均超时；新候选分别保留headers_sent和response_body，pool取消保留connector_queue。仍无法仅凭客户端区分TCP重传、固件排队和handler慢，这是明确边界。

success/error/cancel三类记录携带diagnostics；原异常类、计数、取消行为保留。未记录URL、认证头、payload；测试放入假Bearer头，确认不进入阶段记录。原payload原样交付，不缓存、不制造默认值、不续龄PWM、不改变TTL、间隔、2s预算、connector上限或控制语义。每poll增加少量trace回调与事件数组，增加日志/CPU开销；不能承诺零开销。仍受原接收/队列/磁盘预算限制，部署前需核实际长期资源开销。

此补丁是**取证能力候选**，不是已证实的超时性能修复。如果没有新阶段证据，本轮不应盲改keepalive、延时、HTTP服务任务/锁范围。没有固件修复候选，因此不做无关ESP-IDF全编译，也不假称已构建固件。

## 5. 验证与可复算范围

基线与候选各8个host/loopback测试均通过（共16次）：正常读取及复用、响应头超时、正文超时、同池排队取消与恢复、串行服务资源排队、并发一致响应、超大body/重定向恢复、真实collector路径的独立fan/temp读与超时取消清理。最后一项只启动loopback假采集，最大inflight=2、end_inflight=0，fan失败不阻止temp成功。host一致响应测试只验证假服务返回，不证明ESP32快照原子性。

初次基线测试0.35秒窗口被冷导入psutil阻塞导致断言失败，失败日志保留；在计时前导入依赖、将假服务窗口设0.6秒后，基线/候选同条件通过。此测试环境原因不冒充现场原因。

运行环境：本机CPython3.14，aiohttp3.11.18与候选锁版本相同，psutil7.0.0、socketio5.13.0。并非目标N305 CPython3.10的整套环境等价证明。`py_compile`通过，patch对原包应用检查通过，无whitespace错误。证据包展开后重跑分析与派生接口，6项输出逐字节一致，见portable-replay-verification.json。

复算：

```sh
python3 scripts/analyze.py
python3 scripts/phase_analysis.py
# 在独立venv安装 aiohttp==3.11.18 python-socketio==5.13.0 psutil==7.0.0
python3 tests/loopback.py baseline
python3 tests/loopback.py candidate
python3 scripts/source_health.py
```

所有命令均从证据包展开根目录执行。测试只运行127.0.0.1假服务；不能把测试日志中collector固定提示文字当成真实设备采集。原始Y/M不重采、不插值、模型不训练。包内仅保存通讯复算所需的原run子集，完整原件以用户交接包SHA为准。

## 6. #10只读接口与就绪

只选一种接口：离线派生JSONL `analysis/source-health-Y.jsonl`，5319条，引用原始observation，不建立新服务或额外轮询。`scripts/source_health.py`使用未修改0.2.4 engine处理同一保存流。

- identity：run/config/collector哈希、firmware=null、model=null、spec与观测截止；不知道不填正常。
- measurement：TJ/各rail来源、有效性与到期；PWM最近成功引用/真实接收时刻/年龄/到期/raw_valid。保留旧值仅用于追踪，过期绝不续龄。
- safety：过期或读取失败后guard/fault/mode/binding为null，不把unknown写false。964份过期PWM派生快照全部raw_valid=false，未知安全字段检查通过。
- observer：uninitialized，明确归#8；本线不提供Tf/Ts/E。
- permission：offline_replay，formal_field_authorized=false。
- communication：历史错误阶段明确unknown_historical_no_trace；未来新候选由poll_diagnostics提供阶段。

就绪拆分：可用于#10离线状态消费及错误恢复演练；诊断patch可纳入隔离研究环境复审；不许可现场负载，不表示模型或安全已就绪。Issue开放不应阻塞#8/#10软件研发。

## 7. 最小现场取证与回退（尚未执行）

之后另获授权才执行：先确认真实固件SHA/构建配置和客户端候选hash；不重启服务以追求干净起点。沿用唯一collector，不叠加第二轮询或自动负载。记录候选每条连接阶段及接收长度；按run和同机时间捕获TCP连接/重传/响应边界，抓包须剔除认证信息。板端仅对status路径记录不含正文的到达、handler进入、temp锁前后、快照完成、序列化和发送返回时间及socket id；只在匹配源码、有授权时构建部署。记录已有UI/WS客户端连接、正常操作与订阅频率，不能先主动制造危险压力。

先用原1s/5s轮询复现一段有界状态读取，保留异常及恢复；不以延长超时/TTL作为成功标准。只有服务端阶段或TCP证据能把某类延迟定位到具体资源，才形成相应完整修复；若涉及控制/保护/接口含义改变，先交方案。

若后续候选部署导致资源异常或兼容问题：停止唯一collector，保留新run，恢复原0.2.4 collector源或完整原安装包；不擦记录、不动模型/固件。实际安装、停止和回退均需当次现场授权，本轮没有执行。下一次只需提供固件身份、同一故障窗口的客户端阶段与对应TCP/板端时间线，不要求先重跑完整热实验。
