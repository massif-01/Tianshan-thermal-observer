# TTO 采集质量报告

软件可用，预测效果待验证。

下一步：按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|已收到新测量，完整可靠性仍需核对|
|部署核对|现场部署未核对|
|有效新测量|1794|
|重复缓存|4|
|正常AUTO起点|355|
|正常CURVE起点|0|
|合格且平台已确认起点|355|
|GPU有效新样本/新TJ样本|1794/1794|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|auto: 376, unknown: 6|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|357/359|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx_info.temperature.tj|
|控制资格缺项|模式不在AUTO/CURVE范围（6个起点）；风扇状态缺失或过期（21个起点）；风扇未启用（6个起点）；风扇故障（6个起点）；保护生效（6个起点）；控制温度过期（10个起点）；成功PWM不可用（6个起点）；控制温度状态无效（4个起点）；实际温度来源尚未可信（4个起点）|
|建模准备|input_scope_observed_model_effect_unverified|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|1794|1794|100.0%|
|temperature.gpu [C]|1794|1794|100.0%|
|temperature.soc012 [C]|1794|1794|100.0%|
|temperature.soc345 [C]|1794|1794|100.0%|
|temperature.tj [C]|1794|1794|100.0%|
|power.vdd_cpu_soc_mss.current [W]|1794|1794|100.0%|
|power.vdd_gpu.current [W]|1794|1794|100.0%|
|power.vin_sys_5v0.current [W]|1794|1794|100.0%|


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
    "ref": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb/observation:5570",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb/observation:5570"
  },
  "counts": {
    "temperature_status_records": 359,
    "valid_temperature_status_records": 357,
    "new_tj_samples": 1794,
    "gpu_usable_new_samples": 1794,
    "planned_origins": 382,
    "eligible_origins": 355,
    "normal_auto_origins": 355,
    "normal_curve_origins": 0
  },
  "control_scopes": {
    "auto": 376,
    "unknown": 6
  },
  "control_ineligible_reasons": {
    "unsupported_control_scope": 6,
    "fan_missing_or_stale": 21,
    "fan_not_enabled": 6,
    "fan_fault": 6,
    "guard_active": 6,
    "control_temperature_stale": 10,
    "successful_duty_unavailable": 6,
    "control_temperature_invalid": 4,
    "active_temperature_source_untrusted": 4
  },
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx_info.temperature.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 30678183,
    "ref": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb/observation:5565"
  },
  "gpu_source_status_counts": {
    "valid": 1794
  },
  "gpu_unavailable_reasons": {
    "usable": 1794
  },
  "gpu_latest": {
    "value": 81,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 914.9423869966995,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-a7c66ad2-6dbb-0ab8-c1a2-37ba6dba3600",
    "valid_until": 243982.88286214002,
    "contract_valid": true,
    "ref": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb/observation:5570",
    "observer_receive_mono_s": 243978.797804527,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 1158.1748979806434
  },
  "gpu_coverage": {
    "numerator": 1794,
    "denominator": 1794,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "temperature.gpu [C]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 1794,
      "denominator": 1794,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 1794,
      "denominator": 1794,
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
  "sha256": "d52b1d75db49d4fd19bc9d9aa296e503d30a6831bea41b2ffe6707b0b3044dcd",
  "declared_index_sha256": "d52b1d75db49d4fd19bc9d9aa296e503d30a6831bea41b2ffe6707b0b3044dcd",
  "index_matches": true,
  "records": [
    {
      "record_ref": "operator-records.jsonl:1",
      "raw": {
        "kind": "collection_authorized",
        "source": "human_instruction",
        "verbatim": "我们现在来来开始采集，默认30min，途中我可能会随时叫你停止。这个过程中，我会涉及几个工况：1.空载待机，2.模型拉起，3.拉起后（有负载）待机，4.模型单发推理，5.并发推理，6.推理后待机",
        "recorded_at_utc": "2026-10-13T02:22:47.006251+00:00",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
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
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "collection_started_at_utc": "2026-10-13T02:22:46.371313+00:00",
        "recorded_at_utc": "2026-10-13T02:22:47.006279+00:00",
        "expected_end_at_utc": "2026-10-13T02:52:46.371313+00:00",
        "condition_id": null
      }
    },
    {
      "record_ref": "operator-records.jsonl:3",
      "raw": {
        "kind": "control_mode_observed",
        "source": "actual_mainboard_status",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "recorded_at_utc": "2026-10-13T02:23:37.503791+00:00",
        "observed_received_at_utc": "2026-10-13T02:23:37.254571+00:00",
        "observation_ref": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb/observation:163",
        "mode": "auto",
        "note": "Current motherboard mode differs from prior CURVE installation check; preserve actual mode, no mode/control write performed. Operating condition has not yet been human-reported."
      }
    },
    {
      "record_ref": "operator-records.jsonl:4",
      "raw": {
        "kind": "condition_reported",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "condition_id": 1,
        "condition_label": "空载待机",
        "source": "human_report",
        "verbatim": "现在是工况1空载待机",
        "reported_event_time": {
          "description": "用户上报时当前处于空载待机；实际进入该工况的起始时刻未提供",
          "precision": "approximate_current_state",
          "exact_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T02:24:09.638107+00:00",
        "previous_condition_id": null,
        "collection_continues": true
      }
    },
    {
      "record_ref": "operator-records.jsonl:5",
      "raw": {
        "kind": "control_mode_clarification",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "source": "human_report",
        "verbatim": "风扇是TTI智能模式不会变",
        "operator_mode_label": "TTI智能模式",
        "reported_intent": "风扇模式在本轮保持不变",
        "observed_api_mode_at_collection_start": "auto",
        "recorded_at_utc": "2026-10-13T02:24:36.211558+00:00",
        "note": "User mode label and observed API mode retained separately; no control write performed. Collection and condition 1 continue."
      }
    },
    {
      "record_ref": "operator-records.jsonl:6",
      "raw": {
        "kind": "condition_started_reported",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "condition_id": 2,
        "condition_label": "模型拉起",
        "source": "human_report",
        "verbatim": "现在开始工况2，模型拉起，刚点击启动。",
        "reported_event_time": {
          "description": "用户报告刚点击模型启动，作为近似开始说明",
          "precision": "approximate_just_started",
          "exact_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T02:25:20.783294+00:00",
        "previous_condition_id": 1,
        "previous_condition_transition": "用户上报切换至工况2；没有独立精确结束时间",
        "collection_continues": true
      }
    },
    {
      "record_ref": "operator-records.jsonl:7",
      "raw": {
        "kind": "condition_transition_reported",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "source": "human_report",
        "verbatim": "模型拉起完成了，现在进入工况3，模型保持运行，暂时不做推理，继续采集。",
        "previous_condition_id": 2,
        "completed_condition_id": 2,
        "completed_condition_label": "模型拉起",
        "completion_status": "normal_completion_reported",
        "condition_id": 3,
        "condition_label": "模型保持运行，暂时不做推理",
        "reported_event_time": {
          "description": "用户报告模型拉起已完成，当前进入模型运行但不推理的待机工况；起止时间为人工上报的近似说明",
          "precision": "approximate_transition_now",
          "exact_end_at_utc": null,
          "exact_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T02:28:52.076929+00:00",
        "collection_continues": true
      }
    },
    {
      "record_ref": "operator-records.jsonl:8",
      "raw": {
        "kind": "condition_started_reported",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "condition_id": 4,
        "condition_label": "模型单发推理",
        "source": "human_report",
        "verbatim": "现在开始工况4，模型单发推理，刚点击运行，继续采集。",
        "reported_event_time": {
          "description": "用户报告刚点击单发推理运行，作为近似开始说明",
          "precision": "approximate_just_started",
          "exact_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T02:34:12.439350+00:00",
        "previous_condition_id": 3,
        "previous_condition_transition": "用户上报切换至工况4；没有独立精确结束时间",
        "collection_continues": true
      }
    },
    {
      "record_ref": "operator-records.jsonl:9",
      "raw": {
        "kind": "condition_transition_reported",
        "observer_run_id": "c1a1bd6a-7854-4d08-bea7-42ea1335c0eb",
        "source": "human_report",
        "verbatim": "工况4单发推理10:43完成的，现在开始工况5并发推理，刚点击运行，继续采集。",
        "previous_condition_id": 4,
        "completed_condition_id": 4,
        "completed_condition_label": "模型单发推理",
        "completion_status": "normal_completion_reported",
        "reported_completion_time": {
          "local_date": "2026-10-13",
          "local_time": "10:43",
          "timezone": "Asia/Shanghai",
          "precision": "minute",
          "exact_end_at_utc": null,
          "description": "用户明确上报10:43完成；未提供秒数，不补造秒级结束时间"
        },
        "condition_id": 5,
        "condition_label": "并发推理",
        "reported_start_time": {
          "description": "用户报告刚点击并发推理运行，作为近似开始说明",
          "precision": "approximate_just_started",
          "exact_start_at_utc": null
        },
        "recorded_at_utc": "2026-10-13T02:45:28.223386+00:00",
        "collection_continues": true
      }
    }
  ],
  "issues": [],
  "note": "保留关联人工原文、来源、近似事件时刻与写入时刻；任务结束不代表回落采集应停止，也不自动授予过程独立性。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
