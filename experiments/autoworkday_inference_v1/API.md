# 自动工作日请求线 API v1（离线候选；实现随后交付）

入口：`runner.Runner(clock, requester, plan, admission, emit, control)`，`await runner.run()` 返回汇总字典。

clock.now()：与本次observe相同起点的相对单调秒；clock.utc()：当前UTC；async clock.sleep(seconds)：可中断的短等待，现场只用真实时钟，虚拟钟仅在tests。不得将不同主机的monotonic直接相减。

requester：唯一原样vendor/requester.py Requester实例，构造时使用同一clock；Runner绑定其emit，run拥有一次open/close生命周期（假SSE可使用预置内存session），不调用check_resident_idle/任何模型查询，准入证据由总控提供。config含已批准model/stream=True/sampling={}，messages由冻结tasks逐项设置；max_tokens=256/timeout=30不变。不构造collector/热观察器。

admission()：同步或async，返回 `{"action":"allow"|"pause"|"stop", "reasons":[...]}`；真实测量/保护/5秒确认/身份、观察器存活、独立许可均由总控验证。每秒最多一次复查；暂停持续60s停止请求线，不改变TTL，不等待聊天。前7200秒只读背景不消耗请求准入60秒等待额度；明确stop在背景也立即生效。用户pause同样不延长阶段/总窗；STOP即时停止新增，已提交请求仅允许剩余原30秒协议预算自然收尾；超时或进程被取消才取消客户端，并保留服务端结束未知。总控继续observe与否独立判断。

emit(event,row)：同步落盘回调；每个raw row包含event、mono_s、at_utc、native_run_id、observer_session_id、device_id、config_sha256、clock_domain、plan_sha256。请求行另有slot_id/task_id/当前stage、planned_submit_s与actual_elapsed_s；真实协议字段沿用Requester。`event='workload_event'` 时row是既有Adapter归一化输出，只含已到达事件和当前身份/任务类别，无未来排程/seed/计划时间；放共享事件流。其余raw事件/冻结计划仅用于请求审计，不接预测器。协议日志和normalized事件分流，不把计划当执行。

control：`runner.Control(binding=..., stop=lambda:False, paused=lambda:False)`。binding最少字段：observer_session_id、native_run_id、device_id、config_sha256、clock_domain（本次相对时钟域标识）；现场均非空并由总控许可绑定。`Adapter(session_id=binding['native_run_id'],source_clock_domain=binding['clock_domain'],observer_clock_domain=binding['clock_domain'],complete_from_session_start=True,publication_mode='live_from_source')` 在Runner内部唯一实例。测试环境明确使用synthetic身份。

冻结计划：本目录frozen-plan.json，seed=20261022；plan_sha256为去除自身plan_sha256字段后的canonical UTF8 JSON SHA256。每个slot固定planned_submit_s、5秒准入窗口latest_submit_s、块收尾截止、task及最小完成后间隔。忙碌/暂停/迟到机会跳过，不排队、不追赶；批处理十秒机会不保证十秒完成。前7200s/长休息36000–64800s/末1800s无新增请求。预算先于计划。总控只传已批准同一计划，不改观察器wheel或旧execute。

示例（接口，不是现场启动许可）：

```python
r = Runner(clock, one_requester, frozen_plan, admission, emit,
           Control(binding={"observer_session_id":"synthetic-observe",
                            "native_run_id":"synthetic-native",
                            "device_id":"synthetic-device",
                            "config_sha256":"synthetic-config",
                            "clock_domain":"synthetic-host:boot:observe-start"}))
summary = await r.run()
```

新profile前向替代旧04“必须先停observe”接续要求：observe.2持续只读，唯一请求器只用共享状态，不启动旧自带collector的execute。观察许可不包含负载许可；本次无真实负载授权。

## 实际代码与归档接法

```python
import sys
sys.path.insert(0, '/Users/massif/Tianshan-thermal-observer/experiments/autoworkday_inference_v1')
from runner import Runner, Control, RealClock
from vendor.requester import Requester
```

Requester的output目录必须为本轮新目录，clock传同一对象；Runner修改config.messages以选择已冻结任务，其他模型/流式/采样不变。Runner持有plan与绑定的副本，不接受运行中调度修改。先等真实native_run_id生成，再建立Control/Runner；晚启动仅跳过已错过机会，不能把时钟清零。父进程持有独立许可与唯一请求所有权，不并行创建第二Runner或从别处发请求。

所有raw协议行用emit(event,row)保存原字段；workload_event另存，不与raw合并去重。样例是实际代码产生的 evidence/full-day/sample-actual-emit.json，完整流与386份原样Requester响应均在同目录。绑定真实native UUID与observe session即可关联，不需要改observe.2 registration或将初始未知UUID换成假值。

如果总控因预留归档在86280秒结束observe，应令admission stop，Runner及时退出；不能等待run到86400才开始归档。此次总窗包括清理，RealClock.now仍使用原观察起点。正常暂停/STOP保留已提交请求原预算，外层终止应给最多剩余30秒自然收尾；强取消进程协程才生成request_cancel和server_end_unknown。driver_end同时记录schedule_window_completed与not_submitted_opportunities，不能把提前停止或跳过解释成全部计划完成。

本profile准入与原execute不同之处是去除本方案不使用的YET及研究模型tracking/成绩前置，由同一真实输入质量/保护/当前许可决定。真实输入TTL和5秒确认由总控原规则保留；本组件不计算或放宽。独立许可要绑定本次设备/config/session、模型/请求参数、计划SHA、时间窗与预算；observe原只读许可不升级成负载许可。
