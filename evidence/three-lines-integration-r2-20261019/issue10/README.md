# Issue #10｜混合长负载R2离线准备

**准备候选，实测未执行。** 只实现独立调度/预演/只读状态消费；不实现#8估计器或#9通讯修复，不改src/tto及原采集器。`execute`入口在本版硬性关闭，现场绑定只有模板；本包不授予现场权限。

## 用法（已有Python3.10+，不安装依赖）

在本目录运行；plan/dry-run仅标准库；loopback及其针对性测试复用本地已存在aiohttp。不要把虚拟环境python软链接resolve到系统解释器。

```sh
python3 mix.py plan --profile fixed-anchors
python3 mix.py plan --profile same-plan-other-model
python3 mix.py plan --profile irregular-confirm-after-freeze
python3 mix.py dry-run --profile fixed-anchors --output /private/tmp/mix-fixed-NEW --run-id demo-fixed --command-id demo-fixed-start
python3 mix.py loopback --output /private/tmp/mix-http-NEW
python3 run_offline.py --output /private/tmp/mix-all-NEW
```

每个输出路径需新建；command-ledger按run_id与command_id分别原子占位，停止不自动重启。完整离线入口不读网络源，仅两个loopback假服务场景会建立本机HTTP。当前27项测试另外覆盖503与实际客户端超时。

## 文件与复用

- `scheduler.py`：同一个单调钟状态机供全时长虚拟驱动和缩时loopback驱动使用，工作是槽位发起窗口；自然drain后再计回落。
- `contracts.py`：同一有序本地JSONL只读消费，按as-of不读未来；只解释#8/#9提供的字段与到期时间，不重做源质量、延长TTL或计算状态。
- `fixtures.py`：明确合成的上游合同对象，未冒充#8/#9真实交付；真实接入尚待一次离线集成复审。
- `vendor/thermal_trials/requester.py`：包内0.2.4候选原字节复用SSE、usage、结束与异常语义。每槽位一个原Requester连接对象，最多四个在途；仍是一个调度/请求执行链，不是四个独立runner。
- `vendor/runtime024/`：候选wheel中原字节模块，仅供请求组件离线按正确版本导入，未安装部署；公开main基线是0.2.2，不冒充0.2.4现场身份。
- `vendor/yet_import/`：已验证的YET wrapper和通用ref.py，原字节保留；不再实现CSV解析。未来传新文件、新run及新目录，不能用旧样例常量或按曲线配时。
- `model-profiles.json`、`execution-policy.json`：历史已知配置与待确认项、调度暂停上限；不继承M/Y覆盖，不把未知MoE ID填为已就绪。
- `inputs/mix-plan.json`：用户原件；固定/打散清单原字节。seed61018010仅用于模拟请求耗时的复算，打散顺序由原明确清单冻结，不按温度挑选。
- `results/delivery-r2/`：完整预演、单一fixture流、每请求/阶段日志、假服务记录及针对性测试；全是软件证据。

## 预算和边界

固定名义2670秒；准备300+四次drain各90+清理120后为3450秒，距3600封顶150秒。不规则2640+300+360+120=3420秒，余180秒。驱动离散步进/软件开销消耗剩余预算，不延长窗口。请求上限4096、客户端并发1/2/4；原Requester协议上限30秒，低于plan给的60秒天花板。新调度暂停上限60秒只控制缺数据后的等待，不改任何源TTL，也不是重新要求连续60秒初始化。

仅虚拟/假HTTP处理器峰值不能说明GPU真实并发或热量，不能据此评价模型效果。请求数量、温区、独立rail、Tf/Ts、需求与成功PWM保持不同概念。旧Y“352段、0合法G2状态”和原异常不改。

## 唯一未来现场入口模板（当前执行会拒绝）

```sh
EXISTING_VERIFIED_CANDIDATE_PYTHON mix.py execute --binding APPROVED-NEW-RUN-binding.json
```

由模型推理监控对话作为唯一请求执行方运行，经一次#8/#9真实接口离线集成复审及独立现场授权后再开放，不能把本版关闭入口描述为已可现场运行。`field-binding.template.json`列出需要的身份/流/时钟/授权，非“等待Issue关闭”。见一页操作卡和R2报告。
