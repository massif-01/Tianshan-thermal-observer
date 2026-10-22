# 首轮灰箱研究索引

接受的是首轮实际离线研究交付，模型仍 `deployable=false`；本轮不训练、不选参、不改变初值或未来输入情景。

- 研究代码和原冻结spec：`../../../experiments/thermal_identification_v1/`。
- 六个G1/G2参数的逐字副本：`models/`；模型身份和全部旧拟合/评价SHA：`evidence-index.json`。
- 原证据ZIP SHA：`d2039aafbc778a35ad223a7f6f9cac378e570a1ed67f8e9cf4962da8385ef546`。本地仍位于准备目录的 `handoff/references/greybox-v1-evidence.zip`，其解出内容在同层 `frozen-greybox/`；旧原工作树证据、数据、split与test-used均原位保留。
- L/S分享归档及此前探索输入身份见索引；私有原件SHA与分享SHA分别保存，尤其S的manifest不相同，不能替换身份。
- 旧报告、成功/失败成绩、36个主尝试及其他原诊断均按原SHA引用，未覆盖。新A/B覆盖见 `../../../experiments/thermal_identification_prep_v2/` 和本次证据包 `results/availability-v2/`。

L→S是开发期跨任务检查，S→L是反向工况压力检查，合并资料是表达能力与残差研究；它们均不是新未来留出验证，也没有控制收益结论。两轮只有两个热过程，不把18个请求当18个独立episode。
