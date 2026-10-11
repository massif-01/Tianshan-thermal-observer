# TTO 0.1.1 返修独立复审证据

先读主复审文档。结论：R1/R2/R4关闭，R3主体有效，R3b有效统计遗漏需有限收尾；基础只读采集不因此阻断。

## 最小复现

在已有隔离环境安装 `candidate/wheels/tianshan_thermal_observer-0.1.1-py3-none-any.whl`（非editable）。所需配置、数据、模型已在fixtures，均为合成资料，无需联网/设备/训练：

```sh
python -m pip install --no-index --no-deps candidate/wheels/tianshan_thermal_observer-0.1.1-py3-none-any.whl
python scripts/check_shadow_quality.py --output /tmp/tto-r3b-review-NEW
```

输出目录必须不存在。脚本仅使用TTO模块和标准库，未访问任何端点、不启动设备工具。
**退出0表示当前缺陷被复现，不是修复通过。** 程序刻意断言0.1.1存在“510条隔离段评分仍计入”的事实。

`results/shadow-quality/`保存本轮实际执行结果。模型/配置/原观测来自固定模拟生成器；没有真实用户记录。normal为对照，conflict为第350秒收到同身份冲突，conflict_then_recovery为继续恢复到620秒。

## 原回归

安装候选锁定依赖需自行准备已有wheelhouse或另行下载，不由本复现脚本安装。完整81项/Socket.IO可在依赖齐全环境按candidate/scripts/reproduce_offline.py执行。审查者实际独立运行73项，其余8项依赖缺失，详见environment.json；不得将作者81项日志冒充本审查执行。

candidate只包含被审原样软件，不是修复版或自动部署包。不要将其覆盖到有未提交改动的用户工作树。历史结果中会保留审查环境的绝对导入路径，复现脚本自身按相对fixtures定位，不依赖这些路径。
