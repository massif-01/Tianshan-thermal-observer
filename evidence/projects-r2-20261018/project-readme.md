<!-- TTO-PROJECTS-R2 -->
# TTO 产品路线与执行入口

[主 Issue #1](https://github.com/massif-01/Tianshan-thermal-observer/issues/1) 保存当前执行合同；[产品 Roadmap R2 候选](https://github.com/massif-01/Tianshan-thermal-observer/blob/6fcf46dccb99c88564d54381e7228262c54b1cad/docs/roadmap/PRODUCT-ROADMAP.md) 对应 [文档 PR #13](https://github.com/massif-01/Tianshan-thermal-observer/pull/13)，未合并状态以实时 PR 为准。PR #7/#11/#12 已合并。

- [产品路线 / Table](https://github.com/users/massif-01/projects/3/views/1)：全部节点，Phase 分组，Horizon / Priority 排序；Kind 区分总览、交付和任务。
- [执行状态 / Board](https://github.com/users/massif-01/projects/3/views/2)：Status 分栏，隐藏 Overview；保留历史 Done。
- [已排期时间轴 / Roadmap](https://github.com/users/massif-01/projects/3/views/3)：Start date → Target date，仅显示两个日期均有值的节点。
- [未排期 / Table](https://github.com/users/massif-01/projects/3/views/4)：没有 Start date / Target date 的卡片。当前没有获批日期，日期保持为空；先后由 Now / Next / Later 表达。

| 稳定节点 | 既有 Issue |
|---|---|
| TTO-RM:OVERVIEW | #1 https://github.com/massif-01/Tianshan-thermal-observer/issues/1 |
| TTO-RM:P3-STATE | #8 https://github.com/massif-01/Tianshan-thermal-observer/issues/8 |
| TTO-RM:P3-IO | #9 https://github.com/massif-01/Tianshan-thermal-observer/issues/9 |
| TTO-RM:P4-PLAN | #10 https://github.com/massif-01/Tianshan-thermal-observer/issues/10 |

其余 draft 以正文 `TTO-RM:<id>` 去重，保留交付、验收、证据、局限和 depends-on。原生 #1 → #8/#9/#10 表示拆解；不添加 #10 blocked-by #8/#9。未来 draft 不转 Issue 来凑原生关系。

Done 仅表示 P0-DATA / P1-MODELS / P2-STATES / P2-YET 四个有证据的限定历史交付，不代表阶段全完成、模型全场景有用或控制获准。#1 为持续总览，不计产品交付完成率；#8/#9/#10 没有执行提交或用户确认前保持 Todo。Blocked 仅用于真实外部阻断，Later 不是 Blocked。

Responsible chat 为职责入口文本，不是 GitHub Assignee。Priority：当前三项 Task 为 High，历史及 Next 为 Normal，未来 Later 为 Low。此排序不授权实施。

本项目 private、owner massif-01。Auto-close issue 已关闭；不自动归档历史 Done。工程、设备、部署、负载、风扇控制分别按各自授权办理，卡片或 Done 均不授予这些权限。
