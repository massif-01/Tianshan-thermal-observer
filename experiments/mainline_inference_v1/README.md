# 主线回归04交付：任务事件、业务覆盖与受控补充候选

1. **用户得到什么**：只读任务事件适配 `events.py`、事件/唯一执行链接口说明、自建 SSE/取消样例、历史身份与覆盖表，以及一个待批准的单路补充候选。独立目录 `/Users/massif/Tianshan-thermal-observer/experiments/mainline_inference_v1`。本目录不改现有采集器、模型、TTL、风扇或保护。

2. **实际做了什么**：读取共同00、01、05、06及专项04、README/来源说明；核对输入包SHA清单全部匹配。CPU6孤立+6连续请求计划保持暂停，旧脚本和失败证据原样保留；这不是停止/查验某个远端进程的声明。离线整理2026-10-19 fixed-anchors及2026-10-13短问答证据，区分历史身份与当前未知项。不查询模型列表、不连接设备、不加载/重载模型、不新增采集器或正式负载。

3. **证据**：`outputs/historical-identity.json` 保存历史模型根目录、context262144、原消息模板、采样默认、256 tokens/30秒、确认的4个客户端槽及原来源哈希；引擎确认为历史vLLM线索，当前版本/build未知。回放537个实际已到达的请求事件：179提交、179首内容、179协议完成，客户端峰值在途4，结束在途0；所有GPU内核起止为null。`outputs/coverage.json` 区分背景、孤立自然完成、连续、多路、回落和热机重复的历史覆盖与限制。12项离线测试通过（`outputs/verification.log`）：含原样Requester读取自建内存SSE、截断未知、取消、乱序、重复、缺事件、虚拟时间预算/上限/安全gate失效。自建SSE使用内存替身响应，无监听端口/真实网络请求。`reference/historical-protocol.jsonl` 和来源清单可独立复核。

4. **限制**：这些是历史受控工作负载，不等于新自然窗口已覆盖；长度上限完成不等于业务自然stop；客户端在途≠整机总请求≠GPU利用率≠GPU内核并行。自然任务无事件源就unknown。source/receive时钟域分离，历史回放收到时刻null。补充场景不是已现场集成软件：`supplement.py`默认只输出计划，helper复用原Requester接口并保留旧gate，仍需测试线登记profile、统一execute接入与复审；不能绕过旧formal或另起collector。模型tracking与执行资格解耦仅交最小建议，未修改旧安全合同。

5. **下一步**：交“实际安装与测试”线在observe.1汇总。自然观察唯一collector、默认零Requester；有批准的必要补充窗口时，先明确停止/归档observe，再由本推理对话接续唯一统一execute。唯一可选候选是背景300s→单路360s→回落480s，最多24请求，名义19分钟、含准备/收尾总上限25分钟，取消/未知结束不重试。不自动加测或恢复CPU12。设备/热配置/模型驻留/容量/时钟/事件源及窗口信息见 `outputs/field-checklist.json`，待批准时一次核实。本轮交接后停止，等待具体现场负载窗口批准。

离线复核（在本目录）：

```sh
python3 -m unittest discover -s tests -v
python3 events.py reference/historical-protocol.jsonl --session-id 5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3 --source-clock-domain lpmu305:580450:581592c9-4203-4cc6-817e-ed73c332431d --complete-from-session-start
python3 supplement.py
```
