# TTO 采集质量报告

软件可用，预测效果待验证。

下一步：按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|已收到新测量，完整可靠性仍需核对|
|部署核对|现场部署未核对|
|有效新测量|179|
|重复缓存|1|
|正常AUTO起点|0|
|正常CURVE起点|35|
|合格且平台已确认起点|35|
|GPU有效新样本/新TJ样本|179/179|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|curve: 35|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|36/36|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx_info.temperature.tj|
|控制资格缺项|控制条件已观察到；仍需冻结模型与完整过程证据|
|建模准备|input_scope_observed_model_effect_unverified|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|179|179|100.0%|
|temperature.gpu [C]|179|179|100.0%|
|temperature.soc012 [C]|179|179|100.0%|
|temperature.soc345 [C]|179|179|100.0%|
|temperature.tj [C]|179|179|100.0%|
|power.vdd_cpu_soc_mss.current [W]|179|179|100.0%|
|power.vdd_gpu.current [W]|179|179|100.0%|
|power.vin_sys_5v0.current [W]|179|179|100.0%|


```json
{
  "kind": "diagnostic_replay_only_not_historical_predictions",
  "platform_declaration": {
    "platform": {
      "compatible": [
        "rm01,rm01-thor",
        "nvidia,p3834-0008",
        "nvidia,tegra264"
      ],
      "family": "jetson_thor",
      "gpu_backend": "nvml",
      "identification_source": "device_tree_compatible",
      "schema_version": 1,
      "soc": "tegra264"
    },
    "ref": "c1a2125e-9b02-4e93-b53f-70790ce230ac/observation:573",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "c1a2125e-9b02-4e93-b53f-70790ce230ac/observation:573"
  },
  "counts": {
    "temperature_status_records": 36,
    "valid_temperature_status_records": 36,
    "new_tj_samples": 179,
    "gpu_usable_new_samples": 179,
    "planned_origins": 35,
    "eligible_origins": 35,
    "normal_auto_origins": 0,
    "normal_curve_origins": 35
  },
  "control_scopes": {
    "curve": 35
  },
  "control_ineligible_reasons": {},
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx_info.temperature.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 24936018,
    "ref": "c1a2125e-9b02-4e93-b53f-70790ce230ac/observation:562"
  },
  "gpu_source_status_counts": {
    "valid": 179
  },
  "gpu_unavailable_reasons": {
    "usable": 179
  },
  "gpu_latest": {
    "value": 0,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 1242.037968011573,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-a7c66ad2-6dbb-0ab8-c1a2-37ba6dba3600",
    "valid_until": 212758.3434058,
    "contract_valid": true,
    "ref": "c1a2125e-9b02-4e93-b53f-70790ce230ac/observation:573",
    "observer_receive_mono_s": 212754.585443768,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 1503.85519998963
  },
  "gpu_coverage": {
    "numerator": 179,
    "denominator": 179,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "temperature.gpu [C]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 179,
      "denominator": 179,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 179,
      "denominator": 179,
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

保留关联人工原文、来源、近似事件时刻与写入时刻；任务结束不代表回落采集应停止，也不自动授予过程独立性。

```json
{
  "present": true,
  "sha256": "7fc672f308654cec4cc5ba4d2140026b04fde12b63edf3b7f95fb2eeac668b9d",
  "declared_index_sha256": "7fc672f308654cec4cc5ba4d2140026b04fde12b63edf3b7f95fb2eeac668b9d",
  "index_matches": true,
  "records": [
    {
      "record_ref": "operator-records.jsonl:1",
      "raw": {
        "kind": "installation_connection_check_started",
        "observer_run_id": "c1a2125e-9b02-4e93-b53f-70790ce230ac",
        "source": "assistant_observed_collector_manifest",
        "collection_started_at_utc": "2026-10-12T18:09:22.178255+00:00",
        "recorded_at_utc": "2026-10-12T18:09:53.058335+00:00",
        "duration_s": 180,
        "formal_task_collection": false,
        "task_id": null,
        "purpose": "Verify installed TTO 0.2.2 against Thor service 1.1.1 and motherboard CURVE data"
      }
    }
  ],
  "issues": [],
  "note": "保留关联人工原文、来源、近似事件时刻与写入时刻；任务结束不代表回落采集应停止，也不自动授予过程独立性。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
