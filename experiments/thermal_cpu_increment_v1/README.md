# TTO CPU增量活动信息：模型线离线准备

按TTO-CPU-ACTIVITY-PREP-v1.0实现A1—A3。权威数值目录为`runs/final-v2`，参数只有一次冻结，`deployable=false`。原始fixed-anchors是一个已分析的开发过程；field/modeling不是两次实验。软件只接收本地已有数据，未实现设备观测、现场调度或风扇算法。

先读`TTO-CPU增量活动信息-离线分析与冻结方案.md`。`A1-原结果补充说明.md`单独修正stale解释，不替换旧报告。`analysis-spec.json`与`candidate.json`由`freeze.json`绑定；`interface-contract.json`及fixture说明输入时间和数据角色。

## 独立重跑

用已有Python3.12环境及requirements.txt列出的依赖，在解包目录执行：

```sh
python rerun.py --output /private/tmp/tto-cpu-increment-independent-NEW
```

输出目录必须不存在。该入口跑17项研究测试（只用自建loopback服务）、重新计算本轮旧数据增量对照、核对8118个旧标签判定及B0/B1/HOLD、检查合成高频流，并与权威结果做SHA比较。**不会重跑原观察器、I02、42次拟合或任何现场入口。** 图可单独用`python plots.py --result runs/final-v2 --output NEW-FIGURES`生成；macOS使用系统中文字体，其他环境需要已有中文字体。

`prepare.py`只用于在本机从原交付构造不可变子集与一次校准，当前已完成；独立复跑无需、也不应再次执行它来改候选。

## 可运行消费者

```sh
python consume.py replay --input fixtures-v2/synthetic-stream-200ms.jsonl --output /private/tmp/tto-cpu-consumer-NEW.jsonl
python consume.py serve --allow-loopback-service --port 0 --duration-s 60
```

第一条是文件回放。第二条显式启用本机loopback入口，打印真实监听端口，接收`POST /observe`；不加许可标志即拒绝绑定。它是真实可执行入口，没有永久raise占位；不发出任何设备或推理请求。默认不自动启动服务。接收时实际打点；只有同主机/同boot单调钟声明和已有有效期的帧可形成到达侧结果，时钟不明保持UNKNOWN。

未来测试线可以在另行授权的只读诊断路径调用`activity.Processor`，供应接口规定的帧；本轮没有安装或接入生产链。

## 新记录的离线分析入口

```sh
python evaluate_stream.py --frames FRAMES.jsonl --origins ORIGINAL_1S_ORIGINS.jsonl --actual-events ACTUAL_CLIENT_EVENTS.jsonl --registration DATA_ROLE.json --output NEW-RESULTS
```

`--actual-events`可省略；提供时仅作事后活动参照。DATA_ROLE须绑定candidate和analysis spec的SHA，说明新材料是否被用于开发；看新数据选过阈值就强制标开发探索。接口样例使用`fixtures-v2`，其中所有200ms数据都明确是**合成数据**。

入口分别运行实际到达序列、同序列的因果1秒抽样，三种特征版本共用时序/规则/热初态/转换，输出各自覆盖及跨速率共同起点表。温度起点仍来自原约1秒序列，15/45/90秒分别找原有效答案；没有90秒标签不删45秒。高频旁录事后拷回且没有真实接收时间，只可称源侧潜力，不能按零延迟评分。

## 证据目录

- `inputs/`：15份原样来源文件，含8677个原事件、2706个因果状态、旧逐点评价、真实请求/协议和冻结模型/spec；没有另写原件。
- `handoff/`：独立复审包原样展开，32项被SHA索引的原成员及原SHA文件。
- `runs/final-v2/`：本轮特征/状态/预测逐点值、共同评分、覆盖、全部179条请求参照、背景区间、stale敏感性。
- `verification/`：首次失败与修正、最终17项测试、自建服务/合成流、来源与保护核对、独立复跑回执；中间运行以SHA清单保留，原工作目录未删。
- `figures-v2/`：新增三图PNG/SVG。独立复审包原四图在`handoff/source_readings/figures`保持原样。
- `research.patch`：仅新增研究源码/规格/文档与合成fixture；真实数据和派生大表随证据文件提供，不夹带生产修改。
- `SHA256.json`：本证据包每个成员的字节数与SHA。ZIP自身SHA另列在外部交付回执。

只有本地离线、有限测试和自建loopback获本轮授权。真机能力核对和12请求补测都仍未获当次授权，本软件不会自动申请、转入或重跑现场工作。
