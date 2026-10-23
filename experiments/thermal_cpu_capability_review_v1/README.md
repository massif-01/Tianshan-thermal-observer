# 首次cpu.2真实能力记录：模型线有限离线判读

本目录只消费测试对话已取得的本次资料，不采集或连接设备。run为`80938521-b659-4160-a7b2-5fdfb6ebc197`，command为`cpu2-capability-20261020-1ca3a249-8ea9-4608-aa05-105f9aff5614`。原始记录字节不改；本地副本、原路径及SHA见`input-freeze.json`，随后收到的测试侧资源审计另存`resource-addendum-freeze.json`。

实际流程只有：唯一旧`bridge.py`→来源标签报告器1.0.1→原Activity/evaluate_stream→本目录有限审计。活动阈值、热θ、观察器spec、既有分数和cpu.2 wheel均未改。`audit.py`复用唯一bridge的`cpu_window`，不另写字段映射或温度预测。

完整独立离线复跑：

```sh
python /Users/massif/Tianshan-thermal-observer/experiments/thermal_cpu_capability_review_v1/replay.py \
  --output /private/tmp/tto-cpu2-new27-review-NEW
```

目录必须尚不存在。使用已有Python与NumPy/SciPy/pytest环境（作者验证Python3.12.14、NumPy2.2.6、SciPy1.16.3、pytest8.3.5）；不安装新依赖。独立解包后把上面的脚本路径改成解包目录中的`thermal_cpu_capability_review_v1/replay.py`。

`dependencies/`保留原R1包与新报告器补充包，严格核SHA后只向新输出目录解包运行。原R1依赖包中的150包仅供报告器元数据测试使用；本次适配与数学评价明确只读取新27包，并断言本次run身份。不会运行依赖包里的设备入口、安装器或源采样脚本。

复跑检查5份适配产物严格同字节，10份数学输出和2份本次审计结果按原结构、引用、状态严格一致及派生浮点1e-8容差比较。重定位会改变来源JSON中的路径，所以这些路径清单不做字节等同要求。原始资料与程序/模型身份仍按SHA严格核对。

`results/adapted`保留全部FRAME、60个原TJ起点和撤销记录；`results/joint`保留原数学的逐点15/45/90秒结果、各分支覆盖和两个到达节奏；`results/audit`保存26个完整累计计数窗及资源/失效核对。没有补造高频TJ、未知时间映射、缺少的45/90答案或CPU停止后的状态。

能力未通过、背景ACTIVE及高估都是结果，不能为了“通过”修改本目录的依赖、参数或输入。`replay-spec.json`列出分析规则和冻结身份；本目录不授予12请求或任何设备执行许可。
