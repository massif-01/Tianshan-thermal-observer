# TTO 0.2.3 中等负载准备：独立复审证据

读`TTO-中等负载测试准备-独立复审.md`。两项有限修复指令另附TXT。

本包不是候选/安装包，不修改原交付。结果来自本轮源代码阅读、离线测试、哈希与针对性反例；无设备访问、部署、模型拟合或控制写入。

## 使用与复现

本包不重复嵌套原19MB候选。复现时，将原《TTO-软件修改与中等负载测试准备证据包.zip》解到本包同层`candidate/`，其SHA必须为：

`922200ee70fbed09874e0479ed16b45d7497303adf4e9dc5b13a51ded1d55ca2`

在独立环境非editable安装`candidate/code/wheels/tianshan_thermal_observer-0.2.3-py3-none-any.whl`，使用已有依赖；只运行离线脚本，不使用候选site里的真实地址。脚本按自身上级目录定位candidate/results。

- `scripts/check_health_source.py`：生产Engine和健康检查，合成正常→缺TJ→恢复，无网络。
- `scripts/check_readiness_to_request.py`：同一缺TJ状态进入真实调度器；请求器/时钟为替身，无网络。
- `scripts/check_runner_import.py`：旧源PYTHONPATH引入，真实脚本入口语义；阻断并计数所有socket连接/解析。
- `scripts/check_polling_http.py`：抽取旧/新嵌套esp32函数**原样执行**，真实自建loopback HTTP，约23秒；不假装完整Socket.IO/collect重跑。

前三个反例脚本退出0表示**确认旧候选存在问题**，不是修复后的通过标准。修复回归应反向断言，同时保留正常路径。

运行导入反例之前，准备真实旧源（可重复使用已有同版本原件，也可按以下步骤从候选patch反向恢复）：

```sh
cp -a candidate/code before-copy
(cd before-copy && git apply --reverse ../candidate/results/midload-prep-v1.patch)
cp -a before-copy/src legacy-022-source
python scripts/check_runner_import.py
```

新资格端到端重算命令（不训练）：

```sh
python candidate/code/experiments/thermal_identification_prep_v2/coverage_audit.py \
  --handoff candidate/handoff --frozen candidate/frozen-greybox --output availability-new
```

原回归分开运行，避免不同conftest名称冲突；有完整依赖时按作者README跑全部相关50+24。审查环境只独立跑37+24；13项Socket.IO相关未重跑，见报告。

## 文件

`results/`包括完整性、安装字节、patch往返、原模型保护、资格重算逐字一致、两项反例和独立HTTP排程对照。`logs/`包括已执行回归与环境尝试。`scripts/check_polling_http-attempt01.py`为审查夹具早期失败版本，留作追溯，不作为推荐入口。

`SHA256.json`是本证据包文件清单，不包含自身。不含候选私有site地址或真实鉴权信息。与作者日志的原50/24通过数量分开；报告引用作者结果不等于本次独立执行。
