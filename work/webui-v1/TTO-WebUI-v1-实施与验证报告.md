# TTO Web UI 1.0.0rc3 · 两项补正与交付核验

2026-10-21。此候选替代 rc2 继续交回独立复审；不是复审已通过或 N305 已验证。

前次交付确实仍是原 rc2，缺少本报告的两处补正。反复校验旧文件相同和旧测试通过，不能证明这两处已修复；此前“全部完成”的判断错误。本轮直接修改代码、构建新 wheel，并用旧版反例和新 wheel 定向结果对照。

## 新候选身份

- 版本：**1.0.0rc3**。
- wheel：`dist/tto_web_ui-1.0.0rc3-py3-none-any.whl`，**509816 bytes**。
- SHA256：`5f4c9fe5f28e8ab892c83b1309f8b91ad8d6e828489f116f17c4f67c8a35b910`。
- rc2 wheel SHA256：`d035bd24da55450f28f37bd8bc40d50c00b401e3e425632f5d67ced9f518ca70`；新旧不同。rc2 原 ZIP、报告、操作卡及失败证据继续保留，没有改名冒充新包。
- 新安装清单 122 项；运行清单 62 项，wheel 包成员 63 项（含清单），无多余旧构建 JS。
- `patches/rc2-to-rc3.patch` 是本轮源码差异；`baseline/rc2-before-supplement/` 为修前快照。
- `vendor/tto/`、`vendor/tto_field/` 在 rc2/rc3 wheel 中逐字节一致。原 `accepted-field-to-web.patch` 仍准确，无额外 native 变更。

## 补正一：凭据配置错误不能变成多轮网络恢复

根因：native 配置装载只检查 headers_file 存在；权限、JSON、header 值和禁止的 transport header 由 `tto.config.headers` 在 native 连接过程中检查。rc2 observe 只看最终 `reconnect_attempt_budget`，会把部分本地凭据错误当作临时网络结束，再启动下一轮。

修正位于 `src/tto_web/source.py`：

1. native 配置与 require_live 校验失败时，准确撤销来源并结束此 observe。
2. 在每轮 collector 创建、原锁和传输创建之前，对 orin/tianshan 两路调用原 `headers` 校验；不存储、打印或发布凭据。
3. 本地权限/JSON/字段格式/文件读取错误走明确配置终态，不进入网络恢复。每轮都重新校验，可阻止运行中变坏的文件触发第二轮 collector。
4. 原十次连接预算、采样、TTL 和 native 默认行为不变。已有 STOP、锁冲突、授权失败终态及临时网络恢复主体保留。

新增定向测试使用真实配置装载/原凭据校验，collector 启动用受控替身计数；它不是设备网络实验。覆盖 orin/tianshan 的权限、非法 JSON、非字符串 header、禁止的 Host header、缺文件，以及第一轮后凭据权限变坏。无效配置应为零轮，途中变坏只能为一轮，合法凭据可进入并正常结束一轮。

- **rc2：6 failed / 1 passed**，反例证明先前的边界确实未实现。
- **rc3 最终安装 wheel：新增 7 项 + 原停止语义与实际共享锁冲突 2 项，共 9 passed，32.91s**。
- 原真实 collect/observe/server 两种网络恢复定向验证仍通过：每轮预算 10，累计连接 10→11，新 run，不重叠持锁，STOP 后不复活。设备传输/锁是受控替身，只有等待被缩短，不是现场恢复时长成绩。

证据：`evidence/supplement-rc3/rc2-credential-counterexample.log`、`final-wheel-directed-tests.log`、`final-wheel-recovery.log`、`final-wheel/observe_recovery_result.json`。

## 补正二：D 旧预测响应不能跨 epoch 写回

根因：刷新在等待预测响应时保持 busy。新 epoch 的 SSE 快照到达后，rc2 不会立即清空 D，新的 refreshData 又因 busy 退出，predictionGroup 仍旧。此时旧响应只检查 run_id 和保存的 group，同 run 的新 epoch 就可能接收旧统计/图表。

修正位于 `frontend/src/main.ts`：

- 比较 cohort 明确包含 service/run/source_epoch/model/spec/horizon/range。
- 新快照的 cohort 改变时，立即清空 D 图表、统计、配对文案、缓存与增量游标，同时增加请求代次，使已发请求失效。
- 每次响应在修改任何 D 缓存、统计或图表前，核对完整当前 cohort、请求代次和请求序号。
- 新 cohort 的预测请求可以独立于被旧请求占用的 refreshData 发起。趋势请求也在返回时核对 service/run/epoch，避免旧刷新继续串接 D。
- 同 cohort 的断流仍保留历史配对；当前未来参考的资格撤销不变。不增加轮询或运行依赖。

真实 Chrome 定向反例使用安装 wheel 的实际 TS 构建与实际 SSE；本机测试 harness 控制 source_epoch，Playwright 延迟旧请求。保持同一 run，旧请求位于 refreshData 内，令 busy 持续；切换 epoch 后拒绝新预测查询，以免新响应掩盖旧响应写回。旧响应 summary 中注入 `777.123` 作为可识别标记，不是测得误差或预测能力。

| 核对 | rc2 | rc3 最终 wheel |
|---|---|---|
| 同 run 切换 epoch，旧响应尚未返回 | D 仍保留旧统计 | D 立即清空 |
| 释放旧响应（确认实际返回） | 新 epoch 显示 777.123 | 保持空，不写回 |
| 解除新请求故障注入 | — | 当前 cohort 正常统计恢复 |

证据：`rc2-epoch-counterexample.json`、`rc3-epoch-race.json`、相应日志和 `rc3-current-history-resumed.log`，均在 `evidence/supplement-rc3/`。截图 `output/playwright/1.0.0rc2-epoch-*.png`、`1.0.0rc3-epoch-*.png` 与 `rc3-current-history-resumed.png` 已查看。一次最初未保持 busy 的试验也保留，没有当作准确竞态复现。控制台 503 是有意阻断新 cohort 响应。

## 构建、安装与交付链

1. TS 类型检查与 Vite 构建通过；保留原大 bundle 提示，没有引入新框架或依赖。
2. 构建 rc3 wheel，根 dist/wheelhouse 各只有一个当前 Web wheel；旧 wheel 在明确的 baseline 下。
3. 使用 `--no-index` 在独立 `/private/tmp/tto-web-rc3-final` 离线安装；release `1.0.0rc3-3edc028c`。运行身份 62 项通过。
4. 后端定向测试通过 `TTO_WEB_TEST_INSTALLED=1` 和安装 site-packages 导入实际 wheel；浏览器 harness 也仅把 fixtures 目录加入路径，生产模块来自该 release。
5. 源码与 wheel 文件逐字节一致；实际浏览器服务器返回的 JS 与 wheel 中 `index--dJAhGlH.js` 逐字节一致。
6. 新 ZIP 封装新 wheel、新源码差异、新报告与新操作卡，逐项核对外层载荷哈希和安装清单，再从该 ZIP 解压内容运行独立 prefix 离线安装并核对身份。

证据：`build-rc3.log`、`offline-install.log`、`wheel-identity.json`，以及 ZIP 外的 `TTO-WebUI-v1-rc3-交付核验回执.json`（含解压后离线安装与启动结果）。ZIP SHA256 在同名 `.zip.sha256` 中；wheel SHA256 在本报告与操作卡中。未将 rc2 的 41 项历史回归重复标成 rc3 新成绩；本轮只做这两项定向补正所需验证。

## 保留与边界

R1 展示隔离、R2 质量映射、R3 当前资格撤销、R4 事件归属、R5 源标签结算及冻结数学保持。R6 只新增 owner 层本地配置校验；没有改 native collector、风扇、曲线、gain、保护、采样或 TTL。字段缺项继续真实为空。

资源方面只增加少量浏览器代次计数及低频采集轮次前的两个本地凭据校验，不加常驻服务、数据库、线程或新依赖。没有重做多轮长跑；rc2 的 120s 数字和更早 30min 数字仍仅属于各自旧身份，不能称为 rc3/N305 资源成绩。

全部验证是本机合成服务、受控替身和 macOS ARM64/CPython3.12。未连接 N305/Thor/ESP32、未部署系统服务、未启动真实推理或 CPU 补测、未训练、未推送或创建 PR。结束后关闭本轮自建服务和浏览器，等待独立复审；Linux/N305/systemd 与现场只读监看仍待另行安排。
