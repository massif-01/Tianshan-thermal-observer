# 连续测温工具审查修正

本包修复生成报告的来源文案，并记录最小文档后续PR；不涉及真实测温或模型重训。旧交付ZIP和实施报告保留原字节。

当前修正报告为本目录《TTO-连续测温工具-审查修正报告.md》，发布状态看publication/publication-receipt.json；旧根目录实施报告是历史交付，不将它的26项测试改写为本次30项。

## 重跑

进入包内thermal_reference_v1，使用**已有pytest的Python3.10+解释器**运行，不必沿用作者私有临时路径；图形另需已有Matplotlib和中文字体：

```sh
python run_offline.py --output 一个不存在的新目录
python review_fix_v1/run_report_cases.py --output 另一个不存在的新目录
```

第一条实际完成20个CLI/检查调用，包含原26项和新增4项共30项测试；第二条单独导出四种来源的JSON/MD/HTML。没有Matplotlib时图形状态会明确不可用，不冒报已画图；核心数值与报告仍可生成。软件不联网安装依赖、不调用publication脚本或设备入口。

原受审证据ZIP SHA为f32ccb4c3a70d9005a74c66c2f0b736f5362c9e6ebe85d64f9e912feaef48b1c。software-fix.patch只改三条研究路径；baseline/保留原文，patch-application-receipt.json证明在旧包副本check/apply并逐字节比较成功。make_software_patch.py是作者有旧包时的应用核对，不是通用重跑前置。

## 证据位置

- results/full-flow：新完整入口日志、30项测试、三类旧演示再生成报告、资源/来源读回。
- results/source-cases：零读数、全合成、声明外部、混合来源四组构造输入与实际报告。所有值都是测试构造；false标记仅测试输入类别，文件和备注含TEST-ONLY-NOT-A-REAL-MEASUREMENT，不是假称真实新测温。
- unchanged-results-receipt.json：数值、时间、完整模型范围、参考增量与资格逐点一致；运行特有的UUID/写入时刻另分，探头事件语义也独立比较。
- publication：当前main基底、四文件门禁、仅文档patch、真实PR7/Issue/原唯一进度评论和文档逐字节回读。待审不等于进main，不自动合并。
- inputs：用户交回的独立审查原文及SHA。repair-spec.json登记范围和旧证据身份。
- 旧results/release-check中随包保留的comparison/paired-points是语义比较基线；旧独立审查计数没有冒充为作者这次执行量。

原临时Python3.10在最后补验启动时缺标准库，失败日志保留但未计通过；之后用已有本地Python3.12和已有pytest完成patch副本30项及四来源CLI入口验证。没有修改共享环境或生产依赖。真实YET CSV映射、探头安装/响应、表面与Ts物理对应仍未验证。
