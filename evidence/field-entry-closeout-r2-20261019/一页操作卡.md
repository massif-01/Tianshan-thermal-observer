# 一页操作卡｜先短诊断，再另行决定混合轮

**当前只交软件候选和离线证据；以下是真机下一次另行授权后的步骤，现在不执行。无ESP32候选，不刷板、不重启源服务。**

1. **独立安装，旧包保留。** N305需Linux x86_64、CPython3.10及venv/ensurepip。在本交付展开根目录，用系统/指定3.10执行：

   ```sh
   python3.10 candidate/install_candidate.py --prefix /home/rm01/TTO-field-closeout-1 --wheelhouse candidate/wheelhouse
   /home/rm01/TTO-field-closeout-1/bin/tto-field verify-install --target
   ```

   安装只使用包内wheel，拒绝已有prefix，不改Conda base、旧TTO、systemd或服务。安装失败保留独立目录和日志，不能覆盖旧包。回退：先停止本候选并保留本轮目录，再使用原TTO路径；不需要刷固件或恢复曲线/gain。

2. **先准备只读配置。** 从examples/config.template.json另存配置，只填明确源端点及必要私有认证文件路径；原1/5秒轮询、2秒超时、2.5秒fan TTL不变。采样周期/证据确实未知时保持未知，诊断仍能记录，不能因此称模型已就绪。预览不联网、不打开认证头：

   ```sh
   /home/rm01/TTO-field-closeout-1/bin/tto-field preview --config /home/rm01/tto-config.json --mode diagnose > /home/rm01/diagnostic-binding.json
   ```

   当前窗口用户明确批准后，在binding登记全新command_id；authorization.command_id与之一致、action=readonly-diagnostic、explicit_user_start=true，evidence写本次授权来源。其余源码/model/spec/config SHA用预览实际结果。不能复制旧授权/旧override；不能改SHA掩盖校验错误。

3. **首选300秒无新增负载诊断。** 不需YET、不拉模型、不发推理。获得当次现场批准后仅运行一次：

   ```sh
   OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/rm01/TTO-field-closeout-1/bin/tto-field diagnose --config /home/rm01/tto-config.json --binding /home/rm01/diagnostic-binding.json --output /home/rm01/tto-runs/NEW-diagnostic --duration 300 --allow-network
   ```

   它保存原始fan/temp阶段、RTT、成功间隔、TJ/两rail/GPU/PWM/gain/斜率/预测/失温保护、估计状态、CPU/RSS和日志字节，按秒累计资格。看diagnostic-precheck.json、summary.json与native原始记录。5分钟无超时不叫根因修复。持续无法就绪则交#9按阶段证据定位，不直接耗一小时混合测试。

4. **混合轮必须另行许可，不能从诊断自动升级。** 原模型RM-01 VLM驻留且无其他任务；记录路径/量化/引擎/模板/缓存及实际1/2/4客户端槽位容量证据，权重SHA未知如实写未知。用户确认CH1同一鳍片测点、胶带固定且仪表记录；保存首锚点照片/独立主机时间对应、时区、显示分辨率和未知误差。用preview --mode execute生成**新**binding，补inference（沿用plans/model-profiles.json中原payload，max_tokens256/timeout30）、instrument.clock_start（path/sha256/command_id/timezone/display_resolution_s/uncertainty_s）、本轮fixed-anchors授权；request_actor_thread固定为既定推理监控对话。由该对话在N305启动唯一命令：

   ```sh
   OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/rm01/TTO-field-closeout-1/bin/tto-field execute --config /home/rm01/tto-config.json --binding /home/rm01/mixed-binding.json --output /home/rm01/tto-runs/NEW-fixed-anchors --allow-network
   ```

   此进程自行管理唯一collector/估计器/请求链，总控不另发API。背景300→单路360→回落90→双路270→回落240→四路450→回落120→同单路360→最终回落480秒；名义44分30秒，含准备/drain/清理最多60分钟。窗口不随暂停延长；单请求30秒，每块drain最多90秒，清理120秒。工作窗口停止新提交，允许在途自然完成；超时/不完整SSE记录服务端未知并停止后续请求。

5. **停止与归档。** Ctrl-C或在本轮输出目录创建STOP可停；保留原始文件，不自动重启。当前输入/保护/估计不合格立即暂停新请求，连续60秒不可准入则结束排程；这是调度上限，不是初始化或TTL。明确保护/模式/绑定变化立即停止后续负载。protocol.jsonl和scheduler-events.jsonl实时落盘，可监控实际阶段/首内容/请求结束与末次钟照提醒。结束附近再次对应仪表钟与N305（或Mac—N305括号），提醒停仪表、导原CSV；不重设钟、不用曲线校时。CSV晚交保留电脑侧，不重跑。用tools/attach_instrument.py在新sidecar导入并显式关联本轮UUID；原run索引不改，表面温度不用于重训或纠正状态。
