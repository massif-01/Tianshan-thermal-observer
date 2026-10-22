# 2026-10-22 仓库成果同步说明

Alfred 明确授权：先同步三个已暂停会话的代码修改、全部实验数据和产物，再同步 Web UI，最终合并 main 并同步本地仓库。

## 收录范围

- 三个会话：TTO灰箱辨识与对照实验、模型推理监控、TTO 实机安装与测试。
- 原路径收录 experiments、evidence、investigations、deliverables、wheels、相关源码、合同和报告；包含失败实验、重复副本和历史版本。
- Web UI 在独立提交中收录 work/webui-v1 全部项目源码、前端源文件、候选与证据；仅排除运行环境、node_modules、解释器/构建缓存。
- 安装环境排除清单和原始文件身份见 evidence/repository-sync-20261022/scope.json 及两个 original-files.jsonl；原始目录链接另有清单。没有把“原始实验数据”作为缓存排除。
- 嵌套参考仓库按普通文件快照收录，Git 元数据留在本机，不上传成缺失内容的子模块；没有修改这些参考仓库的源文件。

## 原件保护

同步前记录了 30,704 个普通文件的 SHA256/Git blob 身份及 153 个原始目录符号链接。元数据例外仅 README.md、PROGRESS.md、.gitignore：README 保留远端最新版再添加索引；PROGRESS 使用已有远端版本；忽略规则只补环境路径。旧版可从归档提交 cde09e8 或其父提交恢复；本地旧 README 还额外单独保存。
其余原始代码、数据、模型、报告、ZIP、wheel 不改写。各实验的成功/失败、来源资格、模型/spec 身份和历史结论保持原样；归档不构成新的实验验收或默认后端升级。

## 核验边界

逐文件核对本地原件、Git 提交对象与远端树身份；最终主线同步另做 Git HEAD/远端引用/工作区检查。GitHub 主线的已有 src/tto、scripts、config、pyproject 保持原实现，未通过归档偷偷升级运行后端。
rc6 的 wheel、ZIP、67 项运行源码清单与已有 75 项测试日志身份保持一致；没有重新构建、伪造测试或为上传修改既有证据。
不连接设备、不部署、不重训、不重新执行实验、不启动真实负载；不删除现有成果，不使用 reset --hard 或 git clean。

完整原件 SHA256 复核和 GitHub 主线最终提交信息在本次同步 PR 的最终回执及本地 output/repository-sync-20261022/final-sync-receipt.json 中登记；这些在合并后生成，不在本文件嵌入自身提交哈希。
