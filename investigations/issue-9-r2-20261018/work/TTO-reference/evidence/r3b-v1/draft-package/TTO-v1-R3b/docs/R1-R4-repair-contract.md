# TTO-REPAIR-v1.0：本轮合同补充

软件0.1.1；原方案的只读、身份、新鲜度、成功PWM、特征、Ridge、时距、资源和隐私合同继续有效。原0.1.0交付保留为历史起点，不作为返修候选。

## R4 实际握手

锁定aiohttp3.11.18，不升级依赖。会话局部TraceConfig核对实际请求的origin/path/method，并在request_redirect信号处关闭3xx响应、抛出拒绝；信号发生于跟随Location之前。ws_connect不接收allow_redirects参数。原HTTP不跟随策略、TLS验证、Socket.IO心跳/重连、polling两个传输槽、ESP32单在途GET保留。测试的决定性证据是跨源及同源未授权路径目标请求数0，不以删掉header或事后报错代替。

## R1 跨run顺序与分组

新dataset在每个run记录观测文件中的first_utc/last_utc及first_mono_s锚点，核对接收UTC与本机单调历时一致（1秒校验容差，只用于跨run排序，不改变源TTL、测量年龄或特征时间轴）。不同run只通过各自锚点转换支持区间，不直接比较它们的单调时钟数值。UTC跳变/时间范围交错/缺时间证据明确拒绝跨run未来留出。

freeze_split与check_split独立重建完整run顺序；不能相信传入的去重episodes_order。非连续同名A-B-C-D-E-A报出过程、run与时间范围并拒绝；相邻A-A允许同一已确认过程合组，不自动改名、删段或增加独立实验。跨分区在相邻完整run范围之间取时间边界，purge穿过边界的原始支持区间，保留单run、引用、源哈希隔离。

旧dataset不含足够UTC锚点时，不能继续当严格时间清单使用。可从原始run在新目录生成派生产物；旧split/model/test-used不覆盖，真实已使用测试不能因此恢复未使用身份。本轮所有重复重建是明示合成软件夹具。单run --exploratory仍在本机单调时间上留隔离带，即便UTC跳变也能做“同一热过程时间外推”，不能冒充跨过程泛化。

## R2 三层公平评估

固定基线层B0/B1、M0层B0/B1/M0、M1层B0/B1/M0/M1。每层的15/45/90秒集合独立冻结为同一起点、同一未来标签；记录共同数、计划覆盖率、原始引用、过程、稳定/升温/回落/重新升温与高温诊断。高温诊断与趋势阶段可能重叠，不能相加为总点数。

comparisons是JSON/Markdown/HTML与价值判断共同事实来源。主表三个时距全保留，45秒过程/阶段在可读表中展开；15/90秒的完整分组见JSON及HTML明细。旧same_origin字段继续保留为M1层兼容视图，不再用于阻挡M0判断。M0判断只用M0层内部对照，M1增量只用M1层内部对照，禁止跨层MAE比较。缺项/fallback及每方法全量覆盖继续保留。

模拟、部署未确认、少于两个有效独立测试过程、困难阶段未覆盖和没有稳定收益都保留真实结论。M1不足不抹去M0证据；基线-only正常出报告。训练仍按原共同可训练起点、训练侧字段/缩放及验证45秒小网格合同执行；没有新插补、温度真值修改或超参扩张。

## R3 实际旁路报告

三类report_type：collect采集质量、holdout_evaluation离线分层留出、shadow已发生的旁路运行。新run manifest保存类型和当时模型SHA；新评分保存模型SHA，与预测身份/horizon/method一起关联。旧记录缺模型SHA时，可由唯一预测身份取得当时预测的模型SHA；不能加载当前模型回算。

report/summarize读取本run已保存predictions.jsonl、scores.jsonl，实际已发/评分计数、MAE/RMSE/绝对误差P95/偏差/欠过预测、计划覆盖、实际方法、降级、缺项/跨段/未评分、原始与日志行引用均保留。日志缺失时未知数量是null及明确“缺日志”，不填0；存在但空评分日志表示已发预测尚未评分。日志身份冲突明示，不硬拼。

collect质量可继续辅助诊断；它的回放基线不能冒充历史模型预测。旧run无类型时，可由实际预测中的模型身份识别shadow；日志移走则提示缺证据。新模型文件改变/移开不影响已有统计，report不回写原日志。

旁路表现只描述该次在线观察，不是新的独立留出，不证明降低PWM。模拟标记始终保留；下一步随缺数据、缺日志、无模型、已评分状态变化。CLI只显示重点与报告路径，完整历史原始引用在自包含report.json/HTML中，不建设常驻页面。

## 重跑

安装0.1.1非editable wheel及原依赖锁后：

```sh
python scripts/reproduce_offline.py --output /tmp/tto-repair-check-NEW
```

入口包含完整原覆盖和新增回归、离线doctor、模拟采集—切分—训练—评估、真实loopback协议/自有进程信号、模拟Engine/Journal落盘—正式shadow报告及R1-R4原反例适配核对。模型价值仅在决策函数的明示测试副本设置非模拟分支；保存的评估及报告仍标模拟。
