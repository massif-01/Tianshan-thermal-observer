# R3b离线独立重跑

全部数据/模型为合成。baseline/wheels/0.1.1仅用于旧缺陷复现，新候选为wheels/0.1.2。不要覆盖已有工作树，不部署。

在新的Python 3.10隔离环境准备requirements-locked.txt全部依赖，非editable安装：

```sh
python -m pip install -r requirements-locked.txt
python -m pip install --no-index --no-deps wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl
python -m pip check
python scripts/check_install_identity.py --source . --wheel wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl --output /tmp/tto-r3b-identity-NEW.json
python scripts/reproduce_offline.py --output /tmp/tto-r3b-verification-NEW
python scripts/verify_r3b_saved.py --runs-root before/reproduction --output /tmp/tto-r3b-same-records-NEW
```

完整入口运行88项（原81+新增7）、离线doctor、模拟训练/时间留出评估、实际Engine/Journal模拟记录/正式报告、真实loopback协议与自身测试进程退出。仅允许测试创建的loopback端点，不运行doctor --live。也可单独运行verify_r3b.py。输出路径必须不存在。依赖准备可能访问包索引；验证不访问设备。

旧缺陷独立复现必须使用另一个隔离环境安装baseline/wheels/0.1.1，然后执行review-original/scripts/check_shadow_quality.py。该原脚本退出0表示复现旧缺陷，不能作为修复通过。原脚本未改；新verify_r3b.py是单独注明的修复断言适配版。

before/reproduction保留修复前生产路径产生的原日志与旧报告；after/same-records是同一批原日志的新报告及哈希不变核对。after/r3b-probes是新安装候选通过Engine/Journal/正式report的正常、冲突、恢复、倒退报告与记录。logs包含第一次新增测试的失败及后续通过记录，不能混用为候选成绩。

SHA256SUMS逐文件清单不包含自身。源码patch起点见before/identity.json，baseline/tree只保存修改前必要文件；新文件以/dev/null标记。必要源码全量位于src，未包含历史大包、凭据或实机记录。
