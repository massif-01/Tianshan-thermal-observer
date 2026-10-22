# TTO-Projects-R2-实施回执

2026-10-18（北京时间）。专项 **TTO-PROJECTS-R2** 已完成，未完成项：**无**。

## 结果与入口

项目：[TTO · Product Roadmap](https://github.com/users/massif-01/projects/3)，编号 **3**，owner **massif-01（用户）**，可见性 **Private**，保持开放，已关联 `massif-01/Tianshan-thermal-observer`。

管理回执：[https://github.com/massif-01/Tianshan-thermal-observer/issues/1#issuecomment-6245021432](https://github.com/massif-01/Tianshan-thermal-observer/issues/1#issuecomment-6245021432)。只发布一条带 `TTO-PROJECTS-R2-management-receipt` 标记的管理评论，发布后正文逐字回读一致。

本轮按完整 R2 专项执行，并非只补修订差异。已有项目研究、模型、实验记录、源码、Issue 和 Roadmap 均复用。本轮没有工程实施、设备连接、部署、负载或模型重训。

## Before → After

| 对象 | 执行前 | 执行后 |
|---|---|---|
| 用户 Projects 查重 | 已登录 Safari 完整核对开放与关闭列表：DFA #2、空的旧关闭 #1；仓库 Projects 开放/关闭均 0，无 TTO 匹配 | 新建 TTO #3，Private；原两项目保留。授权后 GraphQL 完整分页回读 3 项，hasNextPage=false，并核对仓库关联 |
| #1 原生子项 | GET 列表为空；#8/#9/#10 parent 均返回 No parent issue found / 404 | #1 子列表 [8,9,10]；每个子 parent 均为 #1，双向确认 |
| 项目字段/卡片 | 新项目默认字段与空项目，UI 先建立 Phase；首次 API 快照 14 字段、0 items | 7 个要求的自定义字段和唯一原生 Status 均存在，19 个唯一节点 |
| 视图 | 初始 View 1 为 Table | 原位复用为产品路线，补 Board / 真正 Roadmap / 未排期 Table，均已保存 |
| Done 自动关 Issue | 新项目默认 Auto-close issue 开启 | 添加条目前关闭；API 与 UI 均回读 false。Auto-archive 保持关闭，历史 Done 未归档 |
| 研发 Issue | #1/#8/#9/#10 全部 open | 标题、正文、状态、标签、Assignees、关闭字段和原评论均保持；只增加原生关系及一条管理回执 |

最初 CLI 仓库调用正常，但 Projects 实际查询返回 INSUFFICIENT_SCOPES；未将其误判为 token 失效。按 R2 说明授权步骤，由用户完成 `gh auth refresh -h github.com -s project`；随后实际项目查询及写入成功。未输出或交付 token，未自行修改全局权限绕过边界。创建项后曾遇到短暂读延迟，先回读再继续，没有盲重试创建。

## 已保存视图

| 视图 | 真实 URL | Layout | 筛选与组织 |
|---|---|---|---|
| 产品路线 | [views/1](https://github.com/users/massif-01/projects/3/views/1) | TABLE_LAYOUT | 无筛选；Phase 分组；Horizon ASC → Priority ASC；关闭层级折叠以显示全部条目；Kind 可见 |
| 执行状态 | [views/2](https://github.com/users/massif-01/projects/3/views/2) | BOARD_LAYOUT | `-kind:Overview`；Status 分栏，18 项；Todo / In Progress / Done / Blocked 四列 |
| 已排期时间轴 | [views/3](https://github.com/users/massif-01/projects/3/views/3) | ROADMAP_LAYOUT | `has:start-date has:target-date`；绑定 **Start date → Target date**，Month；当前 0 项 |
| 未排期 | [views/4](https://github.com/users/massif-01/projects/3/views/4) | TABLE_LAYOUT | `no:start-date no:target-date`；Phase 分组，Horizon / Priority 排序，平铺显示；实际匹配 19 项 |

视图布局、筛选、分组和排序已由官方 API 回读；Roadmap 日期绑定经 UI 保存、重新打开不带查询参数的 URL，再从 View 菜单确认 `Dates: Start date and Target date`。筛选经 UI 验证无错误；多词日期字段使用 UI 自动补全产生的 `start-date` / `target-date`。这不是只创建了 API items 而遗漏保存视图的结果。

没有获批日期，19 项 Start / Target 全空，已排期 0 项；不填历史报告日期、不新建 Iteration，也不承诺每阶段有时间条。项目 README 有四个视图入口、未排期说明、Issue 稳定映射与权限限制。

## 字段

保留原生 Status 的原选项 ID 和合法命名 `In Progress`，只补 Blocked；没有创建同名 Status。

| 字段 | ID | 类型 | 选项 |
|---|---|---|---|
| Status | `PVTSSF_lAHOCoNcq84BnjKJzhmHQWg` | SINGLE_SELECT | Todo / In Progress / Done / Blocked |
| Phase | `PVTSSF_lAHOCoNcq84BnjKJzhmHQoY` | SINGLE_SELECT | P0 / P1 / P2 / P3 / P4 / P5 / P6 / P7 / Control |
| Horizon | `PVTSSF_lAHOCoNcq84BnjKJzhmHQ-8` | SINGLE_SELECT | Now / Next / Later |
| Kind | `PVTSSF_lAHOCoNcq84BnjKJzhmHRAA` | SINGLE_SELECT | Overview / Delivery / Task |
| Priority | `PVTSSF_lAHOCoNcq84BnjKJzhmHRBU` | SINGLE_SELECT | High / Normal / Low |
| Responsible chat | `PVTF_lAHOCoNcq84BnjKJzhmHRCQ` | TEXT |  |
| Start date | `PVTF_lAHOCoNcq84BnjKJzhmHRCU` | DATE |  |
| Target date | `PVTF_lAHOCoNcq84BnjKJzhmHRCY` | DATE |  |

选项 ID、颜色、描述和字段 ID 完整列在证据 `after/fields-minimal.json`。Responsible chat 是文本；只有 #1 保留既有真实 Assignee massif-01，其余不把对话名当账号。Priority 的常规排序决定：当前三个 Task 为 High，历史交付及 Next 为 Normal，未来 Later 为 Low；它不改变授权。

## 条目、状态和证据

实际 **19 项 = 4 个既有 Issue + 15 个 draft**，并非强制凑 19 个新对象。Status：**Todo 14 / In Progress 1 / Done 4 / Blocked 0**；Kind：Overview 1 / Task 3 / Delivery 15。总览 #1 的持续管理状态为 In Progress，执行看板隐藏它，不计产品交付完成率。

- 四个限定 Done：P0-DATA、P1-MODELS、P2-STATES、P2-YET，均保存公开摘要/报告固定链接及局限。公开证据链接已实际回读存在。Done 不扩展为阶段全完成、Ts 物理验证、未来预测获胜、部署或控制授权。
- #8/#9/#10 最新 R2 合同仍开放、无新增执行评论；未凭 Issue 创建或本地其他研究目录推断正在实施，保持 Todo。
- P4-INPUT、P4-OBSERVE、P5-ADAPT 均存在。P6-MATERIAL / P6-DEVICE 分别依赖生成/校准流程，不互相强阻塞，也不等待完整在线学习成品。
- 原生父子仅用于既有 #1 → #8/#9/#10。#10 blocked-by 列表回读为空；未把未来 draft 转成 Issue，也未为了依赖建立额外 blocked-by。

Issue 的稳定 ID 保存在项目 README 和导出映射中，按精确 URL 复用；draft 使用独立 HTML 标记 `<!-- TTO-RM:<id> -->`。依赖正文中提及的其他节点不作为自身身份。完整 item ID → 稳定 ID → content node ID → Issue URL / draft、字段值、依赖与证据见 `after/item-stable-id-map.json`。

| 稳定 ID | item ID | 类型 / 来源 |
|---|---|---|
| TTO-RM:OVERVIEW | `PVTI_lAHOCoNcq84BnjKJzhBjbj0` | [Issue #1](https://github.com/massif-01/Tianshan-thermal-observer/issues/1) |
| TTO-RM:P0-DATA | `PVTI_lAHOCoNcq84BnjKJzhBjb2Y` | Draft |
| TTO-RM:P1-MODELS | `PVTI_lAHOCoNcq84BnjKJzhBjb70` | Draft |
| TTO-RM:P2-STATES | `PVTI_lAHOCoNcq84BnjKJzhBjcAw` | Draft |
| TTO-RM:P2-YET | `PVTI_lAHOCoNcq84BnjKJzhBjcJM` | Draft |
| TTO-RM:P3-STATE | `PVTI_lAHOCoNcq84BnjKJzhBjbks` | [Issue #8](https://github.com/massif-01/Tianshan-thermal-observer/issues/8) |
| TTO-RM:P3-IO | `PVTI_lAHOCoNcq84BnjKJzhBjbk0` | [Issue #9](https://github.com/massif-01/Tianshan-thermal-observer/issues/9) |
| TTO-RM:P4-PLAN | `PVTI_lAHOCoNcq84BnjKJzhBjbk8` | [Issue #10](https://github.com/massif-01/Tianshan-thermal-observer/issues/10) |
| TTO-RM:P3-INTEGRATE | `PVTI_lAHOCoNcq84BnjKJzhBjcV4` | Draft |
| TTO-RM:P4-MIX | `PVTI_lAHOCoNcq84BnjKJzhBjcZY` | Draft |
| TTO-RM:P4-INPUT | `PVTI_lAHOCoNcq84BnjKJzhBjces` | Draft |
| TTO-RM:P4-OBSERVE | `PVTI_lAHOCoNcq84BnjKJzhBjckU` | Draft |
| TTO-RM:P4-CONFIRM | `PVTI_lAHOCoNcq84BnjKJzhBjcp0` | Draft |
| TTO-RM:P5-GENERATE | `PVTI_lAHOCoNcq84BnjKJzhBjcus` | Draft |
| TTO-RM:P5-ADAPT | `PVTI_lAHOCoNcq84BnjKJzhBjczU` | Draft |
| TTO-RM:P6-MATERIAL | `PVTI_lAHOCoNcq84BnjKJzhBjc3s` | Draft |
| TTO-RM:P6-DEVICE | `PVTI_lAHOCoNcq84BnjKJzhBjc_I` | Draft |
| TTO-RM:P7-RELEASE | `PVTI_lAHOCoNcq84BnjKJzhBjdFU` | Draft |
| TTO-RM:CTRL-VALIDATE | `PVTI_lAHOCoNcq84BnjKJzhBjdLk` | Draft |

只读幂等复算：新增字段 0、创建 item 0、修改字段值 0、创建视图 0、补父子关系 0；19 个稳定节点和 item ID 均唯一。没有再次实际运行一遍写操作来证明幂等。

## 版本、自动化与边界

PR #7/#11/#12 已实际回读为 merged。R2 文档 [PR #13](https://github.com/massif-01/Tianshan-thermal-observer/pull/13) 本轮最终回读为 **open / merged=false**，head `6fcf46dccb99c88564d54381e7228262c54b1cad`。
当前 main 产品 Roadmap 与 R2 候选均已读取，项目采用 #1 当前 R2 合同及 PR #13 固定候选的语义，未把未合并候选冒称 main 生效。没有新文档 PR、代码提交、旧分支追加或自动合并。

自动化：保留 Auto-add sub-issues、Item added、Item closed、Pull request linked、Pull request merged 等合理默认规则；只关闭与本次明确边界冲突的 Auto-close issue。自动归档未启用。所有条目 isArchived=false，主 Issue 保持开放。

本专项没有发送工程工作、修改工程代码/源码、连接设备、刷机/安装/重启、发真实推理请求、改变 AUTO/曲线/gain/保护、上传原始实验数据或私有日志。本轮只新增本地管理报告/证据，保留已有脏工作树。

## 官方接口和核验方式

- `gh api graphql`：分页读取 user.projectsV2、仓库关联、fields / views / items / workflows，所有连接 hasNextPage=false；读取 field input schema 确认当前能力。
- `gh project field-create`、`gh project item-add`、`gh project item-create`、`gh project item-edit`、`gh project edit`：仅本项目；既有 Issue 按 URL 复用，draft 创建前去重，创建后回读。
- `POST /repos/massif-01/Tianshan-thermal-observer/issues/1/sub_issues`，JSON `sub_issue_id` 使用数据库 ID：#8=5901752774、#9=5901753220、#10=5901753657；未传 replace_parent。随后 GET 父子双向核验。
- `POST /users/massif-01/projectsV2/3/views`：创建 Board / Roadmap / 未排期，使用 REST 数值字段 ID。`updateProjectV2View` 复用初始 Table 并设置可见字段。UI 补全 Table 分组/排序与 Roadmap 日期绑定，实际保存后再 API / UI 双重回读。
- `POST /repos/massif-01/Tianshan-thermal-observer/issues/1/comments`：发一条带标记回执；重复执行应查找并仅更新本回执，不覆盖研发评论。

官方依据：[原生 sub-issues](https://docs.github.com/en/rest/issues/sub-issues)、[视图 API](https://docs.github.com/en/rest/projects/views)、[项目筛选](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/filtering-projects)、[Roadmap 布局](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-roadmap-layout)、[内置自动化](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations)、[gh 字段创建](https://cli.github.com/manual/gh_project_field-create)。这些是接口依据，完成状态以本次真实回读为准。

## 交回证据

最小证据包包含执行前结构、原 Issue/评论快照、执行后 Project/字段/视图/items、19 节点映射、原生父子双向读回、#10 依赖、PR 状态、工作流、UI 摘录、管理评论及保存/验证结果。`SHA256.json` 对包内文件校验。没有 token、原始数据、设备日志或用户现场路径。

附件自带 `verify_package.py` 已通过 17 文件完整性校验；这只是交接包完整性，不是软件/现场验证。此次验收属于 GitHub 管理落地，不改变研究或现场接受状态。
