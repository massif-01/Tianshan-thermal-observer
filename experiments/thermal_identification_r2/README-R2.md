# TTO-ID-R2-v1.0 独立离线重放入口

本目录实际完成M登记、九份旧JSON冻结检验和第二轮42次非线性拟合。所有模型deployable=false。原采集器、runner、生产模块、依赖锁和风扇未修改；入口没有网络/设备调用。

证据ZIP解压后，本文件与research.py、vendor、runs/main位于同一目录。原三轮资料和首轮完整归档不重复打入成果ZIP，使用本次用户交接包的inputs目录；六个原归档的完整SHA见handoff/inputs/input-index.json。bootstrap需要完整解压后的原交接目录，不能只给runner-summary。

研究环境实测为CPython3.10.18、NumPy2.2.6、SciPy1.14.1、scikit-learn1.6.1、psutil7.0.0、pytest8.3.5，CPU、BLAS单线程。绘图另用已有CPython3.14.0/Matplotlib3.11.2环境。这里不安装或修改任何生产依赖。

当前本机命令（在本研究目录执行）：

```sh
RESEARCH_PYTHON=/Users/massif/Tianshan-thermal-observer/.venv310/bin/python
"$RESEARCH_PYTHON" bootstrap.py --handoff /Users/massif/Tianshan-thermal-observer/experiments/thermal_identification_r2/handoff
"$RESEARCH_PYTHON" -m pytest -q tests
"$RESEARCH_PYTHON" readback.py
```

独立核对者没有作者原工作树时，只跳过工作树文件的本机存在性核对，仍核对阶段冻结、九份模型、全部评分表和JSON抽样回放：

```sh
python bootstrap.py --handoff /path/to/完整解压的原交接包
python readback.py --skip-workspace-integrity
python -m pytest -q tests
```

readback在副本重建CPU传播库并写自己的复核回执，不训练模型。先核验本成果SHA256.json；重放后某些资源/编译日志会反映副本环境。作者的工作树哈希核对回执、封存结果和测试日志已保存，独立副本不能冒称访问过作者工作树。

如独立复审需要完整重新执行本轮，使用新空目录，保留本次产物。该命令重新运行同一42次矩阵，不扩初值/模型族：

```sh
python rerun.py --handoff /path/to/完整解压的原交接包 --destination /path/to/一个尚不存在的新研究目录
```

需要重绘图表时加`--plot-python /path/to/已有Matplotlib的python`。rerun复制研究代码到新目录，顺序register→frozen→refit→diagnose→readback，输出均在新目录。原M三个块不会生成三个初态。原旧模型由精确成员索引加载，不能替换为旧85/5 Ridge。

也可在独立副本里逐阶段执行，research.py拒绝覆盖既有输出和缺少封存的训练：

```sh
python research.py register --out runs/a-new-run
python research.py frozen --out runs/a-new-run
python research.py refit --out runs/a-new-run
```

核心计算代码SHA在stage1-frozen-registration.json，阶段2主逐点与主评分SHA在stage2-frozen-evaluation.json。事件汇总、图表和文字报告是从封存逐点数据后置派生，未用于选初值/扩搜索；其SHA由最终成果清单覆盖。未来辅助缺口的B误差保留且分层，A仍需完整未来输入。

索引：

- runs/main/registered：同原处理器回放、数据、例子、资格与来源。
- runs/main/old-models-on-M：三套旧参照的A-long/A-roll/B、状态、分层成绩、覆盖。
- runs/main/fits：42次尝试、七个新灰箱JSON、三份9/15列Ridge JSON。
- runs/main/evaluation：两个开发方向及联合的旧/新配对、A24诊断。
- runs/main/diagnostics：训练初态重建、事件峰值/回落、输入共线、参数/初态敏感性、数值/残差、热点近似。
- runs/main/figures：六对PNG/SVG，资格缺口不连线补造预测。
- runs/main/*tests.log、readback-verification.json、*-resources.json：离线验证与资源。
- code.patch：仅新增研究代码/测试/本地研究文档，可在空目录git apply --check。

本轮完成后停止。没有在线参数学习、设备部署、现场控制收益或放行结论。
