# I-02 局部修正交付

仅执行复审03。**断连后旧TJ/功率保留作追溯，但不再标为当前有效；重连信号或旧缓存不能自行恢复，须重新接纳合法新源记录。** 不涉及HTTP超时根因，不改变collector诊断补丁、TTL、模型、风扇或保护。没有设备连接、部署或真实请求。

## 接入内容

- `output/source-health-Y-I02.jsonl`：完整Y派生修订，5319行。请用新身份 `COMM-SOURCE-HEALTH-R2-I02-v1` 识别，原接口身份不覆盖。
- `scripts/source_health.py`：修订导出脚本，支持 `export_records(manifest, records)`，或下面显式输入/输出CLI。`runtime/tto` 是原0.2.4只读引擎依赖，未改collector/quality/TTL。
- `deliverables/I-02-source-health.patch`：相对原 `scripts/source_health.py` 的补丁；`baseline/source_health.py` 是精确旧脚本。patch与完整脚本选一种接入，不重复应用。
- `output/verification.json`、`output/tests.log`：逐项核验与6项小测试。
- `output/Y-disconnect-before-after.json`：实际Y最后一条的前后对照。
- `inputs/03-给通讯专项的局部修正.md` 与provenance：任务与原件身份。

原ZIP、原source-health输出、原collector诊断补丁均未覆盖。此包只含局部派生交付，不包含完整历史原件；`inputs/Y-tail.jsonl`是原Y尾部4条摘录，另有一个源测试样本。历史数值/引用/时刻/原到期值全部保留，不重打时间戳，不插值，不续龄。消费者必须按 `raw_valid` 判断当前可用性，不能因 `source.values` 仍有数字就继续使用。

## I-02原因与修改

原导出层只检查旧质量key、TTL、blocked/quarantined；原引擎发生boundary时旧key可能保留。因此在socketio_disconnected之后，之前的key仍匹配且未过TTL，错误输出raw_valid=true。

现加入导出层source_usable状态：源生命周期边界和明确队列缺口使其失效；断连/连接失败后要求经过重连阶段，再由原引擎接受的新合法源恢复。socketio_connecting本身不使旧值有效；重复缓存不会被当作新源。断连后的晚到回调也不恢复当前有效性。正常序列与原TTL判断不变。

## 逐项差异（完整Y重放）

| 项目 | 修前 | 修后 | 范围 |
|---|---|---|---|
| identity.spec | COMM-SOURCE-HEALTH-R2-v1 | COMM-SOURCE-HEALTH-R2-I02-v1 | 5319行仅标新接口身份 |
| observation:5319 的 measurement.TJ_and_rails.raw_valid | true | false | 唯一数据语义变化 |
| 5319里保留的source.ref | observation:5316 | observation:5316 | 不变 |
| 历史TJ/rail数值、key、来源、时刻、valid_until | 原值 | 原值 | 不变 |
| 所有PWM、安全、observer、permission字段 | 原值 | 原值 | 不变 |

原Y末条为socketio_disconnected。逐字段核验确认：除接口身份外，完整输出只有上述一个raw_valid变化。

## 验证

本地标准库测试6项全部通过：正常连续源、断连立即失效且保留历史、旧缓存在重连前/重连阶段不恢复、新合法源恢复、重连前晚到回调不得恢复、无效新源不能恢复且TTL仍到期。修订脚本语法检查和对精确旧脚本的patch应用检查通过。

```sh
python3 tests/test_lifecycle.py
python3 scripts/source_health.py --run-dir /path/to/original/Y-run --output /path/to/NEW-output.jsonl
# 验证与原完整输出的差异；需原完整输出（不在小包内）
python3 scripts/verify_revision.py --original /path/to/original/source-health-Y.jsonl
```

CLI的output使用独占创建，不会覆盖已有输出。测试只用保存输入和内存事件，不发网络请求。原生产问题的现场状态未因此获得验证，也不许可恢复负载或部署。
