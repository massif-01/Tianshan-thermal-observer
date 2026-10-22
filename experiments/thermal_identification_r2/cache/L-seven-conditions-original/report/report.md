# TTO 采集质量报告

软件可用，预测效果待验证。

下一步：按完整使用过程确认分组，在新路径冻结合法切分并做离线时间留出评估。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|已收到新测量，完整可靠性仍需核对|
|部署核对|现场部署未核对|
|有效新测量|2529|
|重复缓存|5|
|正常AUTO起点|505|
|正常CURVE起点|0|
|合格且平台已确认起点|505|
|GPU有效新样本/新TJ样本|2529/2529|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|auto: 517, unknown: 3|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|503/504|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx_info.temperature.tj|
|控制资格缺项|模式不在AUTO/CURVE范围（3个起点）；风扇状态缺失或过期（13个起点）；风扇未启用（3个起点）；风扇故障（3个起点）；保护生效（3个起点）；控制温度过期（4个起点）；成功PWM不可用（3个起点）；控制温度状态无效（2个起点）；实际温度来源尚未可信（2个起点）|
|建模准备|input_scope_observed_model_effect_unverified|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|2529|2529|100.0%|
|temperature.gpu [C]|2529|2529|100.0%|
|temperature.soc012 [C]|2529|2529|100.0%|
|temperature.soc345 [C]|2529|2529|100.0%|
|temperature.tj [C]|2529|2529|100.0%|
|power.vdd_cpu_soc_mss.current [W]|2529|2529|100.0%|
|power.vdd_gpu.current [W]|2529|2529|100.0%|
|power.vin_sys_5v0.current [W]|2529|2529|100.0%|


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
    "ref": "929742d7-6f4d-4d80-b53e-4436d45ac12c/observation:7887",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "929742d7-6f4d-4d80-b53e-4436d45ac12c/observation:7887"
  },
  "counts": {
    "temperature_status_records": 504,
    "valid_temperature_status_records": 503,
    "new_tj_samples": 2529,
    "gpu_usable_new_samples": 2529,
    "planned_origins": 520,
    "eligible_origins": 505,
    "normal_auto_origins": 505,
    "normal_curve_origins": 0
  },
  "control_scopes": {
    "auto": 517,
    "unknown": 3
  },
  "control_ineligible_reasons": {
    "unsupported_control_scope": 3,
    "fan_missing_or_stale": 13,
    "fan_not_enabled": 3,
    "fan_fault": 3,
    "guard_active": 3,
    "control_temperature_stale": 4,
    "successful_duty_unavailable": 3,
    "control_temperature_invalid": 2,
    "active_temperature_source_untrusted": 2
  },
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx_info.temperature.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 36201178,
    "ref": "929742d7-6f4d-4d80-b53e-4436d45ac12c/observation:7875"
  },
  "gpu_source_status_counts": {
    "valid": 2529
  },
  "gpu_unavailable_reasons": {
    "usable": 2529
  },
  "gpu_latest": {
    "value": 0,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 1034.9262639938388,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-a7c66ad2-6dbb-0ab8-c1a2-37ba6dba3600",
    "valid_until": 249508.64987129,
    "contract_valid": true,
    "ref": "929742d7-6f4d-4d80-b53e-4436d45ac12c/observation:7887",
    "observer_receive_mono_s": 249504.684797554,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 1391.5232570143417
  },
  "gpu_coverage": {
    "numerator": 2529,
    "denominator": 2529,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "temperature.gpu [C]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 2529,
      "denominator": 2529,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 2529,
      "denominator": 2529,
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
  "sha256": "a21373c6a232ffdf8b09aec7202c6389e8612b641c1664a1cdc81fad3ab4a756",
  "declared_index_sha256": "a21373c6a232ffdf8b09aec7202c6389e8612b641c1664a1cdc81fad3ab4a756",
  "index_matches": true,
  "records": [
    {
      "record_ref": "operator-records.jsonl:1",
      "raw": {
        "kind": "collection_authorized",
        "source": "human_instruction",
        "verbatim": "那就重新开始采集，本轮设为1小时，旧数据保留，新一轮单独建档。现在是工况1空载待机，风扇仍是TTI智能模式，到期前提醒我，我也可能随时叫停。这个过程中，我会涉及几个工况：1.空载待机，2.模型拉起，3.拉起后（有负载）待机，4.模型单发推理，5.并发推理，6.推理后待机，7.模型kill后空载待机。",
        "recorded_at_utc": "2026-10-13T03:42:36.631824+00:00",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "duration_s": 3600,
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
          },
          {
            "id": 7,
            "label": "模型kill后空载待机"
          }
        ],
        "actual_condition": "空载待机",
        "condition_id": 1,
        "control_mode_operator_label": "TTI智能模式",
        "event_time_precision": "instruction authorizes collection; this is not a reported condition start time"
      }
    },
    {
      "record_ref": "operator-records.jsonl:2",
      "raw": {
        "kind": "collection_started",
        "source": "assistant_observed_collector_manifest",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "collection_started_at_utc": "2026-10-13T03:42:36.009572+00:00",
        "recorded_at_utc": "2026-10-13T03:42:36.631874+00:00",
        "expected_end_at_utc": "2026-10-13T04:42:36.009572+00:00",
        "condition_id": 1
      }
    },
    {
      "record_ref": "operator-records.jsonl:3",
      "raw": {
        "event_id": "round2-condition2-human-start",
        "kind": "condition_started",
        "condition_id": 2,
        "condition_label": "模型拉起",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "source": "human_report",
        "verbatim": "现在开始拉起模型",
        "event_time_utc": null,
        "event_time_precision": "人工上报当前开始；实际启动时刻待操作日志核对，记录时间不是精确启动时间",
        "recorded_at_utc": "2026-10-13T03:46:25.940805+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:4",
      "raw": {
        "event_id": "round2-condition2-human-time-confirmation",
        "kind": "condition_start_time_clarified",
        "condition_id": 2,
        "condition_label": "模型拉起",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "source": "human_report",
        "verbatim": "11:46:24开始的",
        "event_time_local": "2026-10-13T11:46:24+08:00",
        "event_time_utc": "2026-10-13T03:46:24+00:00",
        "precision": "human_report_second_precision_not_yet_log_verified",
        "clarifies_event_id": "round2-condition2-human-start",
        "recorded_at_utc": "2026-10-13T03:47:04.941909+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:5",
      "raw": {
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "source": "human_report",
        "verbatim": "模型已经拉起，现在是有负载待机，时间：11:48:58",
        "event_time_local": "2026-10-13T11:48:58+08:00",
        "event_time_utc": "2026-10-13T03:48:58+00:00",
        "precision": "human_report_second_precision_not_yet_log_verified",
        "recorded_at_utc": "2026-10-13T03:49:39.581336+00:00",
        "event_id": "round2-condition2-human-completed",
        "kind": "condition_completed",
        "condition_id": 2,
        "condition_label": "模型拉起"
      }
    },
    {
      "record_ref": "operator-records.jsonl:6",
      "raw": {
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "source": "human_report",
        "verbatim": "模型已经拉起，现在是有负载待机，时间：11:48:58",
        "event_time_local": "2026-10-13T11:48:58+08:00",
        "event_time_utc": "2026-10-13T03:48:58+00:00",
        "precision": "human_report_second_precision_not_yet_log_verified",
        "recorded_at_utc": "2026-10-13T03:49:39.581336+00:00",
        "event_id": "round2-condition3-human-start",
        "kind": "condition_started",
        "condition_id": 3,
        "condition_label": "拉起后（有负载）待机",
        "details": "模型保持运行，暂不做推理"
      }
    },
    {
      "record_ref": "operator-records.jsonl:7",
      "raw": {
        "event_id": "746fefd9-9a90-490e-8405-c2431d896cd6",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 4,
        "event": "inference_start",
        "event_time_utc": "2026-10-13T03:50:06.612375+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T03:50:06.612490+00:00",
        "evidence_path": "/tmp/tto-round2-single/run.log",
        "details": {
          "concurrency": 1,
          "duration_target_seconds": 600
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T03:50:50.274594+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:8",
      "raw": {
        "event_id": "b61f42a0-3552-4645-b2f6-52426e09efc5",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 4,
        "event": "first_output",
        "event_time_utc": "2026-10-13T03:50:08.295375+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T03:50:08.295452+00:00",
        "evidence_path": "/tmp/tto-round2-single/run.log",
        "details": {
          "request": 1
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T03:50:50.274666+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:9",
      "raw": {
        "event_id": "28f88c0d-c35e-44c8-bd22-da6d345305e5",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 4,
        "event": "inference_end",
        "event_time_utc": "2026-10-13T04:00:06.717543+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:00:06.718083+00:00",
        "evidence_path": "/tmp/tto-round2-single/run.log",
        "details": {
          "started_at": "2026-10-13T03:50:06.612375+00:00",
          "model": "RM-01 VLM",
          "duration_target_seconds": 600,
          "requests": 4,
          "completed": 3,
          "chunks": 4814,
          "characters": 16290,
          "errors": [],
          "last_usage": {
            "prompt_tokens": 61,
            "total_tokens": 2993,
            "completion_tokens": 2932
          },
          "elapsed_seconds": 600.1,
          "ended_at": "2026-10-13T04:00:06.717543+00:00"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:00:49.227388+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:10",
      "raw": {
        "event_id": "1479bce2-3a6d-4d03-bffc-73eac8df0972",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_start",
        "event_time_utc": "2026-10-13T04:02:06.854871+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:02:06.855032+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "concurrency": 4,
          "duration_target_seconds": 600
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:03:16.502395+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:11",
      "raw": {
        "event_id": "aa6ecc72-3277-49f4-a2c0-349723d49d2f",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:02:08.048303+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:02:08.048358+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "worker": 4
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:03:16.502465+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:12",
      "raw": {
        "event_id": "0892fc1f-3d70-4706-94ee-1b6c67bbeb51",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:02:08.666075+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:02:08.666113+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "worker": 2
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:03:16.502513+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:13",
      "raw": {
        "event_id": "22a378d3-43a9-431d-89bc-9eecee633674",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:02:08.666038+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:02:08.666297+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "worker": 1
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:03:16.502560+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:14",
      "raw": {
        "event_id": "1680cb77-33d6-4194-aef0-9b62b0f5132f",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:02:08.666357+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:02:08.666378+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "worker": 3
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:03:16.502598+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:15",
      "raw": {
        "event_id": "5b1590cc-0ae9-4e36-9d1e-427c23d52e6c",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_end",
        "event_time_utc": "2026-10-13T04:12:06.986734+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:06.986776+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": {
          "started_at": "2026-10-13T04:02:06.854871+00:00",
          "model": "RM-01 VLM",
          "concurrency": 4,
          "duration_target_seconds": 600,
          "workers": {
            "1": {
              "requests": 3,
              "completed": 2,
              "characters": 14636,
              "chunks": 4184,
              "errors": [],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 3853,
                "completion_tokens": 3802
              }
            },
            "2": {
              "requests": 4,
              "completed": 3,
              "characters": 13921,
              "chunks": 4180,
              "errors": [],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 1382,
                "completion_tokens": 1331
              }
            },
            "3": {
              "requests": 4,
              "completed": 3,
              "characters": 14932,
              "chunks": 4181,
              "errors": [],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 2500,
                "completion_tokens": 2449
              }
            },
            "4": {
              "requests": 4,
              "completed": 3,
              "characters": 14149,
              "chunks": 4181,
              "errors": [],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 2693,
                "completion_tokens": 2642
              }
            }
          },
          "elapsed_seconds": 600.13,
          "ended_at": "2026-10-13T04:12:06.986734+00:00"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:12:53.370275+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:16",
      "raw": {
        "event_id": "round2-condition6-after-concurrent-end",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 6,
        "event": "condition_started",
        "event_time_utc": "2026-10-13T04:12:06.986734+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:06.986776+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent4/run.log",
        "details": "并发负载程序结束后进入推理后待机；此时刻是客户端负载结束，不声称GPU最后一次执行的精确时刻",
        "source": "derived_from_client_load_end_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:12:53.370275+00:00",
        "derived_from_event_id": "5b1590cc-0ae9-4e36-9d1e-427c23d52e6c"
      }
    },
    {
      "record_ref": "operator-records.jsonl:17",
      "raw": {
        "event_id": "7e9243e1-9bcd-42e1-8f30-244ab80ed997",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_start",
        "event_time_utc": "2026-10-13T04:12:56.845267+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:56.845398+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "concurrency": 16,
          "duration_target_seconds": 300
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:13:56.967892+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:18",
      "raw": {
        "event_id": "81f772e5-51fa-4ac7-b1f8-a97ac1c71487",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:12:57.407880+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:57.407914+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 9
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:13:56.967976+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:19",
      "raw": {
        "event_id": "920c7b1a-1691-47a3-ae38-447d7cf1b423",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:12:57.584089+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:57.584118+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 7
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:13:56.968025+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:20",
      "raw": {
        "event_id": "325c2e15-f28e-47fd-9995-dd0ede485494",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:12:57.584198+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:57.584210+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 11
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:13:56.968072+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:21",
      "raw": {
        "event_id": "58f73f71-c856-4fe9-9587-be36ce8a2b35",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:12:57.584230+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:12:57.584241+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 6
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:13:56.968110+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:22",
      "raw": {
        "event_id": "a99ad3a0-e495-46bd-8922-a8a7944dc51c",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:15:11.608520+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:15:11.608815+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 1
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:16:14.200227+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:23",
      "raw": {
        "event_id": "a6c64e57-7efa-4ab8-ba53-2fca36267b23",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:15:47.692941+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:15:47.693033+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 3
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:16:14.200295+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:24",
      "raw": {
        "event_id": "f86ec9bf-8b3f-4c11-9340-b56229950b20",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:16:07.419611+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:16:07.419906+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 14
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:16:14.200343+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:25",
      "raw": {
        "event_id": "7eeee78e-c65d-4476-a83d-ca6a45042b75",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:16:32.997952+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:16:32.998108+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 2
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:17:16.147816+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:26",
      "raw": {
        "event_id": "6352856e-dd71-4233-8af3-75758c63e296",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "first_output",
        "event_time_utc": "2026-10-13T04:17:44.055101+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:44.055206+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 16
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679018+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:27",
      "raw": {
        "event_id": "488caf09-e0f9-49f2-9ba4-435ea0ed1c77",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.865569+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.865682+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 1,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679086+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:28",
      "raw": {
        "event_id": "4cca27ea-9251-40de-b5d0-f08282a00c10",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.866807+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.866861+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 6,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679135+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:29",
      "raw": {
        "event_id": "4b0b597b-c902-47b6-b920-8c7f11796e19",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.867314+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.867353+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 9,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679175+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:30",
      "raw": {
        "event_id": "4d8e4d48-28e6-435a-baf3-95d7bd939e0a",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.869151+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.869201+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 7,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679210+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:31",
      "raw": {
        "event_id": "e8eca4bc-0328-4add-a35c-7af8344c349b",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.874504+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.874555+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 11,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679250+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:32",
      "raw": {
        "event_id": "dcac3969-1942-48af-8289-92e766647b1f",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.939573+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.939632+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 15,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679283+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:33",
      "raw": {
        "event_id": "0f591480-c9e8-4e06-9590-92bc8b328238",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.947694+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.947793+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 13,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679313+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:34",
      "raw": {
        "event_id": "ea144355-5af9-4c6e-8f98-9b7dbbf00d0a",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.954516+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.954634+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 12,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679347+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:35",
      "raw": {
        "event_id": "b235d8f4-08ed-4683-a935-b39b22d94a4b",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.955430+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.955470+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 10,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679377+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:36",
      "raw": {
        "event_id": "6176b65a-8ce9-49fc-b8a1-fac765c01c7b",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.955630+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.955659+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 8,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679411+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:37",
      "raw": {
        "event_id": "f2a09d0c-f707-4645-8fff-4bd4c69e00d6",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.957719+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.957739+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 4,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679440+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:38",
      "raw": {
        "event_id": "60ece857-4ee5-4b6d-b8aa-51625db42a84",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_error",
        "event_time_utc": "2026-10-13T04:17:56.958022+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.958035+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "worker": 5,
          "error": "timed out"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679475+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:39",
      "raw": {
        "event_id": "666f0a93-c9ba-4828-9fb8-c7ccd7bd4374",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 5,
        "event": "inference_end",
        "event_time_utc": "2026-10-13T04:17:56.958847+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.958869+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": {
          "started_at": "2026-10-13T04:12:56.845267+00:00",
          "model": "RM-01 VLM",
          "concurrency": 16,
          "duration_target_seconds": 300,
          "workers": {
            "1": {
              "requests": 2,
              "completed": 1,
              "characters": 3560,
              "chunks": 1067,
              "errors": [
                "timed out"
              ],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 2153,
                "completion_tokens": 2102
              }
            },
            "2": {
              "requests": 1,
              "completed": 0,
              "characters": 2004,
              "chunks": 596,
              "errors": []
            },
            "3": {
              "requests": 1,
              "completed": 0,
              "characters": 2932,
              "chunks": 914,
              "errors": []
            },
            "4": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "5": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "6": {
              "requests": 2,
              "completed": 1,
              "characters": 3996,
              "chunks": 1197,
              "errors": [
                "timed out"
              ],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 2469,
                "completion_tokens": 2418
              }
            },
            "7": {
              "requests": 2,
              "completed": 1,
              "characters": 3057,
              "chunks": 950,
              "errors": [
                "timed out"
              ],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 1919,
                "completion_tokens": 1868
              }
            },
            "8": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "9": {
              "requests": 2,
              "completed": 1,
              "characters": 5249,
              "chunks": 1517,
              "errors": [
                "timed out"
              ],
              "last_usage": {
                "prompt_tokens": 51,
                "total_tokens": 3172,
                "completion_tokens": 3121
              }
            },
            "10": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "11": {
              "requests": 2,
              "completed": 1,
              "characters": 4641,
              "chunks": 1334,
              "errors": [
                "timed out"
              ],
              "last_usage": {
                "prompt_tokens": 52,
                "total_tokens": 2800,
                "completion_tokens": 2748
              }
            },
            "12": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "13": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "14": {
              "requests": 1,
              "completed": 0,
              "characters": 2443,
              "chunks": 777,
              "errors": []
            },
            "15": {
              "requests": 1,
              "completed": 0,
              "characters": 0,
              "chunks": 0,
              "errors": [
                "timed out"
              ]
            },
            "16": {
              "requests": 1,
              "completed": 0,
              "characters": 267,
              "chunks": 91,
              "errors": []
            }
          },
          "elapsed_seconds": 300.1,
          "ended_at": "2026-10-13T04:17:56.958847+00:00"
        },
        "source": "operations_thread_actual_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679557+00:00"
      }
    },
    {
      "record_ref": "operator-records.jsonl:40",
      "raw": {
        "event_id": "round2-condition6-after-concurrent16-end",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "condition_id": 6,
        "event": "condition_started",
        "event_time_utc": "2026-10-13T04:17:56.958847+00:00",
        "precision": "milliseconds",
        "recorded_at_utc": "2026-10-13T04:17:56.958869+00:00",
        "evidence_path": "/tmp/tto-round2-concurrent16/run.log",
        "details": "16路请求负载程序到期退出后待机；保留客户端超时事件，不能将所有请求记为正常完成；此时刻不是GPU执行精确结束时刻",
        "source": "derived_from_client_load_end_log",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "synced_at_utc": "2026-10-13T04:18:49.679557+00:00",
        "derived_from_event_id": "666f0a93-c9ba-4828-9fb8-c7ccd7bd4374"
      }
    },
    {
      "record_ref": "operator-records.jsonl:41",
      "raw": {
        "event_id": "round2-condition6-human-resident-clarification",
        "kind": "condition_semantics_clarified",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "condition_id": 6,
        "source": "human_report",
        "verbatim": "模型推理完了，从结束开始，你现在记录的都是有负载（模型拉起）的待机温度",
        "condition_label": "推理后模型驻留待机",
        "effective_since_event_time_utc": "2026-10-13T04:17:56.958847+00:00",
        "recorded_at_utc": "2026-10-13T04:20:09.331836+00:00",
        "details": "模型仍保持运行，没有推理请求；尚未进入模型kill后的工况7"
      }
    },
    {
      "record_ref": "operator-records.jsonl:42",
      "raw": {
        "event_id": "round2-condition7-human-start",
        "kind": "condition_started",
        "condition_id": 7,
        "condition_label": "模型kill后空载待机",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c",
        "source": "human_report",
        "verbatim": "现在把模型kill掉了，进入工况7空载待机，记一下时间，继续采集温度回落。",
        "event_time_utc": null,
        "precision": "人工上报已经完成并进入；实际kill时刻待日志核对，记录时间不能代替精确操作时间",
        "recorded_at_utc": "2026-10-13T04:22:21.733636+00:00",
        "recorded_at_local": "2026-10-13T12:22:21.733636+08:00",
        "details": "已卸载模型，空载待机并继续采集温度回落；不停止TTO"
      }
    },
    {
      "record_ref": "operator-records.jsonl:43",
      "raw": {
        "event_id": "round2-human-stop-request",
        "kind": "collection_stop_requested",
        "source": "human_instruction",
        "verbatim": "现在停止采集，保存好本轮数据和操作记录，然后分析各个工况的温度、功耗、GPU利用率和风扇变化",
        "recorded_at_utc": "2026-10-13T04:24:52.365366+00:00",
        "episode": "rm01-seven-conditions-1h-20261013-034232",
        "observer_run_id": "929742d7-6f4d-4d80-b53e-4436d45ac12c"
      }
    }
  ],
  "issues": [],
  "note": "保留关联人工原文、来源、近似事件时刻与写入时刻；任务结束不代表回落采集应停止，也不自动授予过程独立性。"
}
```
本页是采集质量报告；模型价值使用独立的分层时间留出评估报告。
