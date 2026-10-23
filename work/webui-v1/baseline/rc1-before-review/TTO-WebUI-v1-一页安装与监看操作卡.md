# TTO Web UI v1.0｜一页安装与监看操作卡

**状态：本地安装候选，等待独立复审。以下现场命令须另获安装/观察授权；本轮没有执行。**

**1 · 安装**　Linux x86_64、独立 Python 3.10、与原TTO同一非root用户。解压候选后，在包根目录执行：

```sh
python3 tools/install.py --python /绝对路径/python3.10 --prefix "$HOME/TTO-Web" --access local
systemctl status tto-web.service
```

安装器离线建独立env，默认enable/restart，不改原TTO/base。无源也可访问 **http://127.0.0.1:59009/**。本机试装加`--service none`，再运行`"$HOME/TTO-Web/tto-web" serve --config "$HOME/TTO-Web/web.json"`。

**2 · 选择来源**　编辑`$HOME/TTO-Web/web.json`，保留原采样/TTL：

- **follow优先**：`source.mode="follow"`，`active_descriptor`填同用户已注册发布器的`/run/user/UID/tto-web/active.json`。已有旧程序无发布钩子会等待；由原任务拥有者在已授权入口接入`publish-field`（见README），不另开采集。
- **observe**：仅无其他观察者且已批准时，`mode="observe"`，`observation_config`填核实过的原生JSON，`observed_device`填核实标识。模板`config/observation.example.json`的空端点须核实；无任务推理、无SSH、无设备写入。

```sh
sudo systemctl restart tto-web.service
curl -fsS http://127.0.0.1:59009/healthz
journalctl -u tto-web.service -n 30 --no-pager
```

**3 · 跨电脑看**　首次安装显式选`--access lan --bind 实际N305地址 --allowed-origin http://实际N305地址:59009`，使用该地址访问；只读口令在prefix的`readonly-password.txt`（600）。已装配置不会被选项覆盖；修改后重启。不要改防火墙或暴露公网。

**4 · 监看**　先区分Web连接、设备样本有效、模型阶段；看C/D/E与来源抽屉。RPM未确认不是停转；Ts/E不是结构/室温；预测误差=预测−实测，缺标签/待到期单列；无核实曲线就无建议PWM。暂停只冻结画面。盯住Web单核CPU/RSS与显示重同步，不以改源频率/TTL压预算。

**5 · 等待/冲突**　未配置/发布器未注册：等待；观察锁冲突：已有程序优先，改follow，勿kill未知进程；59009占用：启动退出，勿杀占用者。follow停止Web不停止外部实验。

**6 · 停止、回退、移除服务**

```sh
sudo systemctl stop tto-web.service
python3 tools/install.py --prefix "$HOME/TTO-Web" --rollback
python3 tools/install.py --prefix "$HOME/TTO-Web" --uninstall-service
```

回退需存在previous，切换后重启；移除只停用Web unit，保留独立prefix/证据与原TTO。升级默认保留`web.json`和上一Web版本。现场开机恢复、资源与真实链路仍待另行核验。
