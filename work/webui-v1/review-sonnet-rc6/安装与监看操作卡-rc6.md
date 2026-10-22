# TTO Web UI rc6｜安装与监看操作卡

**候选边界**　模型状态历史后端已新增，首页沿用 rc3。Sonnet 新首页待另行集成验收。本轮仅 macOS 临时 prefix/本地合成源；没有设备连接、现场部署、系统服务安装或推送。新候选应先独立复审。

**1 · 核对包**　核对交付 ZIP 的 `.sha256` 和外部交付核验回执；解包后查看 `candidate-identities.json`、最终 wheel SHA256 及报告。不要用文件名中的 `(1)/(2)` 判断版本。源码、静态资源、模型/spec、wheel 与证据须对应同一新候选。

**2 · 离线试装**　已有独立 Python 环境，不升级 Conda base 或原 TTO。解包目录执行：

```sh
python3 tools/install.py --prefix /private/tmp/tto-web-review --service none --access local
/private/tmp/tto-web-review/tto-web serve --config /private/tmp/tto-web-review/web.json
```

浏览器访问 `http://127.0.0.1:59009/`；无源显示等待。另一个终端可读 `/healthz` 核对 version=1.0.0rc6 与本轮 PID。停止用启动终端的 Ctrl+C，仅停止自己的进程。此处不启用系统服务。

**3 · 历史接入**　显式 GET `/api/v1/series?ids=temperature.tj,model.Tf_C,model.Ts_C,model.E_C&max_points=2000`。默认最近 10 分钟，最大 1 小时、18002 行；共同抽样保留断点与差值极值，密集缺口可超过软绘图预算。首页尚未接入这些新序列；可查看接口/合同示例，合成验证页只在测试夹具中提供。

**4 · 监看语义**　TJ 为实测；Tf/Ts/E 为校正后估计。TJ−Tf 是校正后残差，不是预测误差或独立准确率。Ts 不是结构温度，E 不是室温；状态差值可为负。null 必须断线，不补零、不沿用历史末值作为当前值。degraded 与 tracking 分开标注；历史好点保留，当前值过期仍须撤销。

**5 · 数据组与资源**　完整身份为 service/run/epoch/model/spec；切组立即清缓存并废弃旧请求。Web 预算为 RSS ≤192 MiB、平均 CPU ≤5% 单核等效；新增历史存活分配 ≤16 MiB。rc6 未重跑资源短测；rc5 的本机短测不能作为 rc6 新实测或 N305 成绩。不以修改采样、TTL、风扇或模型压低预算。

**6 · 回退与现场停止线**　存在 previous 时，在原解包目录执行 `python3 tools/install.py --prefix /private/tmp/tto-web-review --service none --rollback`，然后手动重启该 prefix；原 TTO 环境不受影响。真实主机的 follow/observe、LAN 凭据、systemd 开机恢复、断源恢复与资源核验，待复审后另行授权；此卡不授权现在连接设备或部署。
