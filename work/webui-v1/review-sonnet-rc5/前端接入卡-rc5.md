# 模型状态历史：前端接入卡 rc5

后端新增历史接口可接入；本候选首页仍使用封存 rc3 资产。Sonnet 的视觉改版源文件保留，未合入本候选。

## 请求与取值

```text
GET /api/v1/series?ids=temperature.tj,model.Tf_C,model.Ts_C,model.E_C&max_points=2000
```

默认最近 10 分钟；需要完整窗口时使用合法 from/to，最多一小时。出现任一新模型 id 即共同抽样；四列的 t/sample_id 逐行一致。
同请求的 TJ 是模型采样对齐视图；独立请求 temperature.tj 仍是原始 TJ 历史。默认 ids 不变。
bootstrap 的 available_series 列举模型序列，series_capabilities 描述共同抽样能力；available_fields 仍表示当前 metrics。

Tf 为吸收该次 TJ 后的状态估计，不能用预测起点 TJ 替代。TJ−Tf 为校正后残差，既不是 innovation_C，也不是预测误差。
E、Ts−E、Tf−Ts 为带符号温度状态分解；负值原样显示，不截零。Ts 不是结构测温、E 不是室温，三者不是热量占比。
phase_at_sample 区分 tracking/degraded。schema 和三个真实接口形状示例在 src/tto_web/contracts/series*。

## 必须保留的显示语义

1. null 必须断线；关闭 connectNulls，不补零、不插值、不延续末值。三个模型历史共同取点，不再在浏览器分别抽样。
2. max_points 为软预算，全部缺口和分段边界优先保留；检查 soft_budget_exceeded/original_points/returned_points，不截断后半段。
3. 历史保持过去合格值；当前状态过期另按当前快照撤值，不能用历史末值恢复当前卡片或 TTL。
4. 完整身份为 service_epoch/run_id/source_epoch/model_id/spec_id。快照组变化时立即清空历史并递增请求代次；无论旧请求是否占 busy，都要能启动新组请求。
5. HTTP 返回时核对完整身份、请求代次、窗口/ids 和暂停状态；任一不匹配丢弃。切换 epoch 即使 run 相同也必须生效。后端不能撤回在途响应。
6. 若使用增量缓存，仍受 1 小时/18002 行边界约束，缺口不能在合并时丢失。后端每次返回的是请求窗口的选点结果，不是可逐行累加的无损增量日志。

## 验证与边界

tools/history_view.html 与 history_view.js 是合成服务的最小验证页，仅由 tools/history_service.py 挂载，不在产品路由或 wheel 静态目录中。
它验证同采样、null 分段及旧响应隔离。正式首页接入后仍需独立验证图形、DOM/可访问性、切组/暂停/恢复和过期撤值。
既有有限记录 2697/2697 与 51/51 有序不等于普遍保证；测试故意覆盖 Tf<Ts、Ts<E。
不连接真实设备，不改模型、预测算法、建议算法、源采样或 TTL。
