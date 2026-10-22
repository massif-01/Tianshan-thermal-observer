# TTO 模拟评估报告

模拟演示：仅验证软件正确性，不代表实机收益。

每层内部使用相同起点、相同标签；不同层MAE不能直接比较模型优劣。M1缺项不阻挡M0层。

接收时间近似，不是硬件采样时刻；未测网络延迟不解释为热滞后。

## 基线层 B0/B1

基线层使用B0/B1共同起点；只在本层内比较。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|288|278|96.5%|0.5555|0.9561|1.0777|
|15|trend30|288|278|96.5%|0.2244|0.4458|0.5309|
|45|persist|288|266|92.4%|1.6286|2.6704|2.9566|
|45|trend30|288|266|92.4%|0.9046|1.7592|2.0742|
|90|persist|288|248|86.1%|3.0913|5.0721|5.2342|
|90|trend30|288|248|86.1%|2.3945|3.9899|4.7823|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|simulation-process-3|persist|144|133|1.6409|
|simulation-process-3|trend30|144|133|0.9023|
|simulation-process-4|persist|144|133|1.6163|
|simulation-process-4|trend30|144|133|0.9070|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|19|1.1314|
|stable|trend30|19|1.1576|
|warming|persist|55|1.3144|
|warming|trend30|55|0.9093|
|cooling|persist|91|1.7898|
|cooling|trend30|91|0.8499|
|rewarming|persist|101|1.7480|
|rewarming|trend30|101|0.9038|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|

## M0层 B0/B1/M0

模拟演示：本层只验证计算，真实价值待数据。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|288|210|72.9%|0.5866|0.9746|1.0777|
|15|trend30|288|210|72.9%|0.2223|0.4730|0.5309|
|15|ridge_tj|288|210|72.9%|0.0586|0.0681|0.0693|
|45|persist|288|198|68.8%|1.7294|2.7343|2.9566|
|45|trend30|288|198|68.8%|0.8745|1.8250|2.0742|
|45|ridge_tj|288|198|68.8%|0.2930|0.3299|0.3348|
|90|persist|288|180|62.5%|3.3405|5.1381|5.2342|
|90|trend30|288|180|62.5%|2.1848|4.2857|4.7823|
|90|ridge_tj|288|180|62.5%|0.4276|0.4635|0.4685|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|simulation-process-3|persist|144|99|1.7276|
|simulation-process-3|trend30|144|99|0.8715|
|simulation-process-3|ridge_tj|144|99|0.2438|
|simulation-process-4|persist|144|99|1.7312|
|simulation-process-4|trend30|144|99|0.8776|
|simulation-process-4|ridge_tj|144|99|0.3423|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|10|1.1368|
|stable|trend30|10|1.0815|
|stable|ridge_tj|10|0.2728|
|warming|persist|0|未覆盖|
|warming|trend30|0|未覆盖|
|warming|ridge_tj|0|未覆盖|
|cooling|persist|87|1.7759|
|cooling|trend30|87|0.8167|
|cooling|ridge_tj|87|0.2953|
|rewarming|persist|101|1.7480|
|rewarming|trend30|101|0.9038|
|rewarming|ridge_tj|101|0.2931|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|
|higher_temperature|ridge_tj|0|未覆盖|

## M1层 B0/B1/M0/M1

模拟演示：本层只验证计算，真实价值待数据。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|15|trend30|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|15|ridge_tj|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|15|ridge_full|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|45|persist|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|45|trend30|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|45|ridge_tj|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|45|ridge_full|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|90|persist|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|90|trend30|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|90|ridge_tj|288|0|0.0%|未覆盖|未覆盖|未覆盖|
|90|ridge_full|288|0|0.0%|未覆盖|未覆盖|未覆盖|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|simulation-process-3|persist|144|0|未覆盖|
|simulation-process-3|trend30|144|0|未覆盖|
|simulation-process-3|ridge_tj|144|0|未覆盖|
|simulation-process-3|ridge_full|144|0|未覆盖|
|simulation-process-4|persist|144|0|未覆盖|
|simulation-process-4|trend30|144|0|未覆盖|
|simulation-process-4|ridge_tj|144|0|未覆盖|
|simulation-process-4|ridge_full|144|0|未覆盖|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|0|未覆盖|
|stable|trend30|0|未覆盖|
|stable|ridge_tj|0|未覆盖|
|stable|ridge_full|0|未覆盖|
|warming|persist|0|未覆盖|
|warming|trend30|0|未覆盖|
|warming|ridge_tj|0|未覆盖|
|warming|ridge_full|0|未覆盖|
|cooling|persist|0|未覆盖|
|cooling|trend30|0|未覆盖|
|cooling|ridge_tj|0|未覆盖|
|cooling|ridge_full|0|未覆盖|
|rewarming|persist|0|未覆盖|
|rewarming|trend30|0|未覆盖|
|rewarming|ridge_tj|0|未覆盖|
|rewarming|ridge_full|0|未覆盖|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|
|higher_temperature|ridge_tj|0|未覆盖|
|higher_temperature|ridge_full|0|未覆盖|

每层的过程/阶段明细、全量方法覆盖与不可用原因见evaluation.json；逐次原始引用见predictions.jsonl。固件趋势仅作诊断。相邻行不是独立实验，没有置信百分比或调速结论。
