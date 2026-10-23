# TTO 模拟采集报告

模拟演示：软件贯通，不代表实机连接或预测收益。 本轮存在不兼容输入合同或控制范围，正式建库拒绝；历史已发记录和恢复段有效评分仍保留。

下一步：保留本轮合同变化、隔离及恢复证据；不将混合run直接冻结为正式数据集。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|仅模拟，未连接设备|
|部署核对|现场部署未核对|
|有效新测量|220|
|重复缓存|0|
|正常AUTO起点|0|
|正常CURVE起点|44|
|合格且平台已确认起点|44|
|GPU有效新样本/新TJ样本|220/220|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|curve: 44|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|221/221|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx.tj|
|控制资格缺项|控制条件已观察到；仍需冻结模型与完整过程证据|
|建模准备|blocked_by_mixed_profiles|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|220|220|100.0%|
|temperature.soc0 [C]|220|220|100.0%|
|temperature.tj [C]|220|220|100.0%|
|power.vdd_cpu_cv.current [W]|220|220|100.0%|
|power.vdd_gpu_soc.current [W]|220|220|100.0%|
|power.vin_sys_5v0.current [W]|220|220|100.0%|


```json
{
  "kind": "diagnostic_replay_only_not_historical_predictions",
  "platform_declaration": {
    "platform": {
      "compatible": [
        "nvidia,tegra264"
      ],
      "family": "jetson_thor",
      "gpu_backend": "nvml",
      "identification_source": "device_tree_compatible",
      "schema_version": 1,
      "soc": "tegra264"
    },
    "ref": "3cf53b21-5883-46ec-b471-c51822e2dede/observation:663",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "3cf53b21-5883-46ec-b471-c51822e2dede/observation:663"
  },
  "counts": {
    "temperature_status_records": 221,
    "valid_temperature_status_records": 221,
    "new_tj_samples": 220,
    "gpu_usable_new_samples": 220,
    "planned_origins": 44,
    "eligible_origins": 44,
    "normal_auto_origins": 0,
    "normal_curve_origins": 44
  },
  "control_scopes": {
    "curve": 44
  },
  "control_ineligible_reasons": {},
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 1200,
    "ref": "3cf53b21-5883-46ec-b471-c51822e2dede/observation:662"
  },
  "gpu_source_status_counts": {
    "valid": 220
  },
  "gpu_unavailable_reasons": {
    "usable": 220
  },
  "gpu_latest": {
    "value": 0,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 0,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-SYNTHETIC-REVIEW",
    "valid_until": 225.0,
    "contract_valid": true,
    "ref": "3cf53b21-5883-46ec-b471-c51822e2dede/observation:663",
    "observer_receive_mono_s": 220.0,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 0.0
  },
  "gpu_coverage": {
    "numerator": 220,
    "denominator": 220,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    },
    "temperature.soc0 [C]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    },
    "power.vdd_cpu_cv.current [W]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    },
    "power.vdd_gpu_soc.current [W]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 220,
      "denominator": 220,
      "fraction": 1.0
    }
  },
  "mixed_profiles": true,
  "model_readiness": "blocked_by_mixed_profiles",
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
