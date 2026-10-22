# 模型状态历史增量合同（TTO-WEB-SERIES-v1）

新序列：model.Tf_C / model.Ts_C / model.E_C，单位 °C、kind=estimate、estimate_stage=posterior。
它们来自既有冻结观察器吸收该次新 TJ 后的状态，不是未来预测，也不是传感器测温。
TJ−Tf 为校正后残差；E、Ts−E、Tf−Ts 为带符号温度状态分解，不能解释为热量占比。

显式请求任一新模型 id，启用 tj_model 共同抽样；同请求中的 temperature.tj 为模型采样锚点视图。
独立 temperature.tj 与默认 ids 保持原指标历史。没有插值、补零或平滑。三个模型状态始终共同取点，
并保留 TJ、Tf、Ts、E 和三种差值的桶内极值、全部显式缺口及相邻段边界；只请求部分模型时索引仍一致。
max_points 是软预算，断点密集时可超额；original_points/returned_points/soft_budget_exceeded 明示实际情况。
每个联合组最多 18002 行，按既有时间裁剪一小时；高于容量的源速率可能不足一小时。

数值资格：新且未重复的 TJ、TJ 有效且未到期、tracking/degraded、三个有限状态、
now < min(consumable_until_mono_s,TJ._expiry)。t=TJ.as_of_elapsed_ms，且与包 input-origin 的毫秒值相差不超过 0.001ms，
此容差只吸收浮点运算误差。sample_id/source_ref/received_at_utc 关联 TJ 锚点；phase_at_sample 保留 degraded。

缺口理由：source_disconnected/source_ended/publication_gap/model_expired/tj_invalid/phase_unavailable/
nonfinite_state/alignment_mismatch。显式缺口四列均 null，status=unknown；过去合格历史不会因当前过期而撤销。
连续失效区间合并断点。断连、显示发布失败用检测时间；过期用原截止时间；阶段失效用包输入时间。
断点时间不早于最后已记录行，同位置缺口优先。断点之后到达且源时刻不晚于断点的样本不回填，
不额外累积日志、点或仅供测试读取的处置状态。只在更新且时间晚于断点的合格 TJ 恢复。

完整响应身份：service_epoch/run_id/source_epoch/model_id/spec_id。run/epoch/model/spec 变化清空历史及去重，
Web 重启产生新 service_epoch。model/spec 冻结校验不放宽。一个 HTTP 响应内身份与数据同时生成。
客户端必须在组切换时清空历史、递增请求代次；响应到达时核对完整身份、代次、查询窗口和暂停状态。
旧响应即使同 run、同参数也不能回填。缺口使用 null 且绘图库须关闭跨空值连线。

bootstrap 新增 series_capabilities 与 available_series；available_fields 仍表示当前 metrics。
series.schema.json 限制新增字段/枚举；三个 series-example JSON 分别演示正常、缺口和同 run 新 epoch。
