# TTO 模拟采集报告

模拟演示：软件贯通，不代表实机连接或预测收益。

下一步：按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|仅模拟，未连接设备|
|部署核对|现场部署未核对|
|有效新测量|720|
|重复缓存|0|
|正常AUTO起点|144|
|正常CURVE起点|0|
|合格且平台已确认起点|144|
|GPU有效新样本/新TJ样本|720/720|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_orin / confirmed|
|实际模式/计划起点|auto: 144|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|144/144|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx.tj|
|控制资格缺项|控制条件已观察到；仍需冻结模型与完整过程证据|
|建模准备|input_scope_observed_model_effect_unverified|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|720|720|100.0%|
|temperature.soc0 [C]|720|720|100.0%|
|temperature.tj [C]|720|720|100.0%|
|power.vdd_cpu_cv.current [W]|720|720|100.0%|
|power.vdd_gpu_soc.current [W]|720|720|100.0%|
|power.vin_sys_5v0.current [W]|720|720|100.0%|


```json
{
  "kind": "diagnostic_replay_only_not_historical_predictions",
  "platform_declaration": {
    "platform": {
      "compatible": [
        "nvidia,tegra234"
      ],
      "family": "jetson_orin",
      "gpu_backend": "tegrastats",
      "identification_source": "device_tree_compatible",
      "schema_version": 1,
      "soc": "tegra234"
    },
    "ref": "d483e4f8-31c1-449d-8205-ddcbf569ce23/observation:1584",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "d483e4f8-31c1-449d-8205-ddcbf569ce23/observation:1584"
  },
  "counts": {
    "temperature_status_records": 144,
    "valid_temperature_status_records": 144,
    "new_tj_samples": 720,
    "gpu_usable_new_samples": 720,
    "planned_origins": 144,
    "eligible_origins": 144,
    "normal_auto_origins": 144,
    "normal_curve_origins": 0
  },
  "control_scopes": {
    "auto": 144
  },
  "control_ineligible_reasons": {},
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 1200,
    "ref": "d483e4f8-31c1-449d-8205-ddcbf569ce23/observation:1575"
  },
  "gpu_source_status_counts": {
    "valid": 720
  },
  "gpu_unavailable_reasons": {
    "usable": 720
  },
  "gpu_latest": {
    "value": 44.31659875889299,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 0,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": null,
    "valid_until": 724.0,
    "contract_valid": true,
    "ref": "d483e4f8-31c1-449d-8205-ddcbf569ce23/observation:1584",
    "observer_receive_mono_s": 719.0,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 0.0
  },
  "gpu_coverage": {
    "numerator": 720,
    "denominator": 720,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    },
    "temperature.soc0 [C]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    },
    "power.vdd_cpu_cv.current [W]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    },
    "power.vdd_gpu_soc.current [W]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 720,
      "denominator": 720,
      "fraction": 1.0
    }
  },
  "mixed_profiles": false,
  "model_readiness": "input_scope_observed_model_effect_unverified",
  "process_completeness": "operator_start_end_and_cooldown_evidence_required",
  "note": "具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。"
}
```
## 关联人工记录

未登记人工任务起止；不自动推断独立过程。

```json
{
  "present": false,
  "records": [],
  "note": "未登记人工任务起止；不自动推断独立过程。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
