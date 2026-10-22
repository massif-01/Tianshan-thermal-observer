# TTO 冻结成果与CPU先导补测｜独立复审交付

先读独立复审报告，再读下一步Codex指令。现有真实实验/主要数值接受，stale解释需局部更正；补测值得做，但先准备、后由用户决定真机。这里没有部署、运行新实验或重训。

- 两份主Markdown：独立结论/证据与可转交的分工指令。
- pilot-plan.json：未来12请求补测模板，当前无现场授权。
- results/：独立数字与原始ref；logs/：本次实际执行结果。
- scripts/：独立raw审计、解析传播/计分和案例抽取代码。
- source_readings/：原上传包的原样报告、01—03、四张当前图；不是新编辑图或新测量。
- SHA256.json：本交付的全成员清单；input-identity.json：原上传包与关键源身份。

本小包不重复嵌套原37.8MB交付及数百MB原始日志。独立重跑需要用户本次原ZIP：将其安全解压到一个新工作目录的 original/；把本包scripts/复制为同目录scripts/，创建results/，使用Python+NumPy执行audit_field.py、audit_numeric.py、audit_examples.py。三个脚本不访问设备、不导入作者评价器、不拟合；输入路径都相对该工作目录。compare_replay.py还需要原rerun输出放frozen-rerun和补充输出放supplement-rerun，说明见原README。独立环境版本在结果文件。

建议将本包同时交给原“灰箱辨识与对照实验”和“实际安装与测试”，只执行各自章节；“模型推理监控”当前暂停负载。原研究/原始数据继续复用，不重新建项目。负责人决定转交后才构成新任务指令。
