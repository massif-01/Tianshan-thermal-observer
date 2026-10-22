# R3b：历史评分与当前评价资格

旁路报告仍读取本run保存的预测与评分，不加载当前模型、不回写观测或日志。质量回放只提供已有的段隔离判定和关联身份，不提供替代预测值或误差。

`dataset.replay`将Engine已有的`invalidated_segment`传为`quality_eligibility`，含run、segment、原因和触发观测引用。报告按预测ID、run、segment、起点原始引用/支持引用及每时距标签引用关联回放；评分仍先经过原有预测ID、时距、方法、模型身份和保存误差一致性检查。无法关联的记录明确列入issues，不能通过修改segment或引用绕过隔离。日志行号只用于定位证据。

`recorded_results`中的`terminal_score_records`是日志里当时保存的全部终结记录（含未评分状态）；`historical_scored_method_horizon_records`是成功关联的历史方法×起点×时距评分。`scored_method_horizon_records`与`scored_records`只含当前有效成绩；`quality_excluded_method_horizon_records`与`quality_excluded_records`保留被已有质量规则排除的历史评分、原值、方法、模型身份和原始引用。每条排除记录的`quality_exclusion`包含原因及触发引用。

各模型、时距、方法分别提供historical_scored、quality_excluded、scored和quality_exclusion_reasons。MAE、RMSE、绝对误差P95、偏差、欠/过预测与图全部使用scored_records。无有效成绩时不报告零误差。

覆盖率`coverage_fraction = coverage_numerator / coverage_denominator = 当前有效评分 / 当时计划起点`；计划分母为该模型组当时保存的全部预测起点，每时距各计一次，包含后来被隔离的段。`score_fraction_of_issued = 当前有效评分 / 当时该方法已发预测`，分母由score_fraction_denominator明确列出。方法未输出、原有未评分/跨段和降级信息保留。日志缺失时成绩与覆盖记未知，不填零；日志齐全且出现隔离时，日志完整性仍与评分资格分开。

隔离规则、粒度、预热与恢复全部沿用现有Engine/Quality。旧隔离段退出统计，后续恢复段继续计分，不因单次冲突清空整轮。不更改特征、模型参数、新鲜度、源频率或控制行为。

所有报告写入新路径；旧报告不会自动更新，不能继续引用旧报告的有效统计。JSON、Markdown、HTML使用同一结果对象，HTML图只用当前有效集合。模拟记录仅用于离线软件验证。
