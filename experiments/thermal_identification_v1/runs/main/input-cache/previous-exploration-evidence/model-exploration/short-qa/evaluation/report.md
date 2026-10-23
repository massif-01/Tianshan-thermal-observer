# TTO 时间隔离评估报告

基线层已有可读结果；证据不足：最终部署身份未核对。 证据不足：最终部署身份未核对。

每层内部使用相同起点、相同标签；不同层MAE不能直接比较模型优劣。M1缺项不阻挡M0层。

接收时间近似，不是硬件采样时刻；未测网络延迟不解释为热滞后。

## 基线层 B0/B1

基线层使用B0/B1共同起点；只在本层内比较。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|29|26|89.7%|0.0457|0.0940|0.1250|
|15|trend30|29|26|89.7%|0.0613|0.1048|0.1576|
|45|persist|29|20|69.0%|0.0891|0.1886|0.2190|
|45|trend30|29|20|69.0%|0.1166|0.2742|0.3808|
|90|persist|29|11|37.9%|0.1649|0.2660|0.2820|
|90|trend30|29|11|37.9%|0.2063|0.4945|0.6056|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|tto-short-qa-v1-20261013-052807|persist|29|20|0.0891|
|tto-short-qa-v1-20261013-052807|trend30|29|20|0.1166|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|19|0.0888|
|stable|trend30|19|0.1124|
|warming|persist|0|未覆盖|
|warming|trend30|0|未覆盖|
|cooling|persist|0|未覆盖|
|cooling|trend30|0|未覆盖|
|rewarming|persist|1|0.0940|
|rewarming|trend30|1|0.1959|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|

## M0层 B0/B1/M0

证据不足：最终部署身份未核对。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|29|26|89.7%|0.0457|0.0940|0.1250|
|15|trend30|29|26|89.7%|0.0613|0.1048|0.1576|
|15|ridge_tj|29|26|89.7%|0.3065|0.3806|0.3919|
|45|persist|29|20|69.0%|0.0891|0.1886|0.2190|
|45|trend30|29|20|69.0%|0.1166|0.2742|0.3808|
|45|ridge_tj|29|20|69.0%|0.5057|0.5798|0.5945|
|90|persist|29|11|37.9%|0.1649|0.2660|0.2820|
|90|trend30|29|11|37.9%|0.2063|0.4945|0.6056|
|90|ridge_tj|29|11|37.9%|0.5520|0.6401|0.6438|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|tto-short-qa-v1-20261013-052807|persist|29|20|0.0891|
|tto-short-qa-v1-20261013-052807|trend30|29|20|0.1166|
|tto-short-qa-v1-20261013-052807|ridge_tj|29|20|0.5057|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|19|0.0888|
|stable|trend30|19|0.1124|
|stable|ridge_tj|19|0.5010|
|warming|persist|0|未覆盖|
|warming|trend30|0|未覆盖|
|warming|ridge_tj|0|未覆盖|
|cooling|persist|0|未覆盖|
|cooling|trend30|0|未覆盖|
|cooling|ridge_tj|0|未覆盖|
|rewarming|persist|1|0.0940|
|rewarming|trend30|1|0.1959|
|rewarming|ridge_tj|1|0.5945|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|
|higher_temperature|ridge_tj|0|未覆盖|

## M1层 B0/B1/M0/M1

证据不足：最终部署身份未核对。

|时距s|方法|计划起点|共同评分|覆盖率|episode等权MAE C|欠预测P95 C|欠预测最大宏平均 C|
|---|---|---|---|---|---|---|---|
|15|persist|29|26|89.7%|0.0457|0.0940|0.1250|
|15|trend30|29|26|89.7%|0.0613|0.1048|0.1576|
|15|ridge_tj|29|26|89.7%|0.3065|0.3806|0.3919|
|15|ridge_full|29|26|89.7%|0.8315|0.0000|0.0000|
|45|persist|29|20|69.0%|0.0891|0.1886|0.2190|
|45|trend30|29|20|69.0%|0.1166|0.2742|0.3808|
|45|ridge_tj|29|20|69.0%|0.5057|0.5798|0.5945|
|45|ridge_full|29|20|69.0%|0.2309|0.4192|0.4474|
|90|persist|29|11|37.9%|0.1649|0.2660|0.2820|
|90|trend30|29|11|37.9%|0.2063|0.4945|0.6056|
|90|ridge_tj|29|11|37.9%|0.5520|0.6401|0.6438|
|90|ridge_full|29|11|37.9%|0.7522|0.8977|0.9193|

### 45秒：各过程

|过程|方法|计划|共同评分|MAE C|
|---|---|---|---|---|
|tto-short-qa-v1-20261013-052807|persist|29|20|0.0891|
|tto-short-qa-v1-20261013-052807|trend30|29|20|0.1166|
|tto-short-qa-v1-20261013-052807|ridge_tj|29|20|0.5057|
|tto-short-qa-v1-20261013-052807|ridge_full|29|20|0.2309|

### 45秒：各阶段

|阶段|方法|共同评分|MAE C|
|---|---|---|---|
|stable|persist|19|0.0888|
|stable|trend30|19|0.1124|
|stable|ridge_tj|19|0.5010|
|stable|ridge_full|19|0.2331|
|warming|persist|0|未覆盖|
|warming|trend30|0|未覆盖|
|warming|ridge_tj|0|未覆盖|
|warming|ridge_full|0|未覆盖|
|cooling|persist|0|未覆盖|
|cooling|trend30|0|未覆盖|
|cooling|ridge_tj|0|未覆盖|
|cooling|ridge_full|0|未覆盖|
|rewarming|persist|1|0.0940|
|rewarming|trend30|1|0.1959|
|rewarming|ridge_tj|1|0.5945|
|rewarming|ridge_full|1|0.1877|
|higher_temperature|persist|0|未覆盖|
|higher_temperature|trend30|0|未覆盖|
|higher_temperature|ridge_tj|0|未覆盖|
|higher_temperature|ridge_full|0|未覆盖|

每层的过程/阶段明细、全量方法覆盖与不可用原因见evaluation.json；逐次原始引用见predictions.jsonl。固件趋势仅作诊断。相邻行不是独立实验，没有置信百分比或调速结论。
