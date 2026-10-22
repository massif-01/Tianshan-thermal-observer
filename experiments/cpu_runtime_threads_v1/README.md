# 数值线程策略与旁录前资源准入 cpu.3

独立源自已审cpu.2精确wheel。未连接设备/修改安装；本目录包含新候选源码、局部patch、锁定依赖增量、离线回放和自建服务验证工具。

运行策略在两个已安装CLI和共用runtime入口调用同一numeric_policy；继承8等冲突值覆盖为1，随后加载并核验NumPy/SciPy OpenBLAS；已提前导入或无法核验则网络前拒绝。没有后设环境冒充池已改变，不改其他应用/系统服务。threadpoolctl只取证，不动态重置已加载库。

资源定义见docs/baseline-resource-contract.md，启动期/样本新鲜度在代码和测试前冻结。相关预算值与cpu.2相同；源脚本和SSH模块未改。

本地复验需要Python3.10–3.12及已接受依赖；参考本包的验证环境和依赖清单。需已安装本目录新wheel及threadpoolctl3.6.0。本地Mac例子的NumPy/SciPy为同版本OpenBLAS wheel，**不是N305验证**。仅有环境变量不能证明数值池；Accelerate等不可核验后端拒绝。

```sh
python scripts/verify_installed_cli.py --prefix /absolute/isolated-env --output /absolute/new-cli-evidence
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -c pytest.ini tests -q --import-mode=prepend -o pythonpath=
python scripts/replay_probe.py --run /absolute/recorded-run --output /absolute/new-replay --candidate-policy --seconds 0
```

12秒节奏对照：从inputs/cpu2.whl解包到新的cpu2-runtime，用同一解释器/数值依赖；默认子进程清除OPENBLAS_NUM_THREADS、OPENBLAS_DEFAULT_NUM_THREADS、OMP_NUM_THREADS、MKL_NUM_THREADS、NUMEXPR_NUM_THREADS，`--package-root cpu2-runtime --paced --seconds 12`；新候选使用`--candidate-policy --paced --seconds 12`。不在同一已加载进程中切环境。紧循环193条只核数学，不将其CPU百分比当实时开销。

`tests/local_cli_service.py PREFIX NEW_OUTPUT`是60秒实际安装CLI/原生collector/observer与自有loopback服务的测试。为不干扰别的本机观察进程，仅测试sitecustomize映射私有锁，flock语义不变；发布源码没有锁绕过开关。计时/CPU/RSS均是真实值，源/proc是明确合成fixture（含计数重置/offline测试）。0推理POST/模型GET，不能把模拟取数资格或吞吐当现场能力通过。测试不得指向真实IP。

目标安装器和依赖增量在candidate/，未来现场流程见docs/操作卡.md。目标Linux x86_64 CPython3.10当前未测，必须另批；本轮不部署、SSH、重启或进入12请求。
