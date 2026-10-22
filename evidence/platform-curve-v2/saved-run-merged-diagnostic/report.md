# TTO 采集质量报告

软件可用，预测效果待验证。 已收到TJ也不代表可建模：平台身份或实际控制温度/来源尚未满足资格。

下一步：先核对平台声明、GPU缺项和控制温度实际有效性；保留CURVE原状，现场来源核对另行安排。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|已收到新测量，完整可靠性仍需核对|
|部署核对|现场部署未核对|
|有效新测量|196|
|重复缓存|0|
|正常AUTO起点|0|
|正常CURVE起点|0|
|合格且平台已确认起点|0|
|GPU有效新样本/新TJ样本|0/196|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|unknown / platform_contract_missing_or_invalid|
|实际模式/计划起点|curve: 38|
|GPU来源封存状态|legacy_no_independent_status|
|观察器当前GPU有效|否|
|源周期ms / 依据|1000 / operator_legacy|
|有效控制温度状态/收到状态|0/40|
|配置温度来源 / 实际温度来源|variable / default|
|配置绑定|agx_info.temperature.tj|
|控制资格缺项|控制温度状态无效（38个起点）；实际温度来源尚未可信（38个起点）|
|建模准备|blocked_by_identity_or_control_qualification|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|196|196|100.0%|
|temperature.gpu [C]|196|196|100.0%|
|temperature.soc012 [C]|196|196|100.0%|
|temperature.soc345 [C]|196|196|100.0%|
|temperature.tj [C]|196|196|100.0%|
|power.vdd_cpu_soc_mss.current [W]|196|196|100.0%|
|power.vdd_gpu.current [W]|196|196|100.0%|
|power.vin_sys_5v0.current [W]|196|196|100.0%|


```json
{
  "kind": "diagnostic_replay_only_not_historical_predictions",
  "platform_declaration": {
    "platform": null,
    "ref": "7113c960-2306-443c-b3ba-002dbfeb08d5/observation:624",
    "evidence_status": "platform_contract_missing_or_invalid"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "operator_legacy",
    "reason": null,
    "ref": "7113c960-2306-443c-b3ba-002dbfeb08d5/observation:624"
  },
  "counts": {
    "temperature_status_records": 40,
    "valid_temperature_status_records": 0,
    "new_tj_samples": 196,
    "gpu_usable_new_samples": 0,
    "planned_origins": 38,
    "eligible_origins": 0,
    "normal_auto_origins": 0,
    "normal_curve_origins": 0
  },
  "control_scopes": {
    "curve": 38
  },
  "control_ineligible_reasons": {
    "control_temperature_invalid": 38,
    "active_temperature_source_untrusted": 38
  },
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "default",
    "bound_variable": "agx_info.temperature.tj",
    "manual_mode": false,
    "normalized_valid": false,
    "timestamp_ms": 0,
    "ref": "7113c960-2306-443c-b3ba-002dbfeb08d5/observation:625"
  },
  "gpu_source_status_counts": {
    "legacy_no_independent_status": 196
  },
  "gpu_unavailable_reasons": {
    "legacy_gpu_missing_or_invalid": 196
  },
  "gpu_latest": {
    "value": null,
    "reason": "legacy_gpu_missing_or_invalid",
    "source_status": "legacy_no_independent_status",
    "age_lower_bound_ms": 39.62635199422948,
    "timeout_ms": 5000,
    "sample_interval_ms": null,
    "device_uuid": null,
    "valid_until": null,
    "contract_valid": false,
    "ref": "7113c960-2306-443c-b3ba-002dbfeb08d5/observation:624",
    "observer_receive_mono_s": 189392.049159496,
    "observer_current_valid": false,
    "observer_current_age_lower_bound_ms": 837.1941529912874
  },
  "gpu_coverage": {
    "numerator": 0,
    "denominator": 196,
    "fraction": 0.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "temperature.gpu [C]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 196,
      "denominator": 196,
      "fraction": 1.0
    }
  },
  "mixed_profiles": false,
  "model_readiness": "blocked_by_identity_or_control_qualification",
  "process_completeness": "operator_start_end_and_cooldown_evidence_required",
  "note": "具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
