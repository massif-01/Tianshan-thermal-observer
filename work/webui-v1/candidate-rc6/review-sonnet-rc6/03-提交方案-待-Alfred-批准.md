# rc6 提交方案（给 Alfred 审批，尚未执行）

建议将独立 Web 应用作为 `webui/` 首次入库；不把整个 `work/` 目录放进仓库。
当前 `work/webui-v1` 是未跟踪的开发/交付工作目录，包含历次候选、虚拟环境、依赖缓存、浏览器证据和包；整目录提交会混入大量历史与生成物。
这是目录与提交范围提案，需 Alfred 明确同意后才执行。此轮没有创建分支、fetch、commit、push、PR 或发布。

## 当前事实（2026-10-22，只读核对）

- 本地分支 main：`97546ba3b403c02d1b9f81aa9fa50276355a4fd3`。
- 本地缓存 origin/main：`5feb66ff521551dad9dd0bd8e30e8c3c3d636eec`；相对它是落后 2 个提交（`0 2`）。
- `git ls-remote origin refs/heads/main` 读到远端：`b85ccae98257c21b220d988c1afcfeae9f27c656`。它已不同于本地缓存；没有 fetch，所以不把“2 个”声称为相对最新远端的差距。
- 根工作区有原 TTO 的 README、安装器、pyproject、src/tto 等无关未提交改动与大量未跟踪实验/交付物；`git ls-files work/webui-v1` 为空。
- rc6 工作完成后，本轮开始时根仓库全部受跟踪文件的内容哈希仍一致。Sonnet 的 8 个前端源/配置文件哈希一致。

## 拟议分支和文件

批准后先更新远端只读引用，再从当时最新的 origin/main 建立独立干净 checkout，拟新分支名 `feat/webui-v1-rc6`。名字目前没有创建；如届时已存在则先核实归属，不覆盖。
采用新的独立 checkout，保留当前 main 和脏工作区原状，不 stash、不 reset、不 clean、不在当前目录切分支。

本次是应用首次入库，不能只提交 rc5→rc6 的差异，否则没有完整可构建源码。
精确文件白名单见 `Git-拟提交文件白名单.json`，每个文件包含候选来源、拟入库路径与 SHA256；全部落在 `webui/`：

- src/tto_web：完整后端、合同/schema/三个示例、封存静态资产与身份清单。
- vendor：候选中既有的冻结观察器/已接受组件与 provenance；不拿根目录的脏 src/tto 替换它。
- config、tests（含 rc5 schema 反例基准）、requirements 与锁文件。
- pyproject、baseline-identities、批准实施方案，以及两个 rc6 接入/安装操作卡。
- 现有 12 个构建、安装、回读与本地验证工具；rc6 的两个工具仅改了版本字符串。

不提交 wheel、ZIP、wheelhouse、candidate-*、.venv*、node_modules、build、dist、运行日志、临时 prefix、原始实验资料或整个 work/；交付包与原始证据单独封存。
Sonnet 未合入的 frontend 源文件保留在现目录，前端应由 Sonnet 在自己的变更中交付，不借此后端首次入库覆盖或隐含接纳。

## 批准后的隔离与核验步骤（本轮未执行）

1. 记录本轮封存候选身份、根工作区状态与各文件哈希；fetch 后记录最新 main 提交。
2. 在独立干净 checkout 建上述分支；只从 rc6 白名单拷贝文件到 webui/，逐一核对哈希，禁止复制根仓库未提交改动或整个 work/。
3. 通过显式白名单逐文件暂存，检查 `git diff --cached --name-status` 每个路径都属于 webui/，核对源码与候选逐字节一致，无密钥/本地配置/设备地址。
4. 在干净 checkout 复核构建和 wheel 身份。现有构建器的 rc3 对照 wheel、离线 wheelhouse 和输出目录是外部构建输入，来自封存包、先验哈希校验，不进 Git；按工具约定预先准备输入及 evidence/self-review-rc6 输出目录。路径迁移后重新核对 tools 的 ROOT 解析。若需要更改构建流程，另列具体差异给 Alfred，不悄悄扩大本轮范围。
5. 只有明确批准的范围才可 commit；提交前提供暂存差异和验证结果。push / PR / 发布仍须 Alfred 分别明确授权，提交批准不自动包含它们。
6. 对原工作区再次核对状态和哈希，证明无关本地改动完整保留。

## 本次建议的审批范围

请 Alfred 审批：是否采用 webui/ 正式目录、`feat/webui-v1-rc6` 分支名及附带精确白名单。尚未获得该同意，本轮止于交付方案与本地候选。
