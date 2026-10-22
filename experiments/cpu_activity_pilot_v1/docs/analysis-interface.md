# 分析交接合同 v1

本候选不训练活动分类器，不更新热θ，不计算新成绩。`cpu_interface.py`仅实现截至预测起点的字段资格筛选；fixture全为模拟数据。

三个嵌套输入视图为GPU利用率+独立vdd_gpu/vdd_cpu_soc_mss；再加同窗全核均值；再加同窗每时刻最大值。不选事后最佳核、不搜索lag，不把CPU百分比再加成瓦数。NVML和rail的底层独立刷新窗口不能从调用次数或数值相同推断。

原始层 `cpu-sidecar-arrivals.jsonl` 保留Thor自己的host/boot/session/CLOCK_MONOTONIC、每字段读窗及CPU累计计数，另保留N305实际接收/生成时刻和唯一native UUID。`network_latency_s=null`；不能跨主机直接相减当网络时延。若只使用源文件，则所有结论标source_potential。

`causal_inputs`的规范化输入要求：`field,value,valid,clock_domain,observed_window_end_s,available_at_s,decision_generated_s`。同域且窗口、可用、判断、起点依序成立，并在明确新鲜度内才进入视图；未知/缺失返回null、不补零。fixture的同域坐标是人为模拟，不能用于替真实文件校时。对真实源窗口没有可靠映射时，这个严格同域入口拒绝它；模型线可以另外在N305接收顺序上评价已到达活动，但必须声明源窗口/年龄仍未知，不能虚填窗口结束=接收时刻来让此入口通过。

CPU `/proc/stat` first8累计差分：total=user+nice+system+idle+iowait+irq+softirq+steal，busy=total-idle-iowait；guest/guest_nice已包含在user/nice，不再加一次。iowait不是精确每核工作量；计数减少、重置、缺前帧、离线及零窗口记不可用。全核均值是可用且完整在线集合的无权均值；任一在线核缺窗则均值/最大值未知，原逐核值保留。SC_CLK_TCK和首末读取括号保留，200ms并非瞬时无窗值。

旧run是开发资料；新12条仍是一个热前史。模型线冻结活动规则/输入转换/spec及新数据角色以后，才可能区分开发与以后确认。计划阶段、尚未提交请求和未来温度不属于输入；实际提交/首内容/DONE仅可作独立EVENT-ASSIST参照，非GPU内核边界。仪表可选；复用Date+Time/CH1/Celsius实际1s格式，日期原样，首末独立锚点、测点说明和新run sidecar，不复用旧M24°C。

未完成事项是活动规则与未来输入转换的模型线交付、真实GPU/rail底层窗、真实安装身份和低开销资格。它们不是本候选已经证实的预测收益。
