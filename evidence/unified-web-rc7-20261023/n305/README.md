# N305 独立安装与 180 秒短测（2026-10-24 北京时间）

**结论：安装成功，现场验收未通过。** 实时预测、Web 重启恢复与持续记录通过；正常结束后历史预测/评分查询变空。候选保留在新目录，所有本次进程已停止，59009 无监听，无常驻服务；未合并 PR。

## 实际环境与授权

- 用户确认旧24小时数据连同收尾异常保全后继续，并明确要求按指定地址登录。首次 SSH 身份不符的阻断如实保留，随后按本次独立固定公钥和用户指定登录方式认证；未改全局 known_hosts，不把密码写入证据或源码。
- 现场主机 lpmu305，Intel Core i3-N305，Ubuntu24.04.4，Linux x86_64，CPython3.10.22。旧文件/配置保留，旧服务 inactive/MainPID0/NRestarts0，安装前端口空闲。
- 新 prefix `/home/rm01/TTO-unified-rc7-20261024`：backend/ 为 observe.5 独立 venv，web/ 内另有 rc7 的独立 venv。基于已有 Python3.10 创建，不升级系统/Conda或旧环境。统一包61份材料 SHA、后端68文件及 Web68文件身份核对通过。
- 只用 `--service none --access local` 离线安装；没有启用系统服务。短测用新 session ID、新许可、新输出路径和唯一 observe，180秒，256MiB记录预算；没有推理请求、模型重训、风扇写入或控制。

## 通过的现场项

| 项目 | 实际结果 |
|---|---|
| 有界正常收尾 | 观察返回0，reason=duration，180.252秒；summary/files均存在，21份索引文件SHA核验通过 |
| 唯一采集链 | collector=1、stateful_observer=1，575 callbacks、180个有效TJ；model错误/丢帧=0，native丢帧/漏轮询=0 |
| 发布 | 575提交、575发布，丢帧/错误=0，发布线程正常退出 |
| Web断开不影响记录 | 第45秒带真实SSE订阅停止Web，0.114秒退出；等待约10秒，states字节1639347→2005604、predictions字节162288→198476，后台未退出 |
| Web重启 | 新Web进程和service_epoch，21个重启前已显示记录全部恢复；同ID的值、起点、签发、目标与模型身份不变 |
| 真实浏览器 | 经SSH本机转发访问真实N305 Web，无注入DTO；15/45/90秒显示值和ID与实际API一致，目标时间说明可见，无pageerror。见browser-live.json及live.png |
| 账本/发布终态保真 | 108个G2记录与108个评分在终态文件中逐ID一致，含102个正式阶段记录；正式已匹配15/45/90秒分别31/25/16条。不能把低负载短测成绩宣传为模型泛化结论 |
| 清理 | 310861/310862/310955等本次进程已退出，端口无监听；旧服务仍inactive，旧配置SHA未变 |

## 阻塞项：正常结束后的历史查询丢失分组

现场证明这是产品缺陷，不能以“测试脚本选错分组”略过：用全新的已安装 Web 跟随器只读恢复同一终态，也得到相同结果。

1. 停止时的最后一个记录撤销测量，产生source_epoch2；之前108条G2预测和评分都属于真实epoch1。
2. `PredictionView.update/page` 用最后帧context作为终态identity，因此终态identity=epoch2，但records仍保留108条epoch1数据，数据并未丢失。
3. Web成功同步到cursor216，缓存108条，ended=true；但snapshot选择epoch2，`State.prediction_view`按snapshot当前epoch过滤，所以15/45/90接口各返回0条，并把空分组称作synced。

定位：`experiments/mainline_observe_v2/src/tto_field/prediction_view.py:78,108`，`work/webui-v1/src/tto_web/state.py:305,324`。复现见terminal-recovery.json：cached_epochs=[1]，snapshot.source_epoch=2，三组api_records均为0。原始result.json的断言失败为(0,0)，verified-result.json保留passed=false及后续独立保真核验，没有改成“全通过”。

需要从合同上区分“运行中的当前源身份/展示资格”与“已结束观察的历史查询分组”，保留真实epoch、记录ID和评分，不把epoch改回去、不延长TTL、不从其他分组捞值伪装实时。补上真实collector结束边界经过发布、终态恢复到API的验收，再构建新版本重测。本轮没有在设备上临时改代码或增加兜底绕过此问题。

因此两项验收的结论分别为：**发布数据保真通过；页面预测实时/恢复口径通过，但终态历史口径未通过，整体现场验收暂停。**

## 资源与保全

后端179个正式资源样本：单核等效CPU均值6.98%，最高样本9.95%；RSS样本峰值80904192字节，约77.2MiB。没有本机关闭发布的对照，不能将总CPU归因于发布开销；Web资源仅有页面点读数，未保留可靠峰值，不宣称整机或长期预算通过。

本次正常会话ZIP为509523字节，SHA256 `685fe782610df2dce370d4ae72d150c72444026ce40b46a90428ec091e705d42`，N305和本地均保全，本地在 `evidence/n305-unified-rc7-20261024/short-test-session.zip`，不向PR上传原始日志。旧24小时原始数据及其缺少最终索引的结论不变。

统一候选ZIP SHA仍为 `02885de2d9e3f67681255aefa1e5ddd8ccab80b0f876fa8f7c3350cc7c89edfb`，没有原地改包；本地增加acceptance.json旁注为未通过。此次提交只更新现场证据/说明，不改运行代码，不宣布新候选可常驻。
