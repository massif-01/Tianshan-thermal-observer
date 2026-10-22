# CPU联合回执来源标签：报告器1.0.1

本目录只修独立复审03要求的来源声明。原`thermal_cpu_activity_bridge_v1`整目录、唯一`bridge.py`、活动阈值、热模型、旧回执和旧成绩均保留。新报告器版本为`cpu-joint-reporter-1.0.1`，代码与依赖身份见`reporter-manifest.json`。它不是新的运行wheel，也不改变cpu.2候选。

将本目录放在原R1目录的同级，名称分别为`thermal_cpu_activity_reporter_v1`与`thermal_cpu_activity_bridge_v1`。若独立解包，先将原R1证据ZIP的根目录解压为后者，再解压本补充包。原R1证据ZIP SHA为`5500ad25357c86bdb53dca7d3d6067d5d397e875e8d85a278f113ae2f6eeabff`。

仍只通过原bridge适配新资料，再使用本报告器：

```sh
python /Users/massif/Tianshan-thermal-observer/experiments/thermal_cpu_activity_bridge_v1/bridge.py \
  --run-dir "$CPU_RUN_DIR" --source-config "$CPU_SOURCE_CONFIG" --output "$CPU_ADAPTED_DIR"
python /Users/massif/Tianshan-thermal-observer/experiments/thermal_cpu_activity_reporter_v1/joint_check.py \
  --adapted "$CPU_ADAPTED_DIR" --run-dir "$CPU_RUN_DIR" --output "$CPU_REPORT_DIR"
```

这些变量由测试总控绑定本次同run/command的实际本地资料；两个输出目录都必须尚不存在。命令仅离线读文件，不调用采集器或设备。离线复跑所需Python/NumPy/SciPy沿用原R1环境；不新增依赖。

来源判断同时读取实际launch、native-binding所指manifest、适配registration与sources。run/command/config必须相符，七个必要原文件的SHA必须与适配来源清单相符，绝对路径可按清单中的run根目录重定位。来源清单未覆盖或变更的文件不被静默接受。来源判断不通过时只写`unresolved_source_association`回执，不调用原分析器。

|来源值|含义|synthetic_only|
|---|---|---|
|synthetic|关联资料明确声明合成|true|
|declared_field_unverified|关联资料明确声明现场研究，实际硬件与时间证据仍待另核|false|
|unknown|缺少声明、声明冲突或资料无法关联|null|

manifest通用`simulated=false`或缺少synthetic键，均不独自证明Thor/N305实测。现场类必须同时有原registration的`targeted_recorded_arrival_research`、launch明确非合成及manifest非模拟声明。保留声明原值和文件SHA；不通过command名称、IP地址、温度波形猜实际来源。

来源、可用性、算法收益分别保存。数据有关联但来源未明时可保留冻结数学输出，来源仍为unknown；有关联但某分支全UNKNOWN时保留结果及`unresolved_variant_availability`，不强制改成有效。`analysis_complete`只表示离线程序完成，不能证明现场身份、物理领先、预测收益或控制收益。本报告器不授予这些结论，相关验证/收益标志保持false。

有限测试：

```sh
python -m pytest -c /Users/massif/Tianshan-thermal-observer/experiments/thermal_cpu_activity_reporter_v1/pytest.ini \
  /Users/massif/Tianshan-thermal-observer/experiments/thermal_cpu_activity_reporter_v1/tests -q -p no:cacheprovider
```

三类元数据测试使用旧合成收发样例作底稿；现场声明的变异只测试标签，不是现场证据。`results/historical-synthetic`是同一旧150包的新报告回执，不能充当新60秒能力资料。`verification/unassociated-receipt.json`是明确变异的反例。

新60秒资料尚未由本目录分析。收到后仅调用同一bridge和冻结分析器，检查真实计数窗/身份/接收顺序/撤销/原GPU与rail年龄/开销及逐时距覆盖，再给测试总控是否支持原12请求的建议；不自动开展设备访问或实验。
