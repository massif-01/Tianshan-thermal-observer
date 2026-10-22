# TTO Web UI 1.0.0rc4：模型状态历史实施与验证报告

日期：2026-10-21。结论：**模型状态历史后端增量候选已完成本地实现、最终 wheel 验证和交付包回读，可交独立复审。** 首页沿用封存 rc3 静态资产；Sonnet 新首页未集成，不属于本轮完成声明。

## 1. 候选身份与范围

- 最终 wheel：`tto_web_ui-1.0.0rc4-py3-none-any.whl`，517876 字节。
- SHA256：`076e7bf5dd6335b32d0f4de254365bb85dc4f70e77470fae678fec3b4b29ef79`。
- 对照 rc3 wheel SHA256：`5f4c9fe5f28e8ab892c83b1309f8b91ad8d6e828489f116f17c4f67c8a35b910`。
- 冻结模型：`dff52c3e641d54bd07f0b5543909166e11a5d935c92474ab9f7b4a08c5396ff0`。
- 冻结 spec：`2080adcf20773650299def2bb0f3ebdb9f87d8f85281d5b87a99d8b406c83c6b`。
- 包内运行文件 67 项，另有其身份 manifest；最终 ZIP hash、字节数、包内核对数量和从 ZIP 安装后的导入路径见外部 `TTO-WebUI-v1-rc4-交付核验回执.json`，避免把 ZIP 自身 hash 放入 ZIP 形成循环。

实施目录为 `work/webui-v1`。本轮保护核对的 frontend/vendor/原始 requirements 文件共 72 项，均未修改；没有执行前端构建。当前产品静态文件与 rc3 wheel 中资产逐字节相等。原仓库其他 dirty 工作保留，没有 reset/clean/stash/commit/push。

本轮没有连接设备、部署 N305 或系统服务、发真实负载、训练/CPU 先导实验、修改天山 OS 风扇/曲线/gain/保护/采样/TTL、推送或创建 PR。

## 2. 实现结果与原因

`state.py` 新增一份共享联合行 deque：TJ/Tf/Ts/E 四列共享采样时间和来源，最多 18002 行、裁剪一小时。三个模型序列在查询时投影，避免三份 dict 历史常驻。

数值只在新且未重复的合格 TJ 上记录，取同包观察器完成校正后的状态；tracking/degraded、有限状态、TJ 合格、既有截止时间未到期均须满足。`t=TJ.as_of_elapsed_ms`，与包 input-origin 时间按 0.001ms 浮点容差核对，并验证 TJ 样本标识。tick、其他指标发布、重复请求不生成模型数值；不新增模型求解。

失效阶段、TJ 无效、非有限状态、时刻不匹配、发布缺口、断连/结束和静默到期都形成显式 null。连续失效合并断点；断点同位置优先，之后源时间不晚于断点的迟到样本不回填，待更晚的新合格 TJ 恢复。过去合格历史保留，不用历史末值续当前 TTL。

新模型 id 为 model.Tf_C / model.Ts_C / model.E_C。请求任一新 id 时启用 tj_model 共同抽样；同请求的 TJ 为模型采样锚点视图，独立 TJ 和默认 ids 保持原行为。共同选点保留四分量及 TJ−Tf、Ts−E、Tf−Ts 的桶内极值、首尾、全部缺口与段边界；强制点可超过软 max_points，响应明确 original_points/returned_points/soft_budget_exceeded。部分模型请求仍使用同一固定组索引。

run/epoch/model/spec 切换清缓存和去重，服务重启更换 service_epoch。`/series` 返回完整 service/run/epoch/model/spec 身份；bootstrap 新增历史能力和可用模型序列，当前 metrics 目录含义不变。新增严格 series schema、三个示例及增量合同；没有把历史塞进 dashboard 当前快照合同。

TJ−Tf 明确为校正后残差，不混称预测误差或 innovation_C；E、Ts−E、Tf−Ts 为带符号温度状态分解，负值原样保留，不暗示热量占比或实测结构/室温。预测起点、成熟标签、建议算法与冻结观察器源码未修改。

安装器的版本目录从候选唯一 wheel 文件名取版本，消除原先硬编码 rc3 的交付标识问题。本次发行用独立 candidate-rc4 staging，只含一个新的 Web wheel，保留原封存 rc3 文件。

## 3. 最终 wheel 验证

安装使用 `tools/install.py --service none`、独立 `/private/tmp/tto-web-rc4-final` prefix、CPython 3.12/macOS ARM64，依赖通过 `--no-index` 从 wheelhouse 安装。源码测试目录通过显式 installed 模式只提供测试夹具，产品模块从 prefix 的 site-packages 导入；新增测试检查导入路径和身份 manifest。

| 方案验收项 | 最终身份结果与证据 |
| --- | --- |
| T1 同采样、去重、真实 observer Tf | 新增合同测试通过，特别断言 Tf 不被预测起点 TJ 替代 |
| T2 阶段/有限性/TJ/截止资格 | provisional、unavailable、invalid、NaN/Inf、接收已过期及恰到期均为 null |
| T3 断源/过期/发布失败/恢复 | 真正 Publication→follow→HTTP 联合测试通过；显示编码异常经既有 DisplayPublisher 传递；浏览器看到静默到期 null、新样本恢复 |
| T4 迟到与同位置冲突 | 已公布断点之后的早到时刻不回填；缺口优先、时间单调、重复 refresh 不堆积 null |
| T5 身份 | run/epoch 清空、冻结不匹配拒绝、服务身份变化；模型/spec 合法组切换在严格限定的测试合同替身下覆盖，未放宽生产冻结校验 |
| T6 有界及共同抽样 | 超一小时裁剪、18002 上限、短有效段、密集缺口、差值独有极值、部分模型同索引通过 |
| T7 schema/兼容 | 实际 HTTP、无源响应及三个示例通过 schema；错误 reason 和未知顶层字段被拒绝；旧默认 ids 保持 |
| T8 数学语义 | 合成负差值保留；已有保存记录只读排序统计完成，详见下一节 |
| T9 原行为 | 最终安装环境全套 **72 passed**，包含 24 项新增历史/合同测试、原配置错误/有效性/结算/安装/CLI 等回归；网络恢复两个场景及真实浏览器 D 跨 epoch 旧响应回归通过 |
| T10 构建与交付 | 同一最终 wheel 离线安装、浏览器、资源短测；最终 ZIP 解包逐项核对并再次离线安装、真实 CLI 启停，见外部回执 |

执行命令与原始输出在 `evidence/history-rc4/tests-installed-final-72.log`、`tests-final-contract.log`、`install-final.log`、`build.log`、`recovery.log`。最终 72 项用时 20.71s；8 条为既有 aiohttp NotAppKeyWarning，没有新增运行依赖来消除此非阻塞提示。

恢复补测使用实际 observe/collect 生命周期和可核对的惰性传输/锁替身，保留 reconnect_max_attempts=10，只缩短测试退避；没有连接设备、占用原观察器锁或证明现场恢复原因。结果在 `recovery/observe_recovery_result.json`。

浏览器为独立 Chrome，产品 API/static 来自最终安装。最小历史验证页由测试夹具单独挂载，不存在于生产路由或 wheel 静态目录。发布缺口后四条曲线从 4 个 polyline 变为 8 个独立段；静默末值为 null；恢复样本保留 degraded 阶段。保持旧 HTTP 响应并注入 777.123 哨兵，同 run 从 epoch 1→2 后清图且迟到响应被忽略。原 D 回归同 run 从 epoch 3→4，旧预测响应实际返回后评分仍为空，无哨兵回填。DOM、具名可访问性表格、实际可访问性树与截图共同核对；证据为 browser-history.json/log、browser-D-epoch.json/log、browser-accessibility.txt 和 output/playwright 中 rc4 截图。

## 4. 资源与保存记录检查

没有新增采集器、观察器、数据库、线程、依赖、常驻日志、SSE 历史广播或额外模型求解。复用既有期限检查；空闲时不重建整份历史。

| 同口径本机短测 | rc3 基线 | rc4 最终 wheel |
| --- | ---: | ---: |
| 时长 | 120.68s | 120.43s |
| Web 平均 CPU（单核等效） | 2.682% | 3.024% |
| Web RSS 峰值 | 151.27 MiB | 169.89 MiB |
| 新增联合缓存存活分配 | 无 | 8.086 MiB / 18002 行 |

rc4 满足本机平均 CPU ≤5%、RSS 峰值 ≤192 MiB、新缓存 ≤16 MiB 的门槛。相对基线 CPU 增加约 0.342 个百分点、RSS 峰值增加约 18.63 MiB；RSS 包含请求临时分配及分配器驻留，不能与缓存存活分配混为同一口径。多轮历史查询后的存活分配保持约 8.10 MiB；清空后约 20 KiB，不保留整表副本。

短测使用独立合成发布进程、一个原产品 Chrome 页面、相同 1Hz 源流与刷新节奏；两者预填既有数值历史 18002 行，候选额外预填联合历史 18002 行。候选每 2 秒增加一次共同历史请求，最大实测 17.58ms、226633 字节、252 个共同索引。source 原观察器成本单独记录在 resources.json；Chrome JS 堆在浏览器证据单列，未进行 Chrome 全进程树 RSS 汇总，不包含在 Web 过程预算中。

这是受控历史预填的短测，不是实际等待一小时，也不是全部预测/事件缓存同时填满的最坏情况测试；预测和事件仍按真实短测源流增长。120s 不证明长期/N305 稳定性，不借用旧版本 30 分钟成绩。首次非合格夹具计量已中止，未混入通过结果。

已有保存状态只做 JSON 扫描，不运行观察器或新回放。冻结身份、tracking/degraded、合格新 TJ、同 TJ 来源及去重后，两组分别 **2697/2697、51/51** 满足 Tf≥Ts≥E；104016039/2204368 字节输入的 SHA256、排除计数和规则在 ordering.json。有限样本全部有序不能保证未来恒有序，负差值仍须支持。原始大文件未复制进候选，复核可用现存相同 hash 输入；不将排序比例当预测准确率或新现场证据。

## 5. 失败证据与交付闭环

保留 preflight/failures.json 与原始失败输出：来源/服务未就绪就探测；Chrome 沙箱启动限制；小数秒夹具漏掉 5 秒控制上下文；发布缺口夹具同时间重复造样触发既有 feature times must increase；旧 D 脚本与独立发布控制响应形状不同；全套测试与自己的 59009 浏览器夹具冲突。修正测试夹具/调度后重新验证，没有改生产采样、模型或 TTL 来绕过失败。一次浏览器收尾导航与停止服务重叠导致拒绝连接，随后顺序执行可访问性采集和关闭。

源码和 wheel 在上述验证期间保持同一身份；后续只调整测试夹具、文档及封包脚本。最终 staging 同步最新测试/工具，更新 candidate-identities.json 和 PAYLOAD-MANIFEST.json；ZIP 外部回执记录源码与 wheel 字节核对、报告/卡片一致、从该 ZIP 新 prefix 离线安装及真实 CLI PID/version/退出码。旧 rc3 封存包未覆盖。

交付文件：新安装候选 ZIP、独立最终 wheel、本报告、一页操作卡、前端接入卡、完整差异/新合同/测试/证据以及外部交付核验回执。复现构建入口为 tools/build_history_candidate.py，需作者工作区保留的 rc3 封存 wheel 和已准备构建环境；安装只依赖交付 wheelhouse，不需要前端构建环境。

**停止点：本地后端候选交回复审。Sonnet 新首页集成、Linux/systemd 实际执行、N305 实际安装/只读监看/断源恢复/资源核验均未执行，等待后续授权。本轮自建服务和测试浏览器全部关闭。**
