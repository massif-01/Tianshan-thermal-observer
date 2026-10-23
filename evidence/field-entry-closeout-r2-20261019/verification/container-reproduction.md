# 目标环境复现边界

实际验证：Ubuntu22.04 amd64容器，CPython3.10.12，glibc2.35；2 CPU/2GiB边界，OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1。Mac宿主使用兼容层运行；这不是N305性能证据。

先在自己的隔离Ubuntu22.04容器准备python3.10/python3.10-venv，再将本包只读挂载为/bundle，新的可写证据目录挂为/results。不得挂载真实设备、秘密或生产目录。

```sh
python3.10 /bundle/candidate/install_candidate.py --prefix /results/env --wheelhouse /bundle/candidate/wheelhouse
/results/env/bin/tto-field verify-install --target
/results/env/bin/python /bundle/source/tests/run_loopback.py /results/loopback diagnose normal disconnect short_gap guard user_stop unknown
TTO_TEST_STATE_FILE=/results/loopback/normal/output/states.jsonl /results/env/bin/python /bundle/source/tests/test_entry.py
/results/env/bin/python /bundle/source/tests/run_virtual.py /results/full-virtual
/results/env/bin/python /bundle/source/tests/check_lifecycle.py /results/lifecycle
/results/env/bin/python /bundle/source/tests/check_exit_under_load.py /results/active-exit
/results/env/bin/python /bundle/source/tests/check_timeout_diagnostics.py /results/timeouts
/results/env/bin/python /bundle/source/tests/check_instrument_sidecar.py /results/instrument-sidecar /results/loopback/normal/output
```

目录必须全新，不自动覆盖/重跑。完整虚拟时间只压缩等待，实际loopback测试保留原1/5秒轮询及2秒HTTP预算。原14项新增检查不等于旧28/23/6重复相加。5319投影数值库兼容引用已有保存流，不把它装成新实测数据；它只重喂冻结状态算法，不做拟合。

实际镜像环境来源/依赖及安装身份见bootstrap.log、delivery-identity.json和delivery-dependencies.lock。native原始文件及field索引均保留，artifact本身的完整性仍以本包SHA清单为准。
