# A/B资格与下一轮准备研究

规则 `TTO-EVAL-AVAIL-v2.0`。生产 `quality/engine/evaluate/report` 合同保持原样；本目录从原始事件分别追踪温度源身份/隔离与辅助可见性，不靠旧综合segment直接决定B答案。

每个时距分别记录：可信同源TJ答案、当时各方法输入/历史资格、未来功率/成功PWM输入完整性、控制上下文正常/辅助缺口/明确异常或改变/不可分辨。A必须完整未来输入，B只给已经保存且起点合法的值评分；缺失预测不补发。当前PWM或60秒历史缺少时G1/G2/R_IO仍不合格；B0/B1/R_TJ按自身输入资格列出。未知控制状态不写正常，源冲突/隔离/身份边界不恢复温度答案。

覆盖核对读取冻结的F-LS/F-SL/F-POOL预测；它们是之前离线回放生成的预测，不能称原现场已发。所有预测数值、模型参数、旧scores/strict合同不变。共同比较按起点/时距/答案引用计算集合ID，正常、辅助缺口、异常和全部可信答案分别列出。扩大覆盖不是算法变准，合并资料仍为开发数据。

从本轮证据包取得同层级的 `handoff/`、`frozen-greybox/` 之后可独立复核；大型ZIP不在本地代码分支重复存放。以下仅重建资格/诊断，不拟合：

```sh
python experiments/thermal_identification_prep_v2/coverage_audit.py --handoff /path/to/handoff --frozen /path/to/frozen-greybox --output /path/to/new-availability-v2
python -m pytest -q experiments/thermal_identification_prep_v2/tests
```

温度描述参考用提交前30秒真实TJ中位数，历史须有至少20点且跨度25秒；不是热平衡。事件峰值/模型峰值用相同有效引用集合；温升面积单位°C·s，不是热量。事件窗口保留原始时钟、PWM/输入覆盖、与前负载重叠标记。新结果和图表由同一JSON生成。
