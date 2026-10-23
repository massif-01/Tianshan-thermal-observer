# TTO-SLOWSTATE-v1.0：实际离线研究

本目录是新增的独立研究层。先读`产品决定与字段含义.md`与`slowstate-spec.json`，再读中文研究报告与`figures/中文图解.html`。所有L/S/M资料都是开发资料。模型没有控制权；本轮没有重新拟合动态参数，没有新安装候选。

## 一条入口独立重跑

保留原交接包中的两个ZIP，不解压历史脚本后执行它们：

```
python3 rerun.py --input-dir /绝对路径/原交接包/inputs
```

入口先校验固定SHA及CRC，再提取只读源副本，重建CPU传播核，导出三套冻结模型的两种状态、四分支A-roll/B-HOLD、普通需求和即时风险台账，执行有限测试，绘制四类中文图，最后独立回读。它不安装依赖、不使用网络、不执行任何设备入口、不调用历史fit/all。运行日志在`replay-logs/`。在交付目录重跑会更新本轮派生物；复审建议先复制或解压到新目录，便于与封存SHA对照。

本机入口自动使用已经存在的`.venv310`计算环境和已存在的Matplotlib绘图环境，使用者无需逐项拼装。可用`--python /path/to/python --plot-python /path/to/python`明确指定；两参数可以是同一个Python。异机可用单一Python 3.10–3.12环境，所需库只有NumPy、SciPy、pytest、Matplotlib及一个中文字体；精确已执行版本和本机入口在`results/resources.json`、`figures/plot-environment.json`与`replay-logs/receipt.json`。C编译器只编译复制的CPU二状态传播核，未使用CUDA。源码中的绘图环境切换不是生产依赖变更。

## 输入身份及重跑范围

原大ZIP按`source-inventory.json`索引引用，不递归塞入成果ZIP。`sources/`已含本轮所需的不可变已登记数据、冻结模型、原预测/校准/状态、原控制快照子集和来源索引，可用于无需原大ZIP的回读；从原件完整重建使用上面的一条入口。`sources/provenance/`保留M的24°C附注、旧私有/分享归档身份区分。24°C未填到L/S，旧E未重写。

两个必需原归档：

| 文件 | SHA256 |
|---|---|
| r2-results-original.zip | 809e90eef398daf34e9cabfd5d4427d35275fc8185541d61810f67943f35aecb |
| r2-prerequisites-original.zip | 7f52d7cfad66564ff07178bfe14a5a46da83390b0855c28f2b65cad8910c3614 |

## 文件用途

| 文件/目录 | 用途 |
|---|---|
| prepare.py、stage1-freeze.json | 来源/语义/规则在新成绩前冻结 |
| vendor/ | 从已接受R2复制的CPU传播及过去前缀状态函数；原样保留，fit函数定义不被调用 |
| core.py、run_study.py | 固定QS/LP、四分支传播、固定需求塑形、即时状态台账和诊断 |
| results/states-A-long.jsonl | 同次自由传播的Tf/Ts；不读后续TJ反馈 |
| results/states-causal60.jsonl | 原过去60秒估计；Tf观测锚定，不算预测 |
| results/four-branch-predictions.jsonl | 每个独立时距的四来源同参数、同输入情景、同温度标签；原B0/B1/Ridge/RELAX30另字段保留 |
| results/normal-demand-origins.jsonl | 原始/裁剪/塑形、参考、死区、限速、饱和，指数不是PWM |
| results/fast-status-and-demand-ledger.jsonl | 所有原到达节点及已知有效期终点；即时失效，保留真实TJ与原异常 |
| results/accepted-demand-availability.jsonl | 全6643个accepted起点的需求可用/不可用及原因 |
| results/*metrics.json、*diagnostics.json | 温度、覆盖、形态、事件、初态/滑窗/模型敏感性、组合驱动 |
| tests/、test-attempt-*.log | 仅研究层与直接复用函数检查，包含失败及修复后的日志 |
| figures/ | 四类中文PNG/SVG/三句图解及HTML入口 |
| verify_results.py、readback-checks.json | SHA、独立重算的共同集合/温度指标、因果字段与1797个原文件保护核对 |
| code.patch、SHA256.json | 只包含新增研究代码/本地文档的补丁及封存成员身份 |

初始两次计算尝试分别暴露新统计程序没有跳过无温度答案、S阶段元数据没有macro字段的兼容错误；失败日志保留。随后修正新程序的尾部时段裁切、已知资格到期仍保留快通道TJ的字段，以及补齐预定诊断。没有改变冻结的模型、规则、分支或塑形参数。所有成功/失败日志不构成新的参数搜索。

独立复审只需核对本目录。本轮停止于离线交付，不自动部署、实测或继续训练。
