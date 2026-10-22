# TTO 采集质量报告

软件可用，预测效果待验证。

下一步：按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|已收到新测量，完整可靠性仍需核对|
|部署核对|现场部署未核对|
|有效新测量|364|
|重复缓存|1|
|正常AUTO起点|73|
|正常CURVE起点|0|
|合格且平台已确认起点|73|
|GPU有效新样本/新TJ样本|364/364|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|auto: 73|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|73/73|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx_info.temperature.tj|
|控制资格缺项|控制条件已观察到；仍需冻结模型与完整过程证据|
|建模准备|input_scope_observed_model_effect_unverified|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|364|364|100.0%|
|temperature.gpu [C]|364|364|100.0%|
|temperature.soc012 [C]|364|364|100.0%|
|temperature.soc345 [C]|364|364|100.0%|
|temperature.tj [C]|364|364|100.0%|
|power.vdd_cpu_soc_mss.current [W]|364|364|100.0%|
|power.vdd_gpu.current [W]|364|364|100.0%|
|power.vin_sys_5v0.current [W]|364|364|100.0%|


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
    "ref": "f43af598-d8e1-43f2-824b-9471d35b0593/observation:1162",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "f43af598-d8e1-43f2-824b-9471d35b0593/observation:1162"
  },
  "counts": {
    "temperature_status_records": 73,
    "valid_temperature_status_records": 73,
    "new_tj_samples": 364,
    "gpu_usable_new_samples": 364,
    "planned_origins": 73,
    "eligible_origins": 73,
    "normal_auto_origins": 73,
    "normal_curve_origins": 0
  },
  "control_scopes": {
    "auto": 73
  },
  "control_ineligible_reasons": {},
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx_info.temperature.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 31430751,
    "ref": "f43af598-d8e1-43f2-824b-9471d35b0593/observation:1152"
  },
  "gpu_source_status_counts": {
    "valid": 364
  },
  "gpu_unavailable_reasons": {
    "usable": 364
  },
  "gpu_latest": {
    "value": 0,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 1575.1148349954747,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-a7c66ad2-6dbb-0ab8-c1a2-37ba6dba3600",
    "valid_until": 244735.642847871,
    "contract_valid": true,
    "ref": "f43af598-d8e1-43f2-824b-9471d35b0593/observation:1162",
    "observer_receive_mono_s": 244732.217962706,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 2206.1230689869262
  },
  "gpu_coverage": {
    "numerator": 364,
    "denominator": 364,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "temperature.gpu [C]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 364,
      "denominator": 364,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 364,
      "denominator": 364,
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
  "sha256": "42ba036f2663f6160b35bb369aa03ef6c21e91c73d0a0e55da48959aa18585c4",
  "declared_index_sha256": "42ba036f2663f6160b35bb369aa03ef6c21e91c73d0a0e55da48959aa18585c4",
  "index_matches": true,
  "records": [
    {
      "record_ref": "operator-records.jsonl:1",
      "raw": {
        "kind": "collection_authorized",
        "source": "human_instruction",
        "verbatim": "工况5并发推理完成了，现在进入工况6，推理后待机，继续采集温度回落。",
        "recorded_at_utc": "2026-10-13T02:59:15.499732+00:00",
        "observer_run_id": "f43af598-d8e1-43f2-824b-9471d35b0593",
        "duration_s": 1800,
        "condition_plan": [
          {
            "id": 1,
            "label": "空载待机"
          },
          {
            "id": 2,
            "label": "模型拉起"
          },
          {
            "id": 3,
            "label": "拉起后（有负载）待机"
          },
          {
            "id": 4,
            "label": "模型单发推理"
          },
          {
            "id": 5,
            "label": "并发推理"
          },
          {
            "id": 6,
            "label": "推理后待机"
          }
        ],
        "actual_condition": "not_yet_reported",
        "event_time_precision": "instruction authorizes collection; this is not a reported condition start time"
      }
    },
    {
      "record_ref": "operator-records.jsonl:2",
      "raw": {
        "kind": "collection_started",
        "source": "assistant_observed_collector_manifest",
        "observer_run_id": "f43af598-d8e1-43f2-824b-9471d35b0593",
        "collection_started_at_utc": "2026-10-13T02:59:14.931136+00:00",
        "recorded_at_utc": "2026-10-13T02:59:15.499761+00:00",
        "expected_end_at_utc": "2026-10-13T03:29:14.931136+00:00",
        "condition_id": null
      }
    },
    {
      "record_ref": "operator-records.jsonl:3",
      "raw": {
        "kind": "condition_6_continuation_reported",
        "observer_run_id": "f43af598-d8e1-43f2-824b-9471d35b0593",
        "source": "human_report",
        "verbatim": "工况5并发推理完成了，现在进入工况6，推理后待机，继续采集温度回落。",
        "time_clarification_verbatim": "并发结束时间是2026 年 10 月 13 日 10:56:35.734",
        "completed_condition_id": 5,
        "completed_condition_label": "并发推理",
        "completion_status": "normal_completion_reported",
        "reported_completion_at_local": "2026-10-13T10:56:35.734+08:00",
        "reported_completion_at_utc": "2026-10-13T02:56:35.734+00:00",
        "reported_completion_precision": "millisecond_as_provided",
        "time_verification": "human_report_not_independently_verified",
        "condition_id": 6,
        "condition_label": "推理后待机",
        "recorded_at_utc": "2026-10-13T02:59:16.449558+00:00",
        "original_collection_ended_at_utc": "2026-10-13T02:52:46.386363+00:00",
        "completion_after_original_collection": true,
        "note": "Late annotation stored beside closed run; original logs and files index remain unchanged. A new bounded run continues same thermal episode; gap is real.",
        "previous_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "previous_run_path": "/home/rm01/TTO/runs/run-2026-10-13T022246.369032_0000-c1a1bd6a",
        "resumed_collection_started_at_utc": "2026-10-13T02:59:14.931136+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:4",
      "raw": {
        "kind": "additional_condition_reported",
        "observer_run_id": "f43af598-d8e1-43f2-824b-9471d35b0593",
        "source": "human_report",
        "verbatim": "现在多加一个工况记录，就是模型下掉，回到1的空载待机，我现在已经进入，你可以采集了",
        "condition_id": 7,
        "condition_label": "模型卸载后空载待机",
        "equivalent_operating_condition_id": 1,
        "previous_condition_id": 6,
        "model_state_reported": "模型已下掉",
        "reported_event_time": {
          "description": "用户报告当前已进入模型下掉后的空载待机；卸载开始、完成及进入待机的精确时刻未提供",
          "precision": "approximate_current_state",
          "exact_unload_start_at_utc": null,
          "exact_unload_end_at_utc": null,
          "exact_idle_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T03:03:37.066276+00:00",
        "collection_continues": true,
        "note": "Added phase 7 to distinguish post-unload idle from initial phase 1; no inference about exact unloading duration."
      }
    },
    {
      "record_ref": "operator-records.jsonl:5",
      "raw": {
        "kind": "collection_stop_requested",
        "observer_run_id": "f43af598-d8e1-43f2-824b-9471d35b0593",
        "source": "human_instruction",
        "verbatim": "现在停止采集，保存好数据和操作记录，然后帮我分析一下各个工况的温度、功耗、GPU利用率和风扇变化。",
        "recorded_at_utc": "2026-10-13T03:05:20.170932+00:00",
        "reported_event_time_precision": "stop_requested_now; writer time is not exact user message time",
        "active_condition_id": 7
      }
    }
  ],
  "issues": [],
  "note": "保留关联人工原文、来源、近似事件时刻与写入时刻；任务结束不代表回落采集应停止，也不自动授予过程独立性。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
