# Tianshan Thermal Observer · 天山热观察器

软件可用，预测效果待真实数据验证。TTO 在 CPU 上记录现有系统的温度、负载、功耗和成功 PWM，提供未来 15/45/90 秒 TJ 参考及事后评估。没有风扇、温度绑定、源频率、服务或设备写操作；退出只停止观察。

目标环境：Intel N305 / 16GB / Ubuntu 22.04，出厂已预装Conda；TTO使用独立Conda环境中的Python 3.10。当前交付的主机验证为 macOS ARM64，目标机资源及真实连接尚待验证。只有一个风扇，预测目标是 Jetson TJ。

**测试者从这里开始：** [中文使用说明](docs/TTO测试者使用说明.md) · [第一次测试操作卡](docs/TTO第一次测试操作卡.md) · [测试记录模板](docs/TTO测试记录模板.md)。

## 项目路线图与技术决策

[主路线图 Issue](https://github.com/massif-01/Tianshan-thermal-observer/issues/1) · [热建模、持续校准与跨 Jetson 适应路线图](docs/roadmap/TTO-roadmap.md)

当前先使用 v1 取得可信真实数据；Ridge 保留为参照，低阶灰箱为下一阶段重点，在线学习与跨硬件适应按证据推进。具体状态与决策记录见上述入口。

## 安装与离线检查

下载[0.2.2 Conda 便捷安装包](deliverables/TTO-v1-0.2.2-Conda便捷安装包.zip)，解压后在包目录执行 `sh install.sh`。默认安装到 `~/TTO`，复用出厂Conda创建独立Python 3.10环境、安装锁定依赖和0.2.2 wheel、核对身份并做离线doctor；设备地址可以稍后填写。安装后入口为 `~/TTO/tto`。重复安装保留配置、模型和数据；详见[便捷安装](docs/便捷安装.md)。

下面保留开发用venv手动安装示例；出厂N305使用上面的Conda安装脚本：

```sh
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements-locked.txt
.venv/bin/python -m pip install --no-deps wheels/tianshan_thermal_observer-0.2.2-py3-none-any.whl
.venv/bin/tto doctor --config config/tto.example.json
.venv/bin/tto demo --output /tmp/tto-demo-NEW
```

源码目录开发安装可改用 `python -m pip install '.[train,test]'`。依赖锁固定已验证版本；NumPy/SciPy/scikit-learn 只在训练命令加载，采集不加载训练库。不要在真实连接时运行回归脚本。

证据包安装依赖需要已有本机 wheelhouse 或一次包下载；准备依赖之后，以下重跑本身完全离线，只允许测试的 loopback 服务：

```sh
.venv/bin/python scripts/reproduce_offline.py --output /tmp/tto-replay-NEW
```

## 用户运行的有界采集

复制 `config/tto.example.json` 为本机配置，只在本机填写两路 `base_url`。URL 只接受 HTTP(S) origin，不带用户名密码、路径或查询。新版配套服务提供平台声明及 `telemetry_meta.source_sample_interval_ms`，TTO 自动读取 Orin / Thor 和实际源周期；建议保持配置中的 `source_sample_interval_ms` 为 `null`。未知平台会明确显示未确认，不猜测。旧服务缺少周期声明时，才由用户填写实际周期及 `source_interval_evidence`；非空配置与新版服务声明冲突时会报告冲突并停止模型资格，不改变源采样频率。周期未知时仍可记录，但模型不启用。

已有凭据通过 `headers_file` 引用权限 600 的本机 JSON，例如 `{"Authorization":"..."}`；TTO 不登录、不猜口令，文件内容不会进入记录。自签 TLS 可指定 `ca_file`，不关闭验证。`.env` 不自动加载。端点为空，不扫描内网。

配套 `rm01OrinStatus` 在独立项目维护，本仓库只交付 TTO。服务部署由用户另行安排，保留实际安装包身份、服务生效配置与回退资料，填写 `templates/deployment-record.example.json`。HTTP 和 Socket.IO 不能证明安装 wheel 的身份，TTO 报告默认保留 `deployment_unverified`，不会拿旧 main 或历史 wheel 哈希补齐。可用 `--deployment-record 本机JSON`登记用户提供的最终证据，完整记录标为 `user_recorded_not_independently_verified`；缺少部署身份时真实评估仍写证据不足。

```sh
.venv/bin/tto doctor --config config/local.json --live --duration 180
.venv/bin/tto collect --config config/local.json --duration 1800 --episode normal-process-01
```

Conda 安装默认记录到 `~/TTO/runs`；手动安装且未改配置时记录到 `~/.local/share/tianshan-thermal-observer`，每轮新建私有目录；结束时命令打印 run 路径。`--episode` 只填短场景词，同一持续热过程跨 run 时沿用同名；独立性仍需用户确认，不把文件数当实验数。没有该分组说明时，正式切分拒绝宣称独立过程；可显式 `--exploratory` 做受限探索。

`collect`/`shadow` 是明确联网命令，用户运行即授权该端点的本轮有限只读访问；助手只有另获对应时段授权才执行。没有常驻服务或开机项。

## 离线建模与评估

```sh
.venv/bin/tto summarize --run /path/to/run
.venv/bin/tto report --run /path/to/run --output /tmp/record-report-NEW
.venv/bin/tto split --runs /path/run1 /path/run2 /path/run3 /path/run4 /path/run5 --output /tmp/frozen-NEW
.venv/bin/tto train --dataset /tmp/frozen-NEW/dataset.json --split /tmp/frozen-NEW/split.json --output /tmp/model-NEW.json
.venv/bin/tto evaluate --dataset /tmp/frozen-NEW/dataset.json --split /tmp/frozen-NEW/split.json --models /tmp/model-NEW.json --output /tmp/evaluation-NEW
```

至少三个完整过程可做探索；五个以上时默认至少两个全新测试过程。一个长过程只能通过 `--exploratory` 留真实时间隔离带，不能升级长期旁路候选。四个方法是保持、30秒趋势、TJ历史 Ridge、多输入 Ridge。字段选择和加权标准化仅看训练区，小网格仅看验证区45秒；测试清单一次使用，评估开始前写 `test-used.json`。看测试后改模型，需要新的未使用过程，不复制清单绕过登记。

若不训练模型，`evaluate` 可省略 `--models` 只报告基线与缺证据。JSON 模型有完整性校验、维度和有限数检查，不加载 pickle/joblib。没有正式模型成绩也能正常采集。模拟模型被明确禁止通过 `shadow` 连接真实端点。

## 固定模型旁路

只有用户审阅真实评估并确认窗口后，运行：

```sh
.venv/bin/tto shadow --config config/local.json --model /path/frozen-real-model.json --duration 1800 --episode observed-process
```

该命令只观察，不在线训练，不自动切换模型。模型不可加载时撤下模型结果，继续记录及明确标注的基线；缺多输入时实际方法降级，不能算 M1 成功。断线、缓存过期、异常状态或输入合同不支持时撤下资格、断段和重新预热。已发预测不可改写，未来评分单独追加，有界等待到期失效。

## 边界

时间轴为本机接收时间近似；不是硬件采样时刻，源年龄不含未测网络在途时间。成功 PWM 是最后下发逻辑百分比，target_duty 和 RPM 不能替代它。功耗 rail 单独用 W，不相加为总功耗。没有铝体温度/热容识别，没有 GPU/CUDA/LLM，没有降低 PWM 或降噪收益结论。

详细合同见 `docs/contracts.md`，所有 CLI/环境覆盖见 `docs/CLI使用卡.md`。验收、失败修正及现场待办见 `TTO-v1-实施与验证报告.md` 和 `PROGRESS.md`。

## 0.1.1 有限返修

R1—R4修复保留原架构与模型路线。跨run分组使用完整接收时间范围，非连续同名过程明确报冲突；分层评估分别比较B0/B1、B0/B1/M0、B0/B1/M0/M1；shadow报告读取当时已保存的预测/评分及模型身份；WebSocket实际握手在跳转前拒绝。原交付保留为历史起点，不作为本轮候选。详见`docs/R1-R4-repair-contract.md`和`TTO-v1-R1-R4返修与验证报告.md`。

R3b旁路报告区分历史保存评分与当前有效成绩，应用生产质量层已有的段隔离；恢复段继续统计，历史分母与原始日志保留。字段及覆盖率定义见[报告资格合同](docs/R3b-report-eligibility.md)。离线重跑：`python scripts/verify_r3b.py --output NEW_DIRECTORY`，使用固定合成夹具，不连接设备或训练模型；原独立复审脚本以退出0表示旧缺陷复现，不能当修复通过。


## Orin / Thor 与 CURVE 本地候选 0.2.2

配套监控服务为tegrastats-api 1.1.1。平台从计算模块设备树声明自动选择，CURVE使用成功PWM并保留控制温度资格；GPU错误不伪造为0。新run/dataset/model使用schema2，旧run按schema1冻结规则回放。当前候选只完成本地修改与离线验证，不代表新包实机通过或真实模型收益。

测试者先读[中文使用说明](docs/TTO测试者使用说明.md)，接口和维护边界见[新版合同](docs/platform-curve-v2-contract.md)。既有0.1.2及0.2.0交付和哈希是历史资料，0.2.1是返修中间候选。当前候选为0.2.2：

- [F1—F3返修与验证报告](TTO-F1-F3有限返修与验证报告-20261013.md) · [证据包](deliverables/TTO-0.2.2-F1-F3返修证据包.zip) · [交付核验](deliverables/TTO-0.2.2-F1-F3交付核验.json)。报告和回执记录的是封包时状态；后续提交 PR 不改写这些历史证据。
- [0.2.2 wheel](wheels/tianshan_thermal_observer-0.2.2-py3-none-any.whl) SHA-256：`53a1c2a9b60abb41071a57ca8bcfea322e0835ae2039ccba9b95a98519f7cb27`。
- Conda 安装包 SHA-256：`f555287011e00ab41f960ae2c5ac79e59f4857ce35abf378cea326171d5d90d1`。

封包时源码与干净非editable安装各189项回归通过，Conda安装器10项通过；验证环境为macOS ARM64 / Python 3.10，协议测试仅使用loopback。N305/Linux现场安装、真实连接及预测效果未验证。仓库说明更新不改变上述已验证安装包与证据包的SHA。

## 实机采集报告

见[实机采集报告目录](docs/reports/README.md)：包含工况分析、温度/功耗/GPU/PWM时间线和原始数据与操作记录。

## 本地研究与测试准备

首轮冻结灰箱研究的代码、模型副本和来源SHA见 [研究索引](docs/research/greybox-id-v1/README.md)。新A/B资格仅写独立研究结果，见 [准备研究](experiments/thermal_identification_prep_v2/README.md)。0.2.3中等负载候选的 [操作卡](docs/TTO中等负载测试操作卡.md) 默认离线预览；现场未执行，须先独立复审。
