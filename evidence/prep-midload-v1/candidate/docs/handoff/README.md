# TTO v1 实施交接包

## 交给谁、在哪里做

交给Codex，在用户新建的独立 `tianshan-thermal-observer` 仓库工作，不是原WS或天山OS仓库。

## 阅读顺序

1. `TTO-v1-Codex完整实施交接.md`：唯一生效的TTO任务主文件，TTO-PLAN-v1.0。
2. `TTO-v1-发给Codex的启动指令.txt`：复制到执行对话即可。
3. `TTO-v1-用户操作卡.md`：用户看这一页，细节查主文件。
4. `config/tto.example.json`、`templates/deployment-record.example.json`：需要实现/填写的配置与部署记录模板，端点和身份有意为空，不是已经接通的配置。
5. `reference/`：仅在需要时溯源数据合同与前一修复要求。

本包是实施方案，不含TTO产品代码、训练好的模型或可安装程序；没有执行真实设备操作。所有示例命令是需Codex实现的CLI合同。

WS最后两项收尾由用户报告完成，用户将手动部署；编写方没有收到最后新版证据，未作新候选复审背书。这不阻止TTO离线实现，真实数据准入另核对。

包内 `checksums.sha256` 校验所有其余文件，清单本身不列入自身校验；ZIP的SHA另见同名外部文件。
