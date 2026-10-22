# CPU旁录有限收尾 / 0.2.4+cpu.2

只完成TTO-CPU-PREP-CLOSE-v1.0测试线R2与模型线R1联合验证。cpu.1、原活动候选、热模型、旧结果保留。本轮没有真实设备连接、部署或推理请求。

运行CLI沿用`tto-cpu-pilot preview|capability|execute`。需要新的当次许可；cpu.2能力回执不能由cpu.1冒充。source/query200ms、8%CPU预算、唯一native/observer/Requester、原payload256token/30s以及6+6/1200秒均不变。

变化仅版本、cpu_pilot中的版本绑定、cpu_transport有界异步启动/清理/诊断证据，以及旧cpu_interface helper失效撤销。新活动FRAME转换只有模型线bridge，不在本目录再造适配器。

SSH mux检查1s，启动步骤合计3s；首包从真实源进程启动后最多1s。子进程TERM/KILL各等0.5s，启动任务/读流取消各最多等0.5s。这些时间均消耗原run预算，不新增期限。`Sidecar.tick`只安排任务并读状态，不等待check.wait；STOP/截止保持可响应。没有master终止或新TCP认证回退。

`cpu-sidecar-wire.jsonl`先保存原行base64/实际接收时间，拒绝行不会进入arrival；stderr每个本轮子进程最多保留4096字节并登记总字节/截断，记录阶段和退出码。只有本Sidecar创建的check/source客户端进入回收清单。

本地验证：`PYTHONPATH=src python -m pytest tests/test_pilot.py tests/test_startup.py tests/test_runtime_deadline.py`。`generate_joint_sample.py`经实际source.stream/read_cpu/utilization与receive代码、合成/proc和自建Socket.IO生成完整同run样例；不是手工模型FRAME。本轮不跑旧45分钟或12条现场工作。

最小安装交付保留新wheel与原安装器；依赖复用cpu.1已交wheelhouse。用`scripts/assemble_wheelhouse.py --accepted-wheelhouse OLD --candidate NEW.whl --output FRESH`核原字节、复制依赖、只替候选。然后用原installer在独立新prefix安装，不能写入cpu.1目录。Linux3.10真实安装核验仍应与本地主机代码验证分开。
