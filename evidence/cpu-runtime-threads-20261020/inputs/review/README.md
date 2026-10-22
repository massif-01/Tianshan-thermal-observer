# TTO cpu.2 首次能力记录：独立复审与有限软件收尾

**2026-10-20｜TTO-CPU2-CAPABILITY-REVIEW-v1.0**

## 一句话结论

真实60秒记录及失败结论成立；不进入12请求。已经找到可以先处理的明确启动合同缺口，并本地复现数值库线程对CPU开销的巨大影响；先做进程内单线程策略落实和同进程核验，不重训、不大范围排查、不立即重测。

## 发给谁

- 原“实际安装与测试”对话：完整读01报告，执行02指令，参考04来源与scripts/results；只做本地候选，现场另批。
- 原“灰箱辨识与对照实验”对话：03是接受结果和职责说明，本轮无需新实现，按需做数学等价核验。
- 推理监控：本轮不发请求。Web UI：独立旁路，不加入当前运行候选。

## 包内内容

01 独立复审；02 实際软件收尾指令；03 模型线说明；04 来源/哈希；evidence为必要源码原字节和启动差异说明；scripts为主审纯离线验证；results为新独立结果。没有复制私有认证或大型历史归档，旧现场授权不因打包重新生效。

## 离线脚本如何复现

脚本不连接设备。`04-来源与身份.json`列出原档案的名字与哈希。建立独立工作目录ROOT：

1. 现场能力ZIP解到`ROOT/field_original/`；模型ZIP解到`ROOT/model_original/`（含thermal_cpu_capability_review_v1目录）。
2. 旧cpu.2源码参考ZIP解到`ROOT/cpu2_source_reference/`；旧300秒诊断ZIP解到`ROOT/previous_diagnostic/`。
3. 将当前现场ZIP的candidate/cpu.2 wheel解到`ROOT/delivered_runtime/`；本复审包内容放`ROOT/deliverable/`。
4. 本机安装库只用于复验。完整模型replay用其自己的README；新输出目录不得存在，不能覆盖原results。

```sh
python ROOT/deliverable/scripts/verify_and_audit.py --root ROOT
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ROOT/model_original/thermal_cpu_capability_review_v1/replay.py --output ROOT/model_replay
python ROOT/deliverable/scripts/audit_windows_scores.py --root ROOT
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python ROOT/deliverable/scripts/paced_pipeline_probe.py --root ROOT --output ROOT/probe_single --paced --seconds 12
env -u OPENBLAS_NUM_THREADS -u OMP_NUM_THREADS -u MKL_NUM_THREADS -u OPENBLAS_DEFAULT_NUM_THREADS python ROOT/deliverable/scripts/paced_pipeline_probe.py --root ROOT --output ROOT/probe_default --paced --seconds 12
```

CPU对照必须在独立子进程中于数值库导入前选环境。结果只解释当前复验机，不能声称是N305测量。紧循环重放用于数值等价，不用其CPU占用与有等待的实时流程比较。

原件/代码继续严格SHA；数值结果按合同容差。`SHA256.json`只覆盖本复审包内文件（自身除外）。
