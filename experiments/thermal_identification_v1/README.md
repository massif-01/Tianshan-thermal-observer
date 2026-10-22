# TTO-GREYBOX-ID-v1.0：已执行的离线研究

先读 [实际结果报告](TTO-首轮灰箱实际辨识与对照实验报告.md)。36次主拟合、一次d1=0、双向迁移与合并表达检查均已执行。没有设备、网络采集、控制或发布入口；研究JSON不兼容生产模型加载器，`deployable=false`。

## 复核已有结果（不重新拟合）

在本目录，使用有 NumPy/SciPy 的 Python：

```sh
python verify_results.py --run runs/main --output readback-new.json
```

输出必须为新文件。这个命令核对冻结SHA、初值择优、实际标签／共同集合、B指标与独立增广矩阵指数。ZIP中每个文件的清单为根目录 `SHA256.json`；它不包含自身。原始三包不递归打入本包，其精确SHA见 `runs/main/source-archives.json`。

## 从原始分享归档独立重跑

从最初的《TTO-首轮灰箱实际辨识与对照实验-Codex交接包.zip》解出 `inputs/`，包含三个ZIP和 `input-index.json`；保留原层级。不能拿私有manifest哈希替换分享文件的哈希。全部请求文本不进入派生特征或输出。

核心运行环境：Python 3.12.3、NumPy 2.2.6、SciPy 1.14.1、scikit-learn 1.6.1、threadpoolctl 3.7.0、pytest 8.3.5，以及本机 C 编译器。实际使用仓库既有 `.venv`，未安装/升级生产依赖。独立环境依赖列表见 `research-requirements.txt`；需要安装时只安装到新的研究环境。C内核会在输出目录编译；没有CUDA依赖。

```sh
python run_experiment.py \
  --spec experiment-spec.json \
  --input-index /ABSOLUTE/PATH/ORIGINAL_HANDOFF/inputs/input-index.json \
  --output /ABSOLUTE/PATH/NEW_RESEARCH_RUN
```

默认 `--stage all` 顺序执行输入校验、数据回放、冻结、G1-L/G2-L/G1-S/G2-S及Ridge、双方参数冻结、目标评价、F-POOL、唯一d1=0、诊断和状态。输出目录必须不存在；不会覆盖旧实验。原始质量源码从第三个原包取出并按其SHA核对，不依赖当前 `src/tto` 的变化。`sources/tto-reference/` 是本次包内同一源码副本，供独立审读。

作者为了在拟合后完成评价代码，分两阶段运行：`--stage directions` 后 `--stage finish`。后者只能用于已经完成方向冻结且尚未产生 `evaluation/` 的目录，先核验冻结文件。第一次评价入口空矩阵错误的空目录和日志已单独保存；修复后只重启评价，没有重训双向模型。最小独立重跑直接使用默认 `all` 即可。

计算合同：最多36次主非线性拟合、每次300 nfev及1500实际残差调用，1 BLAS线程，2GiB RSS目标，2小时总计算软预算。实际核心流程42.73秒、约531MiB。每次求解边界与调用预算由程序执行；RSS与总耗时为记录/人工监督的软目标，不是操作系统硬限额。时长不含实现/阅读/测试/绘图/打包，更不是N305基准。

## 测试、图表与报告

新的研究测试在读取新重跑数据时设置该路径；不设置时读取交付的 `runs/main`。

```sh
TTO_RESEARCH_RUN=/ABSOLUTE/PATH/NEW_RESEARCH_RUN \
  python -m pytest tests -q --basetemp=/ABSOLUTE/PATH/NEW_TEST_TEMP
python plot_results.py --run /ABSOLUTE/PATH/NEW_RESEARCH_RUN \
  --output /ABSOLUTE/PATH/NEW_RESEARCH_RUN/charts
python report.py --run /ABSOLUTE/PATH/NEW_RESEARCH_RUN \
  --output /ABSOLUTE/PATH/NEW_REPORT.md
```

绘图另外需要 Matplotlib。作者复用 `/private/tmp/tto-analysis-20261013-env` 的 Python 3.14、NumPy 2.5.4、Matplotlib 3.11.2，仅读取保存结果；核心拟合依赖未改变。图表的运行版本在 `charts/plot-environment.json`。生成报告含本次的解释性文字与固定验证结论；复跑到不同环境或不同结果时应重新核对这些结论，不把模板文字当验收。

相关既有回归的原样副本在 `sources/related-tests/`。已执行的是11项与本轮复用质量/平台链有关的测试，不是整套仓库回归。独立执行同一集合：

```sh
python -m pytest \
  sources/related-tests/test_review_repair.py \
  sources/related-tests/test_platform_curve.py::test_thor_rails_units_without_alias \
  sources/related-tests/test_platform_curve.py::test_qualification_does_not_relax_invalid_temperature \
  sources/related-tests/test_platform_curve.py::test_gpu_age_sum_duplicates_utc_and_window_gap \
  sources/related-tests/test_platform_curve.py::test_same_identity_additive_fields_isolate \
  -q -o pythonpath=sources/tto-reference/src \
  --basetemp=/ABSOLUTE/PATH/NEW_RELATED_TEST_TEMP
```

相关测试导入原 CLI/collector 模块但由离线guard阻断外部连接和进程启动；不会启动现场采集。对应导入依赖列在研究依赖中。

## 文件与语义

- `experiment-spec.json` 与 `runs/main/freeze.json`：拟合前冻结，代码变更时间和唯一初始化修复另记，不悄悄改历史冻结。
- `data.json`：4139个accepted点、56个严格连续段、原引用、所有传播输入事件及TTL、逐规则排除。约1秒资料不是独立样本集合。
- `fits/`：全部36次主尝试、选择记录、6个灰箱模型、三套按h独立的紧凑Ridge及单次嵌套诊断。
- `evaluation/`：A与B分离，固定HOLD/RELAX30分离，共同集合ID、覆盖分母、逐起点状态证据和请求窗口。
- `diagnostics/`：灵敏度含/不含nuisance、参数散布、输入共线、残差、热点、数值/初态敏感性。
- `protected-before.json` / `protected-after.json`：起始HEAD与3506个既有文件字节保护检查；没有创建分支或修改Git索引。
- `research-code.patch`：仅新增研究代码、测试、README与spec的补丁，路径相对仓库根；在空临时仓库通过 `git apply --check`，未应用到既有脏工作树。
- `executed-commands.json`、环境/资源、通过与失败日志、图表视觉核对和SHA：验证范围可区分，原三包按SHA引用。

F-LS/F-SL都是开发迁移/反向压力检查；F-POOL参数来自整轮，只能作拟合内描述。B的输入特征因果不意味着这些参数在历史现场已经可用。潜在状态不是实测热容，状态估计不是在线参数学习。`target_validation=not_performed`，`control_authorization=none`。本轮到此停止。
