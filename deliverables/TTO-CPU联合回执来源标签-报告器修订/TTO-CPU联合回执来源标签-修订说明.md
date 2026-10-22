# TTO-CPU联合回执来源标签-修订说明

已完成独立复审03要求的报告器小修。现在会区分“合成”“声明现场，证据另核”“未知”，并在原始资料无法关联时交回未决；没有重新研究活动识别或训练热模型。

新入口位于`experiments/thermal_cpu_activity_reporter_v1/joint_check.py`。唯一适配器仍为原R1的`bridge.py`，cpu.2运行wheel没有变化。原R1报告与证据包、旧150包回执保持原样。

- 三类元数据来源测试：3项通过；覆盖显式合成、现场声明与未知，以及无标志、冲突、command不符、SHA变更和缺文件。
- 同一旧150包经过新报告器，仍为合成；342个FRAME、56个原TJ起点。10份科学输出与原R1相同，最大数值差0。这里只验证报告器没有改变数学。
- 不相干command的CLI反例：输出`unresolved_source_association`，`analysis_complete=false`、`evaluate_stream_called=false`。
- 2076个受保护的原R1及Git跟踪文件核对无变化。此数量是本次有限改动的保护范围，不冒称全仓审查。

来源声明先核实际launch、native-binding/manifest和适配registration/provenance的身份及七项必要原文件SHA。没有synthetic键不等于物理真实；manifest的通用simulated=false也不是现场证明。来源声明、数学程序完成、分支可用性和收益结论分别保存。全UNKNOWN不触发“强修”数据。

本次没有新现场资料、没有新的物理领先/预测收益/控制结论。旧CORE=MEAN及CPU策略未胜HOLD的开发负结果保留；没有改参数、旧θ、模型、旧评分合同或历史成绩。

新60秒资料应由测试对话按已获得的当次授权取得，再交回同run/command的native/state/source config/arrivals/wire/events/summary。模型线届时只离线判读信息、原链干扰/开销、真实接收序列上的BASE/MEAN/CORE可比性和仍未知的源侧物理时间；旧150包不得替代它。资料未交付前，本补充包不预判能力通过，也不授权12请求。

完整命令与同级目录解包方法见本包README。补充包依赖原R1证据ZIP，SHA：`5500ad25357c86bdb53dca7d3d6067d5d397e875e8d85a278f113ae2f6eeabff`。由测试总控将新报告器身份追加至候选证据和操作卡，不替换原bridge身份。

新报告器版本：`cpu-joint-reporter-1.0.1`。
报告器代码SHA：`a391161edbe4908009053b52c41b49805008aa47aadc23e89817181a1d5e031b`。
报告器清单SHA：`80285a84bdb6fc7972413f64e2b1820d387718113345184172a2d69ead2fe8da`。
唯一bridge SHA仍为：`8d6fe5f013e67d2a26c192419b0b82f29a4c1aa794ddd598e2f6ba33a45045e3`。
