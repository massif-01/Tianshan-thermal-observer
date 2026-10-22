# TTO Web UI 1.0.0rc2 · 安装与监看操作卡

**状态：本地候选，等待独立复审。本轮不执行下列现场步骤。** 复审通过并另行安排 N305 后，再使用同一 TTO 用户操作；不改变天山 OS 控制与原采样/TTL。

**身份**　wheel `tto_web_ui-1.0.0rc2-py3-none-any.whl`（509462 bytes）
SHA256 `d035bd24da55450f28f37bd8bc40d50c00b401e3e425632f5d67ced9f518ca70`
新包 `TTO-WebUI-v1-rc2-有限修正与安装候选.zip`；外层 `.zip.sha256`，安装前核对 `candidate-identities.json`。详细证据见 rc2 有限修正报告。

1. **离线安装到独立 prefix。** 保留原 TTO/Conda base，选已批准的独立 Python 3.10。在解压目录运行；安装器核验 120 项文件、离线依赖和 62 项运行身份。下例为已获准现场安装后的 follow 模式：

   ```sh
   /path/to/python3.10 tools/install.py --python /path/to/python3.10 \
     --prefix "$HOME/TTO-Web" --service system --mode follow \
     --active-descriptor /approved/local-publication/active.json
   ```

   默认 Linux system 服务使用当前非 root 用户，仅安装 unit 时 sudo；安装器 enable/restart 后核对 MainPID 与 59009 health PID。仅本地候选检查用 `--service none`，不注册系统服务。升级保留已有 `web.json`；模式参数只初始化新配置，改旧配置前备份并明确核对。

2. **选择来源。** 已有 collect/field owner 时跟随显式本地 publication descriptor；follow 不接管外部生产者，停 Web 不停它。没有其他 owner 且已批准只读观察时，可用 `--mode observe --observation-config /approved/native.json --observed-device <已核实设备ID>` 初始化新 prefix。observe 使用原共享锁，冲突时等待处理，不抢占、不 kill。正式 field 入口仍须原授权/绑定；不把现有采集自动改成新的实验。

3. **确认服务与页面。** `systemctl status tto-web.service`；`journalctl -u tto-web.service -n 50 --no-pager`；打开 `http://127.0.0.1:59009/`。远程访问需安装时显式 `--access lan --bind <主机地址> --allowed-origin http://<主机地址>:59009`，口令在 prefix 的 600 权限文件；不放 URL。59009 被占用应排查拥有者，不终止未知进程。

4. **核对监看含义。** 顶栏 Web 连接与设备有效性分别看；检查 run/epoch、数据年龄和剩余资格。C 的 Ts/E 为模型估计；D 上部为历史成熟配对，下部为当前 HOLD 三点。暂停只冻结画面，后台继续；恢复用最新合格快照。RPM“未确认”、未登记任务、无合法曲线/需求 provider 都允许为空，不能补零。

5. **经安排的断源恢复与资源核验。** 源失效应撤下当前值/动效/未来参考/建议；SSE 仍连接也不延长资格。observe 用完原每轮十次连接预算后，收完旧轮并按 1–30s 退避重取锁，恢复创建新 run；授权/配置/处理失败或 STOP 不重启。follow 只重连发布者。核对事件不串过程、标签按源窗结算，并以 N305 当前进程 CPU/RSS 单独记录；本机 rc2 120s 短测和旧身份 30min 均不能替代现场结果。

**停止 / 回滚**　`systemctl stop tto-web.service` 停自己的 Web/observe；follow 的外部生产者另按原流程停止。回滚：`python tools/install.py --prefix "$HOME/TTO-Web" --service system --rollback`（需存在 previous）；仅卸载 Web unit 用 `--uninstall-service`，独立 prefix 与原数据保留。
