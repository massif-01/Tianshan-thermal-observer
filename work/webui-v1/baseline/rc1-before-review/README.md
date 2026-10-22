# TTO 热观察台 1.0.0rc1

这是可离线安装的只读 Web UI 软件候选。最终结果与证据边界见《TTO-WebUI-v1-实施与验证报告.md》；安装与停用见《TTO-WebUI-v1-一页安装与监看操作卡.md》。本包不附带现场安装、设备访问或负载许可。默认配置没有来源，也不会自动加载样例。

## 软件入口与安装

目标 Linux x86_64 / Python 3.10。wheelhouse 包含锁定的 cp310 Linux 轮子；另外包含本地 macOS ARM64 / Python 3.12 验证用轮子。不要在原 TTO 或 Conda base 中安装；安装器创建独立 prefix/releases/VERSION/env。运行时不需要 Node、CDN、外网或数据库。

```sh
# 仅临时本机安装验证，不启用系统服务
python3 tools/install.py --python /absolute/path/to/python --prefix /tmp/TTO-Web-check --service none
/tmp/TTO-Web-check/tto-web serve --config /tmp/TTO-Web-check/web.json
# 在本机访问 http://127.0.0.1:59009/；初始页面准确显示等待。
```

正式 Linux 安装在独立复审通过并获得现场授权后执行：

```sh
python3 tools/install.py --python /absolute/path/to/python3.10 --prefix "$HOME/TTO-Web" --access local
```

默认安装 systemd system unit，以当前非 root 用户运行，自动 enable/restart，检查 is-active 后再核对本机 healthz PID 与该 unit MainPID；sudo 只安装 unit。不要以 root 安装或混用不同 TTO 用户。端口固定59009，冲突会退出，不杀占用者。`--service user`生成用户服务；其离线登录保持策略需主机另行核查。`--service none`只用于本地测试，不开机启动。

## 只读来源

`prefix/web.json`是持久配置，升级不会覆盖。修改后重启 Web 服务，不需要升级原 TTO。配置模板分别为 `config/web.json`、`config/observation.example.json`。

- `follow`：优先选择。设置 `source.active_descriptor`，消费同用户、同Linux boot的注册 Unix 发布流。不会根据目录 mtime 猜测活动run，也不会另开设备轮询。旧 TTO 没有发布钩子时会等待，不能把旧数据目录当活动流。
- `observe`：仅在已批准配置、没有其他观察者时选择。设置 `source.observation_config`为原生配置文件，`source.observed_device`为已核实设备标识；与已有 collect/shadow/field 共享 `/tmp/tto-observer-UID.lock`。复用原采集/质量/冻结观察器，不构造推理Requester，不列模型，不开SSH旁录。冲突时保留网页并提示；不会停止别人。
- 原生配置须填写经批准的端点与源间隔证据。模板端点为null，不能直接启动观察；采样/TTL沿用冻结合同，不为页面改动。凭据仅保存在原配置引用的本地600文件中。

已有 field 运行需要由其拥有者在获准的下一次入口接入发布钩子：`tto-web publish-field --config ... --binding ... --output ... --descriptor /run/user/UID/tto-web/active.json --mode diagnose|execute --duration ...`。它执行原有 field 授权校验并使用同一 engine/projection/observer，不是绕过原许可的启动器。`field-template`只生成未批准binding，仍需原流程核实。本轮只用自建端点测试了该代码路径，未执行任何现场入口。

发布目录必须为同用户私有短路径（Unix socket路径少于100字节），例如 `/run/user/UID/tto-web`；descriptor 固定指向同目录 `publication.sock`，socket/descriptor为600。Web与生产者须在相同时钟域/用户。Web关闭不会结束外部follow生产者；observe关闭只停止自己的采集。

## 本机与LAN

本机默认127.0.0.1:59009。LAN是明确安装选择：

```sh
python3 tools/install.py --python /absolute/path/to/python3.10 --prefix "$HOME/TTO-Web" --access lan --bind ACTUAL_N305_LAN_IP --allowed-origin http://ACTUAL_N305_LAN_IP:59009
```

在首次安装时选择；已存在配置需人工调整`web.json`后重启。LAN口令由安装器生成至`prefix/readonly-password.txt`（600），配置只存加盐PBKDF2摘要；访问页面后登录。不要将口令放URL。来源/Host显式核实，无任意代理，无自动防火墙或公网发布。LAN HTTP属于可信本地网络访问，HTTPS终结/公网不是本候选部署范围。

## 语义与资源

- 默认TJ/CPU/GPU温度、两rail W、成功PWM、独立NVML年龄、逐核与RAM/SWAP；0与缺失不同。RPM目前未确认；原报0只留在上次原始观测，不解释为停转。
- C固定G2依赖，Ts/E为模型内部态；TJ是测量校正，不画成热功率。D真实发布15/45/90秒HOLD并在目标后同epoch首个有效TJ（最多+2秒）成熟；误差是预测减实测。回放/晚发/缺标签/跨epoch单列。
- E仅展示已登记任务事实；无runner就未知，客户端DONE不等于GPU停止。没有校准置信度或结构测温。平稳需求无合法provider，明确未计算。
- PWM观察建议仅支持核实本地曲线参考，必须有方法/设备/fan0/温源/配置摘要/曲线摘要和当前正常保护语义；域外禁止外推。默认没有现场曲线，返回null和原因。不要手填示例曲线冒充生产依据。合法曲线格式与哈希规则见`State.validate_curve`和测试，仅合成测试曲线曾产生数字，未宣称现场建议可信。
- 运行时Python aiohttp + 已构建TS/ECharts；无前端开发服务，无数据库。1Hz页面更新，质量过期检查0.1s；新数据/显示周期/到期才重建快照，GET快照实时刷新；单线程数值运算，等待来源不加载NumPy/SciPy；SSE最多4、每客户端8项，慢客户端只损失显示帧。浏览器暂停/后台降低绘制，不停止采集。
- 曲线与预测增量传输；历史60分钟且每序列18002点、预测11070条、事件1000条、标签随预测出队清理。只读observe不落原始日志。systemd错误日志限流；不清理原TTO数据/日志。release和previous保留供回退，不自动删除历史版本。
- 资源预算为192MiB RSS / 5%单核等效；最终本机持续计量见报告，不替代N305核验。观察器原有成本、浏览器成本与新增Web过程分别说明。

## 构建与测试

```sh
# 开发环境，与原TTO隔离
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.runtime.lock build==1.2.2.post1 setuptools==80.9.0 wheel==0.45.1 pytest pytest-asyncio jsonschema
npm_config_cache=/tmp/tto-web-npm-cache npm --prefix frontend ci
npm_config_cache=/tmp/tto-web-npm-cache npm --prefix frontend run build
.venv/bin/python -m pytest -q
.venv/bin/python tools/build_candidate.py
```

构建需要Node；运行不需要。测试中`TTO_WEB_TEST_BOOT_ID`仅允许非Linux自建测试，并强制test_replay，不允许伪装live。`tools/self_source.py`、`browser_service.py`明确为自建测试入口，不在serve默认启动，也不是设备配置。共享锁测试需要停止本任务自己的自建观察者；真实CLI回归使用59009，须先停止自己的Web。有其他监听者时不终止该进程，换测试时段。

`candidate-identities.json`校验安装文件；`src/tto_web/web-candidate-files.json`校验新候选源码；`baseline-identities.json`和`baseline/`记录原轮子身份。`vendor/tto_field/candidate-files.json`保留历史原件，不用它冒充新候选身份。`patches/`给出对accepted包的最小差异。
