# G2只读因果接口1.0

入口为`from g2_runtime import Predictor, ThermalObserver`。测试线只复制本包；不另写G2传播。`ThermalObserver.step`和三份数学原件保持字节，`Predictor.predict`只组织输入、调用原`mean_step`并给出发布记录。

```python
predictor = Predictor()  # 默认同目录frozen-model-manifest.json
records = predictor.predict(
    state, origin=origin, observed_through=observed_through,
    issued_at=issued_at, identity=identity,
    publication_mode='live', history=past_accepted_TJ)
```

每次返回9条：15/45/90秒各G2-HOLD、B0、B1；每项有值或明确不可用原因。原状态不被修改。预测不读未来输入、业务计划、任务结束或外部测温，不含CPU活动→高功率策略。

|参数|唯一映射|
|---|---|
|state|同一SavedStream/I-02本次`ThermalObserver.step`原样结果；不能先处理下个TJ再回填|
|origin.ref/value_C/received_at_mono_s/received_at_utc/raw_valid|原`state.measurement.tj`的source_ref/value_C/observed_mono_s/observed_utc/raw_valid|
|origin.source_epoch/clock_domain|原state.identity.source_epoch与外层真实process_clock_domain|
|observed_through.ref/mono_s/clock_domain|state.observed_through_ref / state.generated_at_mono_s / 同一外层域；原state时钟文字不被改写为live证据|
|issued_at.mono_s/utc/clock_domain|调用方在真实生成/发布时记录的本进程时刻、UTC及域；不能用输入接收时间回填；若排队延迟，必须按真实发布时刻重新调用而不能沿用早期草稿|
|identity|明确device_id、thermal_config_id、observer_host_id、run_id、clock_domain；boot_id已知就填，未知为null。配置ID为登记身份，物理细节未知不填造|
|history|同一原质量引擎已接受TJ列表；字段同origin，按原接收顺序。B1只用原TJ前30秒，至少10秒支持，跨epoch/超过5秒缺口不连线|

只在新的有效原TJ起点发布。观测截止必须等于该TJ原接收时刻；如果状态已吸收之后观测，返回`state_not_at_TJ_origin`，不得倒贴。所有方法使用同一信息截止/发布时点。target=原接收anchor+h，effective_lead=target-issued_at；到/超过目标则值null，原因`issued_at_or_after_target`，不冒充有效提前预测。

新实时口径固定为`TTO-RECEIVE-ANCHOR-v1`。旧历史以状态生成时刻作起点的评分保持原样另列，不能混合排名。历史加速调用必须`publication_mode='replay'`；golden中的历史issued_at来自原外层记录，注入案例使用明确的replay虚拟时刻，全部不是本轮live成绩。

G2从同一实际TJ及原因果Ts/E出发，两个独立rail和声明PWM按HOLD固定。原KF的Tf另有意义，不替换实测TJ锚点。provisional/degraded可按原spec作条件预测，并保留phase/assumptions；长期缺失或原观察器unavailable则G2为null。PWM假设不是成功PWM、目标PWM或RPM；不更新测量TTL。不确定性沿原内部假设，不能叫校准95%概率。

B0/B1在原TJ有效时可保留；原guard/fault/unknown等safety字段每项原样带出，基线有限可算不代表正常或控制许可。所有`control_permission=false`。不同设备/会话的估计器由集成方分别创建，纯Predictor不缓存任何设备热状态。

离线JSON入口：在本目录运行`python -m g2_runtime --input golden/request.json --output /private/tmp/tto-g2-forecast-NEW.json`，输出必须不存在。仅使用既有NumPy/SciPy；数值库单线程由观察进程原numeric_policy负责，不改全机环境。

跨端golden见`golden/cases.json`，容差1e-8°C。正常状态来自已接受fixed-anchors原记录；短/长缺口与恢复是明确标记的、基于该前缀调用原观察器的故障注入，不冒称新的现场。boot未知仍为null。有限测试：`python -m pytest -c pytest.ini tests --confcutdir=. -q`。
