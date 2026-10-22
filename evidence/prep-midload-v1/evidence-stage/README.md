# TTO 软件修改与中等负载测试准备证据

`TTO-PREP-MIDLOAD-v1.0`，本地0.2.3候选，交独立复审。现场部署/实测、新训练、Git提交/推送/PR均未执行。完整结论见同层报告。

- `code/`：基线与此次修改的可重跑源码、研究索引、模型副本、runner、操作卡、现有依赖锁及新wheel。临时环境、Git对象和无关旧产物不进入包。
- `results/midload-prep-v1.patch`：针对a27ddb6f41c887fd9f08d4120f98d97eed31f4d0的源码patch。新wheel单独在code/wheels中，先复制到相应wheels路径再用安装manifest；patch已实际apply-check并逐文件对照。
- `installation/`：新Conda候选，含runner及本地目标配置。私有site配置不在公共patch，包只交本地复审，不自动公开。
- `results/`：冻结规则、逐点新资格、共同集合/误差、覆盖、事件诊断、图及安装身份；`loopback-evidence/`含最终自建服务测试原日志。
- `handoff/inputs/`：L/S完整分享归档和输入索引；`frozen-greybox/`含原spec、data、参数/尝试、已保存评价以及原SHA总表。复核所需原文件逐字相同。原完整灰箱ZIP仍按d2039aaf…索引保留，不递归塞进包。
- `preservation/`：原工作树身份、起点状态及4289个原文件SHA；`logs/`保留失败和最终通过日志。失败覆盖尝试本地仍保存，本包记录其SHA索引，不重复大体积逐点派生内容。

## 先验证包

解压后在本目录执行 `python tools/verify_delivery.py`，只读SHA，不连接任何接口。

## 独立离线复核

在新的CPython3.10环境安装当前锁和0.2.3 wheel；依赖须使用匹配本机平台的已有缓存，本包不提供通用依赖wheelhouse：

```sh
python -m venv .review-env
.review-env/bin/python -m pip install --no-index --find-links /path/to/existing-platform-wheelhouse -r code/requirements-locked.txt
.review-env/bin/python -m pip install --no-index --no-deps code/wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl
.review-env/bin/python -I -m tto doctor --config code/config/tto.example.json
.review-env/bin/python code/scripts/thermal_trials/run_midload.py --plan --trial-config site/local-midload.json
cd code
../.review-env/bin/python -m pytest -q tests/test_polling_schedule.py tests/test_network.py tests/test_failures.py tests/test_config_storage.py tests/test_quality.py
../.review-env/bin/python -m pytest -q scripts/thermal_trials/tests experiments/thermal_identification_prep_v2/tests
../.review-env/bin/python experiments/thermal_identification_prep_v2/coverage_audit.py --handoff ../handoff --frozen ../frozen-greybox --output ../review-availability-v2
```

两组pytest分开运行，避免旧测试的同名conftest导入方式冲突。只重算已保存预测的资格/误差，输出用新的目录；不执行首轮run_experiment、拟合测试或模型搜索。`--live`需未来明确授权，当前复审只用默认plan/dry-run。N305命令与停止/回退见code/docs/TTO中等负载测试操作卡.md，真实地址来源未作现场验证。
