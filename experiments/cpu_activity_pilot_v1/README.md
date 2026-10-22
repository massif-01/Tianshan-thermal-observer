# TTO CPU activity pilot v1 / 0.2.4+cpu.1

独立离线准备候选。复用closeout.2执行链；不是生产升级，不包含负载许可。详见`docs/一页操作卡.md`及准备报告。

入口：`tto-cpu-pilot preview|verify-install|capability|execute`；源旁录：`tto-cpu-source`或独立运行`src/tto_field/cpu_source.py`。未来安装使用交付包candidate中的原安装器及新wheelhouse；完整精确依赖随附。当前只验证本地/自建服务。

代码增量：`cpu_pilot.py`计数调度与当次许可；`cpu_source.py`只读累计CPU/NVML/显式rail；`cpu_transport.py`已有SSH mux诊断接收及开销停止；`cpu_interface.py`分析可用性筛选；`cpu_cli.py`入口。原42文件中39字节不变，3项局部扩展见`docs/closeout2-extension.patch`；原native、模型、spec、I-02、Requester和fixed-anchors计划保持原字节。

本轮没有设备连接、真实推理、部署、拟合或旧成绩改写。源侧查询200ms仅目标，真实源窗、共享关系、开销必须经未来许可核对。SSH失效拒绝新连接，旁录不会给原输入续龄，模型available不替代measurement/control/user许可。

测试：`PYTHONPATH=src python -m pytest tests/test_pilot.py`；`PYTHONPATH=src python tests/integration.py FRESH-OUTPUT`。后者只开自有numeric-loopback服务，测试进程临时缩短等待；正式计划不提供缩放或自定义替换入口。虚拟完整时钟测试保留原等待与预算。`scripts/seal_candidate.py`对已审wheel核身份并生成局部patch，不改旧目录。

`config/pilot-plan.json`保留审查方原件；`config/data-role.json`和`resource-budgets.json`是未来新结果前的预登记。能力检查不自动授权12请求；`inspect_capability.py`只生成可复核软件资格回执。活动规则和热预测评价归模型线，当前fixture不代表预测收益。
