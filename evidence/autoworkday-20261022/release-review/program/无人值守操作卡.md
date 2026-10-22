# 自动工作日 v1：一次批准、机器自行执行（当前仅准备）

**用户无需2小时值班、22小时持续使用、YET或录像。** 当前未授权设备访问、部署或真实负载。

1. **一次批准整窗。** 填具体设备/热配置、观察主机、既有测量源/原驻留模型API、无已知其他任务的设备使用窗口、24小时上限、计划/程序SHA、最多600提交/5小时客户端在途及停止负责人。独立只读许可与负载许可分别保存；不继承旧许可。首批最多3台，各自独立会话；先首台。更短窗口需要预先冻结相应计划、标明缺失覆盖，本候选没有临场压缩或延长入口。
2. **获准后独立放置。** 保留observe.2原wheel/全部旧环境，严格Linux x86_64/Python3.10及21个锁定依赖，先`verify-install --target`。把本包程序目录放到新目录，使用同一observe prefix的Python。无需重新CPU60秒或O1/O2实验，不启动旧execute。
3. **准备新文件。** 按`configuration.template.json`填绝对路径；新registration/session、原observe preview生成的新只读grant、原模型请求配置（stream=true、sampling={}、输出256及30秒协议不变）。plan使用随包`executor/frozen-plan.json`。observe grant覆盖86280秒记录与收尾，整个批准窗86400秒，最后120秒用于停止/归档；不在窗口外继续观察。
4. **生成并填写负载许可。** `"$PREFIX/bin/python" program.py preview --config "$CONFIG" > "$PREVIEW"`，根据本次真实批准填写load_grant_template，另存`$LOAD_GRANT`。设备/config/session、计划、请求配置、程序及wheel身份精确对应，not_before/expires含时区并覆盖同窗。不要把self-owned-loopback测试标志用于设备。预览不访问网络、不产生许可。
5. **无人值守启动。** `"$PREFIX/bin/python" program.py unit --config "$CONFIG" --grant "$LOAD_GRANT" --output "$UNIT"`只生成用户服务文本，不自动enable/start。现场授权包含用户服务启用及确保该用户服务/机器整个窗口持续运行（包括远程终端关闭后，必要linger操作单独列在同一清单），再由原“模型推理监控”唯一执行方启动该服务。实际ExecStart为`program.py run ... --allow-network`，Restart=no；无需Codex或浏览器在线。禁止旁边再起自带collector的execute。
6. **自动运行。** 同一observe起点：0—2h背景；2—6h稀疏；6—8h讨论组；8—9h有限批处理；9—10h回落；10—18h长休息；18—23:30混合；末30min无新增。程序自动保存2小时检查；软件健康与负载准入分开，普通fan缺口仍失效。条件不满足暂停，连续60s停负载，观察可继续；无追赶、不自动换模型/延长。386个冻结机会不保证全部提交或固定响应时长。
7. **随时暂停/恢复/停止。** `"$PREFIX/bin/python" program.py control --output "$RUN" pause`；同窗恢复用`resume`；结束整窗用`stop`。不需逐阶段回来确认。暂停不延长期限；已提交者最多剩余原30秒自然收尾，未知结束后不恢复负载，不把客户端断开当GPU停止。不凭自身inflight=0推断整机空闲。
8. **到期/失败自动保存。** 同run的原始采集、状态/预测/成熟评分、自动检查、独立及合计资源、实际请求/归一化事件、许可/计划、退出原因和索引保留。observe归档调用受剩余窗口及最多60秒限制；磁盘/超时失败保留部分与错误，不重跑。归一化事件为同run相邻流，observe自身business_events可能仍显示unknown，不伪称已内嵌。停止服务仅清理本总控及其子进程，不重启模型/源服务或改风扇。

只读轮转、TTL、AUTO、曲线、gain、保护、冻结G2与评分合同不变。数据类型是“真实设备+自动构造工作负载”，不是自然用户全天分布。汇总时同时给总体和各阶段覆盖/尾部；本轮一个连续热过程，不自动重训。回退：停止并归档自己的新程序，保留失败记录和旧prefix，不自动重开旧观察器。
