本目录是 TTO-MAINLINE-RETURN-v1.0 的模型线离线交付。旧模型、原 observer、旧成绩和生产 TTO 均不改。CPU 逐核、200ms 和原 12 请求继续暂停。

用户获得两件可以实际使用的东西：`baseline/` 内固定 G2 的只读预测接口，以及 `tool/` 内真正运行的生成、校准、比较和本地版本管理工具。冻结基线已提前单独交给测试线；新候选留待复审，不替换试跑版。

入口与证据：

- `baseline/API说明.md`、`baseline/model-card.md`：原件身份、接口、缺口/恢复与跨端 golden，主模型 deployable=false。
- `config/`：训练前写定的数据角色、六初值、约束、目标、资源预算及未来数据规则。
- `runs/generate/`：L 训练六初值，选 N5；`runs/calibrate/`：以 L 生成模型为父版本，仅用相对该父版本新增的历史 M 训练六初值，选 N2。选择只看训练 J。
- `runs/compare/`：历史 S 上同集合的 A-long、A-roll、B-HOLD、B-RELAX30、B0/B1/LP30/LP120，逐点、覆盖、缺失和分层全部保留。
- `diagnostics/`：十二次尝试汇总、输入共线、参数稳定性和尾部原始引用。没有追加拟合。
- `verification/`：测试、资源与本地版本切换/回退命令回执；失败的启动尝试也保留。
- `scripts/replay.py`：独立重跑，默认不拟合；`scripts/rebuild_dataset.py`：从明确提供的旧 R2 原归档重建输入，可字节级复核。
- `一页决策卡.md`、`数据合同与工具用法.md`：给负责人及后续数据交接使用。

使用 Python 3.12，以及本目录 `requirements-research.txt` 记载的现有研究依赖；不修改项目生产依赖。C 编译器需支持 `cc -O2 -fPIC -shared ... -lm`。当前执行是 macOS Accelerate，已在 `config/runtime-amendment-before-fit.json` 中于优化前登记，所有数值线程环境变量请求 1；此后端不能由 threadpoolctl 证实实际工作线程数，不能当现场 OpenBLAS 线程验收。其他环境应先明确冻结适合它的 runtime_profile，不伪称同一运行环境。

在解压后的本目录执行（`python` 指上述环境；输出路径必须不存在）：

```sh
PYTHONDONTWRITEBYTECODE=1 VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/replay.py --output /private/tmp/tto-mainline-review-replay
```

默认重跑 A1 的 5 项测试、新工具的 12 项测试、真实 JSON API 调用及保留候选的完整比较，检查逐点身份/数值一致性，绝对容差 1e-8。它不发任何网络或设备请求。`--fit` 才会额外运行固定六次 generate 和六次 calibrate，输出到新目录；不同数值后端可能在近乎同 J 的种子间改变选择，不能要求新时间戳/新模型 SHA 或 θ 位级相同。

本包包含独立计算所需的规范化 L/M/S、原始引用、完整来源身份和 SHA；不重复塞入过去数十 MB 的历史归档。需要从原质量证据再次重建规范化输入时，显式提供 `inputs/source-registration.json` 所列 SHA 的旧归档，运行 `scripts/rebuild_dataset.py --archive 原归档.zip --output 新目录`。原私有日志与分享归档的 SHA 区别见 `inputs/original-source-inventory.json`，没有被合并成同一身份。

`source.patch` 只含本轮新研究目录内的软件/测试/配置/使用文档；数据和计算产物由完整证据 ZIP 提供。无需、也不应通过覆盖生产 TTO 来使用研究工具。注册表示已保存，选择表示新会话的本地版本意向，均不等于部署或获准控制。
