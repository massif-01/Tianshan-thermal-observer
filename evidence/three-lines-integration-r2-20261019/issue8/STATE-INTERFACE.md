# 给#9/#10的只读状态接口

本线只输出模型证据；不修通讯、不写采集器、不提供调度或设备控制。唯一传输是本地JSONL，一行一个不可变快照。schema为TTO-STATE-READONLY-R2-v1。

## 入口与例子

已有记录：runs/final/cases/Y/states/AUGMENTED-KF-interface.jsonl。M的各遮挡情景也有同结构文件。交付时另给fixtures/read-only-state-examples.jsonl，包含记录流中的五类阶段。

离线只读消费：

~~~sh
python consume_example.py fixtures/read-only-state-examples.jsonl
~~~

假流可调用synthetic.synthetic_frame构造，随后传入observer.ThermalObserver.step；明确标记SYNTHETIC。不要把它的温度、时刻或状态当成现场证据。例子没有任何poll/request/start/stop调度动作。

## 五组字段语义

| 组 | 字段 | 用法 |
|---|---|---|
| identity | run_id、config_sha256、firmware_identity、collector_source_sha256、model_sha256、spec_sha256、source_epoch | 不同身份不拼状态；未知固件保留null。模型是冻结参数身份，不能拿公开main当现场0.2.4 |
| 生成/截止 | generated_at_mono_s、generated_at_utc、generated_clock_domain、observed_through_ref/utc | 生成时刻是明示的离线虚拟回放时钟；真实文件写入时刻在运行回执。不是设备实时服务输出 |
| measurement | tj、power、last_successful_pwm、control_context | 保留原值/引用、observed_mono_s、age_s、valid_until_mono_s、raw_valid。最后成功PWM的数值只说明历史那一条；raw_valid=false时不能当当前实测PWM |
| observer | phase、available、Tf_C/Ts_C/E_C、E_source、reasons、unknown_input_assumptions、uncertainty | available包含provisional/degraded；不是正常资格。条件PWM在conditional_inputs_rails_W_PWM，与实测字段分开。E是推断边界，不是室温 |
| safety | guard/fault/mode/enabled、temp_stale、normalized_valid、binding/active_source、fan_fresh/binding_fresh、confirmed_normal_now | current字段只在相应源新鲜时给值，未知为null；历史last_observed_flags只能按历史解读。没有异常证据不等于已确认正常 |
| permission | local_demo、formal_field_authorized、device_actions | 本轮恒为true/false/false。研究状态永远不能单独授权发负载 |

phase枚举：uninitialized、provisional、tracking、degraded、unavailable。有限数值不自动tracking；内部tracking也不证明真实Ts、预测可靠或现场安全。不可用时公开Tf/Ts/E为null，不能插补连线。

内部covariance_C2和marginal_std_C只描述注册模型/噪声/条件输入假设，不含动态θ误差、真实未来负载、仪表时钟误差。calibrated=false；不要显示成95%置信区间或安全温度上下界。

## 与原TTO保存流的映射

TJ和两rail来自manifest匹配native处理器的accepted新样本。rail依次vdd_gpu、vdd_cpu_soc_mss，单位W；不是整机功耗或纯CPU/GPU贡献识别。PWM来自成功fan响应的native successful_duty，界面保留percent，模型输入除以100。

fan TTL 2.5秒、temp状态TTL 7.5秒、source年龄/有效期不改。HTTP失败后可以在observer中假设保持最后PWM；measurement.raw_valid不会被估计器续龄。显式guard/fault/非AUTO/手动状态、绑定/源变化与普通超时不同；原因和原始flags都交出。任务阶段不是重置条件。

#9只需核对measurement来源和候选身份，不必按本线的滤波器修生产模块。#10消费同一快照；估计不可用须拒绝正式模型对照，估计可用仍需独立满足当前测量、保护、仪表/时钟和本轮实际授权。用户未授权现场，consumer示例始终formal_comparison_allowed=false。

## 已完成的离线链

启动缺输入、短缺口保留历史、HTTP失败但TJ有效、长缺失停输出及恢复、无tick长静默、guard/fault/模式/绑定/源epoch、未来TJ/隐藏PWM/表面非干扰均有有限测试。真实Y全部事件流与M遮挡结果可以复核。这里没有通讯现场根因、正式准入或控制收益结论。

上下文确认的5秒只按原TTL内的观测支持计时；未知或到期段清除这段确认计时，恢复后重新累计。它不证明采样间的设备实况无变化，也不替代#9通讯健康或#10准入。最终Y只有97/1843个内部tracking，剩余主要为degraded条件状态。
