# TTO 代码、实验资料与交付索引

本次把三个已暂停会话的代码、实验数据、模型、失败记录、报告和交付物纳入同一仓库；这是成果归档，不把实验候选自动提升为默认运行后端。

| 内容 | 路径与身份 |
| --- | --- |
| 已公开的基础采集器 | src/tto；项目版本 0.2.2，与原 main 已接受实现对应 |
| 灰箱辨识、校准、冻结模型与 CPU 研究 | experiments/thermal_*、experiments/cpu_*；各自方案、数据角色、模型/spec 与结论以目录合同和交付报告为准 |
| 主线观察与推理运行候选 | experiments/mainline_*、experiments/autoworkday_*；保留各版本，不自动替换设备运行环境 |
| 原始观察、实验与验证证据 | evidence/、investigations/；保留原始数据、失败记录、重复输入副本及来源身份 |
| 安装候选、交付 ZIP 与报告 | deliverables/、wheels/；历史版本原样保留，不把所有包称为当前可用版本 |
| Web UI | 独立项目 work/webui-v1；rc6 的入口为 work/webui-v1/DELIVERY-rc6.json，Sonnet 前端源文件和历史候选一并保留 |

首轮灰箱研究曾单独推送至 research/greybox-id-v1；该分支继续保留。本次补齐本地后续成果，不改写该分支历史。
已存在的远端 main 文档/路线图保留；本地旧 README 原件保存在 evidence/repository-sync-20261022/README-before-sync.md。

## 原件保护与复核

- evidence/repository-sync-20261022/backend-original-files.jsonl 与 webui-original-files.jsonl 记录同步前每个原件的路径、字节数、SHA256 和 Git blob 身份。
- Python/Conda 的已安装测试环境、node_modules、解释器与构建缓存仍留在本机，排除路径记录于 scope.json；不把实验数据目录当作缓存排除。
- 仓库提交前后对照原件清单；允许更新的是仓库入口文档、忽略规则和这次同步说明，实验代码/数据/模型/报告/候选包不改写。
- 这次同步不连接设备、不部署、不运行真实负载、不重训模型，也不重跑实验生成新的数据。

历史报告中“待复审”“尚未提交”等文字反映封包时状态，原件保持不变；当前 Git 同步状态以本次提交历史及同步回执为准。

## 未来功率预测专项入口（2026-10-23）

[专项 Roadmap：DOC0 / WP0—WP5](roadmap/WORKLOAD-PREDICTION-ROADMAP.md) 对齐 [#17](https://github.com/massif-01/Tianshan-thermal-observer/issues/17) 和现有产品/技术路线。main 的 generate/calibrate/compare、冻结 G2、observe.2、事件与版本工具可复用；“多模型对比评估”本地 v1 已有真实比较及五包，但尚无公开提交，身份摘要、差距和保管边界见专项 §2.3。这里不为本地未提交文件创建虚假的 main 下载入口，也不把归档或同数据复现称为新盲测、目标机或控制通过。
