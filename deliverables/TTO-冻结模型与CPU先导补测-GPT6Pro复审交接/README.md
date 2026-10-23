# TTO：冻结模型成果与CPU先导补测复审

合同：**TTO-CPU-LEAD-REVIEW-v1.0**。本包用于独立复审现有成果及下一轮补测方案。现在没有新增实测、模型重训、采样修改或设备动作。

用户上传本交接ZIP，并粘贴`04-直接粘贴给GPT-6-Pro.txt`即可；`00-给GPT-6-Pro的复审指令.txt`是完整任务合同。所需当前run代码、数据、模型、逐点结果和图表已经展开在包内，不需要再补传两个原始交付ZIP。

## 阅读顺序

1. `00-给GPT-6-Pro的复审指令.txt`：本轮任务、证据要求、输出和停止边界。
2. `01-用户产品决定与待证假设.md`：区分产品目标、用户设想、已有事实和作者判断。
3. `02-逐核CPU与时间分辨率补充说明.md`：从原记录新做的只读描述；没有拟合或搜索领先时差。
4. `03-下一轮针对性补测草案-待审非执行.md`：有限补测建议，尚未批准或实施。
5. `reports/TTO-首轮fixed-anchors混合实测与YET归档报告.md`和`reports/TTO-首轮fixed-anchors冻结模型对照报告.md`：分别是现场线和模型线原报告，字节未改。
6. 查`evidence/modeling/`的spec、源码、逐点结果、验证；查`evidence/field/`的实际run、请求、安装身份、时钟及仪表原件。
7. `reports/TTO-缺测状态估计与冷启动-R2报告.md`仅提供历史M/Y背景，不是本轮新结果。

## 先避免三个身份混淆

- `evidence/field/`与`evidence/modeling/`是**同一个新run的两条工作线交付**，不是两轮独立实测。唯一run为`5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3`。
- `analysis/`是从这同一个run事后提取的逐核CPU、内存和采样年龄描述，不是新采集、CPU领先验证或新预测成绩。未来jtop录屏尚未提供。
- 现场包封存于2026-10-19 10:39 UTC，当时的“建模比较待回”是历史状态。模型线后来已完成独立重放和交付；不能据此认为本轮现场或比较尚未执行。

当前45秒共同集合：A-roll 0.334°C、B-HOLD 1.544°C、B0 2.230°C；跨阶段B-HOLD为8.871°C，最坏低估12.712°C。A-long初始化后不再吸收TJ，MAE 0.888°C。这些是待核查结果，不能直接当成复审结论。

## 包内证据

| 路径 | 用途 |
|---|---|
| `reports/`、`reports/figures/` | 现场报告、冻结比较报告、历史R2报告及全部对应中文图 |
| `evidence/modeling/` | 原模型交付ZIP逐成员展开：冻结G2/spec、现场身份源码、原始输入、23份可独立重放科学结果、测试与patch |
| `evidence/field/` | 原现场交付ZIP逐成员展开：179条请求和响应、状态/准入/资源、原生日志、YET CSV/映射、首末时钟与身份 |
| `analysis/`、`tools/recompute_supplement.py` | 2706条原引用的逐核CPU/内存CSV、描述统计和标准库重算入口 |
| `references/` | 原交付回执、历史状态接口；不要求重做历史M/Y研究 |
| `sources/` | 原交付身份/SHA、官方资料和适用限制 |
| `verification/` | 本次组包、补充统计独立重算及旧文件不变核验 |

两份当前交付展开时均先逐项核对原SHA索引，内容不改，保留各自`SHA256.json`。两包有重复成员和索引包含关系，不能把文件数或样本数相加。没有递归装入历史95MB研究ZIP或原始远端tar；其身份留在`来源`索引中。当前冻结比较的独立重跑输入已经完整包含。

## 可选离线核查

在解压根目录运行：

```sh
python3 verify_handoff.py
python3 tools/recompute_supplement.py --output /tmp/tto-cpu-supplement-new
```

输出目录必须不存在。以上只读原件，第二条只向新目录写派生描述。数值模型重放需要原`requirements.txt`所列环境：

```sh
python3 evidence/modeling/rerun.py --output /tmp/tto-frozen-review-new
```

该入口保留6项测试并在重放阶段阻止socket连接。不得执行包内历史现场启动、部署、安装或设备操作脚本。无需为了复审安装wheel、连接设备或发推理请求。

复审应分别判断：现有成果是否接受、哪些解释需修订、补测方案是否值得推进。不因新假设未验证全盘否定可复现成果，也不因重放一致认定预测或控制已成功。
