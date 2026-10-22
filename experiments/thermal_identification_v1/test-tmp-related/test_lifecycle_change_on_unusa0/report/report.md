# TTO 模拟旁路运行报告

模拟旁路：本次只有基线，尚无可用模型输出；已保存基线评分。 历史评分中354条因质量隔离排除，当前258条有效；误差和图只使用有效集合。 模拟记录仅验证软件，真实预测效果待数据。 本轮存在不兼容输入合同或控制范围，正式建库拒绝；历史已发记录和恢复段有效评分仍保留。

下一步：保留本轮合同变化、隔离及恢复证据；不将混合run直接冻结为正式数据集。

接收时间近似；源年龄是下界，不含未测网络在途时间。

## 采集质量

|项目|结果|
|---|---|
|连接|仅模拟，未连接设备|
|部署核对|现场部署未核对|
|有效新测量|619|
|重复缓存|0|
|正常AUTO起点|0|
|正常CURVE起点|124|
|合格且平台已确认起点|124|
|GPU有效新样本/新TJ样本|619/619|

## 输入与控制资格

具名字段覆盖不等于平台已确认；配置绑定不等于实际来源生效；收到TJ不等于建模准备完成。此诊断未计算或替换历史预测/评分。

|检查|结果|
|---|---|
|计算模块声明|jetson_thor / confirmed|
|实际模式/计划起点|curve: 124|
|GPU来源封存状态|valid|
|观察器当前GPU有效|是|
|源周期ms / 依据|1000 / wire_telemetry_meta|
|有效控制温度状态/收到状态|124/124|
|配置温度来源 / 实际温度来源|variable / variable|
|配置绑定|agx.tj|
|控制资格缺项|控制条件已观察到；仍需冻结模型与完整过程证据|
|建模准备|blocked_by_mixed_profiles|
|完整过程证据|仍需任务起止、回落与过程分组|


## 原始具名输入覆盖

|实际字段/单位|有效新样本|新TJ样本|覆盖率|
|---|---|---|---|
|temperature.cpu [C]|619|619|100.0%|
|temperature.soc012 [C]|619|619|100.0%|
|temperature.soc345 [C]|619|619|100.0%|
|temperature.tj [C]|619|619|100.0%|
|power.vdd_cpu_soc_mss.current [W]|619|619|100.0%|
|power.vdd_gpu.current [W]|619|619|100.0%|
|power.vin_sys_5v0.current [W]|619|619|100.0%|


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
    "ref": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60/observation:1364",
    "evidence_status": "confirmed"
  },
  "source_period_evidence": {
    "period_ms": 1000,
    "basis": "wire_telemetry_meta",
    "reason": null,
    "ref": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60/observation:1364"
  },
  "counts": {
    "temperature_status_records": 124,
    "valid_temperature_status_records": 124,
    "new_tj_samples": 619,
    "gpu_usable_new_samples": 619,
    "planned_origins": 124,
    "eligible_origins": 124,
    "normal_auto_origins": 0,
    "normal_curve_origins": 124
  },
  "control_scopes": {
    "curve": 124
  },
  "control_ineligible_reasons": {},
  "last_temperature_binding": {
    "preferred_source": "variable",
    "active_source": "variable",
    "bound_variable": "agx.tj",
    "manual_mode": false,
    "normalized_valid": true,
    "timestamp_ms": 1200,
    "ref": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60/observation:1355"
  },
  "gpu_source_status_counts": {
    "valid": 619
  },
  "gpu_unavailable_reasons": {
    "usable": 619
  },
  "gpu_latest": {
    "value": 50.38306047704776,
    "reason": null,
    "source_status": "valid",
    "age_lower_bound_ms": 0,
    "timeout_ms": 5000,
    "sample_interval_ms": 1000,
    "device_uuid": "GPU-SIMULATION",
    "valid_until": 624.0,
    "contract_valid": true,
    "ref": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60/observation:1364",
    "observer_receive_mono_s": 619.0,
    "observer_current_valid": true,
    "observer_current_age_lower_bound_ms": 0.0
  },
  "gpu_coverage": {
    "numerator": 619,
    "denominator": 619,
    "fraction": 1.0
  },
  "named_input_coverage": {
    "temperature.cpu [C]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "temperature.soc012 [C]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "temperature.soc345 [C]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "temperature.tj [C]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "power.vdd_cpu_soc_mss.current [W]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "power.vdd_gpu.current [W]": {
      "numerator": 619,
      "denominator": 619,
      "fraction": 1.0
    },
    "power.vin_sys_5v0.current [W]": {
      "numerator": 619,
      "denominator": 619,
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
## 当时实际发出的预测与评分

数值来自本run的predictions.jsonl与scores.jsonl，按预测身份/时距/方法/模型关联；未加载当前模型重算。每方法覆盖单列，不拿不同集合的MAE判断优劣。有效评分使用生产质量回放的既有段隔离；覆盖率分子为当前有效评分，分母为当时计划起点（包含隔离段），已发预测分母另见JSON。

|当时模型SHA/基线|时距s|实际输出方法|计划起点|已发|历史评分|质量排除|输入证据排除|当前有效|有效/计划起点|MAE C|RMSE C|绝对误差P95 C|偏差 C|欠预测P95 C|欠预测最大 C|过预测P95 C|过预测最大 C|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|无模型基线|15|persist|124|124|118|67|0|51|41.1%|0.5722|0.6307|1.0547|-0.2841|1.0547|1.0969|0.6172|0.8961|
|无模型基线|15|trend30|124|120|114|65|0|49|39.5%|0.2330|0.2806|0.4987|-0.1449|0.4987|0.5441|0.2608|0.3051|
|无模型基线|45|persist|124|124|106|61|0|45|36.3%|1.6200|1.8043|2.9503|-0.9627|2.9503|3.0059|1.3068|1.7698|
|无模型基线|45|trend30|124|120|102|59|0|43|34.7%|0.9614|1.1320|2.0176|-0.8170|2.0176|2.1292|0.7050|0.9746|
|无模型基线|90|persist|124|124|88|52|0|36|29.0%|2.7934|3.2531|5.0445|-2.0593|5.0445|5.1525|2.2122|2.7613|
|无模型基线|90|trend30|124|120|84|50|0|34|27.4%|3.0055|3.1514|4.5573|-3.0055|4.5573|4.6634|0.0000|0.0000|

## 历史记录与当前评价资格

```json
{
  "issued_prediction_origins": 124,
  "terminal_score_records": 372,
  "historical_scored_method_horizon_records": 612,
  "scored_method_horizon_records": 258,
  "quality_excluded_method_horizon_records": 354,
  "log_evidence_complete": true,
  "quality_isolations": [
    {
      "run_id": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60",
      "segment": 4,
      "reason": "lifecycle_contract_change",
      "trigger_ref": "0f9af1f7-b858-4cbd-9bfc-fb78292bda60/observation:773"
    }
  ]
}
```
## 实际方法、降级与未评分原因

```json
{
  "baseline_no_model": {
    "model_sha256": null,
    "actual_methods": {
      "persist": 4,
      "trend30": 120
    },
    "fallback_origins": 124,
    "unavailable_method_reasons": {
      "persist": {},
      "trend30": {
        "warming_up_10s": 4
      },
      "ridge_tj": {
        "model_not_loaded": 124
      },
      "ridge_full": {
        "model_not_loaded": 124
      }
    },
    "unscored": {
      "15": {
        "cross_segment": 6
      },
      "45": {
        "cross_segment": 18
      },
      "90": {
        "cross_segment": 36
      }
    }
  }
}
```

模型身份及每次预测/评分/原始观测引用见report.json；图按目标时刻对齐。
