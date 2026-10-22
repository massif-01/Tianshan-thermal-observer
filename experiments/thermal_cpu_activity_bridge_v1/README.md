# CPU旁录适配与失效撤销：模型线有限收尾

执行TTO-CPU-PREP-CLOSE-v1.0的R1。只新增本研究目录；不做测试线SSH/运行候选修复，不重训、不扩活动搜索。原`thermal_cpu_increment_v1`、活动参数、G2/spec和旧成绩保持原样。`frozen/`是调用所需旧代码/参数的逐字节副本。

唯一实际旁录转换入口：

```sh
python bridge.py --run-dir inputs/joint-complete/run --source-config inputs/joint-complete/source-config.json --output /private/tmp/tto-cpu-adapt-NEW
python joint_check.py --adapted /private/tmp/tto-cpu-adapt-NEW --run-dir inputs/joint-complete/run --output /private/tmp/tto-cpu-joint-NEW
```

用已有NumPy/SciPy/pytest环境；本机验证Python3.12.14、NumPy2.2.6、SciPy1.16.3、pytest8.3.5。目录必须不存在。首条读取实际旁录信封/native/state/source config，交`frames.jsonl`、`thermal-origins.jsonl`、`registration.json`、撤销/诊断/来源清单。第二条逐行核实真实wire与接收source一致，再运行原Activity、原evaluate_stream；不创建网络客户端。

独立完整复跑：`python replay.py --output /private/tmp/tto-cpu-bridge-replay-NEW`。原件、代码、模型、参数用严格SHA；派生浮点用1e-8绝对容差，结构/引用/状态/计数严格相同，避免把跨数值库舍入差当成新的科研失败。

本包输入确由测试线`cpu_source.stream/read_cpu/utilization → Sidecar.receive`产生，原样保留wire/base64、150份arrival、native/state、配置、回执与源码SHA。CPU/proc及原生服务是**合成自建服务**，不是Thor/N305实测。正常、计数回退、离线/恢复及原生断连来自同一真实收发过程；额外负向回归从这些信封做明确变异，不使用手写模型FRAME替代联调。

详细时间、资格与撤销合同见[接口说明](接口说明.md)，新冻结身份见`interface-freeze.json`。原一秒adapter和旧评分未改。`results/final-v2`与`results/joint-final-v2`是本轮权威结果；先前目录仅为实现阶段保留，不是多次选参。

模型线交回本目录与最小证据后，由“实际安装与测试”汇总cpu.2候选、适配身份、操作卡。这里没有安装器/旁录源/现场runner或新的风扇算法。当前不访问设备、不部署、不发12请求、不提交GitHub；一次60秒真实能力检查也仍需用户当次批准。
