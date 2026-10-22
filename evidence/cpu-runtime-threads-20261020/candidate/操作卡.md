# cpu.3操作卡：当前只交回复审

当前候选只完成本地验证，没有N305安装或现场能力通过；没有12请求许可。不要复制旧许可、旧command或把下列模板现在执行到设备。

1. 复审核对cpu.3 wheel、50项清单、8处运行文件增量、threadpoolctl3.6.0纯Python wheel及SHA；原生TTO、源脚本、SSH、有界停止、I-02、热模型、observer-spec、活动候选和计划原字节保留。生产环境不升级NumPy/SciPy。
2. 等用户下一次明确批准独立安装/只读源准备/一次60秒记录后，使用Linux x86_64 CPython3.10原解释器与旧20个锁定依赖，组装新的wheelhouse，仅加入cpu.3和threadpoolctl3.6.0；原安装器安装到全新prefix。保留cpu.2和基础解释器，不热改或重启源服务。
3. 运行新prefix的`tto-cpu-pilot verify-install --target --thread-policy-output NEW/verify-thread-policy.json`。这只是该验证进程；现场运行还必须自己保存同PID回执，不能拿这份替代。
4. 通过安装检查后，准备全新capability preview/command/binding/源只读许可；执行方式仍为`tto-cpu-pilot capability --config CONFIG --binding BINDING --output NEW_RUN --allow-network`。入口自行在数值导入前覆盖冲突线程环境为1，并核验实际NumPy/SciPy池；不需要聊天里手工加env才有效。数值策略无法确认时在网络前拒绝，失败回执位于`NEW_RUN.startup/thread-policy.json`；不在原目录重试覆盖。
5. 同一真实进程的`NEW_RUN/thread-policy.json`必须verified=true，PID与launch/summary时钟PID一致；实际库路径、两个后端、线程池、版本/环境均有记录。OpenBLAS之外或不可核验的后端本候选拒绝，不把环境值1当通过。不要用threadpool_limits热改提前加载的进程。
6. 仍只前30秒原生背景、后30秒旁录；接近30秒时按`docs/baseline-resource-contract.md`核最新可靠1秒CPU/RSS。超8%单核等效/128MiB，或记录未知、陈旧，旁录不启动、无重试；原生记录按有界流程保存，查看baseline-resource-admission.json。不是温度保护阈值，也不是负载许可。
7. 启动旁录后原预算/源预算、STOP、截止、撤销和自有子进程回收继续有效。inspect_capability按实际before/during/after分组；缺旁录是明确失败回执，不要求重复到绿色。
8. 现场结束后收回线程回执、基线准入、同run原生/状态、wire/arrivals、事件/stderr、resources、summary/files，按新目录离线回读与SHA核验。失败保留，交主审；不自动进入12请求，不发模型列表/推理、不训练、不改风扇/Web UI/采样/TTL。

未来组装（仅在许可后，变量使用实际新目录）：

```sh
"$PY310" scripts/assemble_wheelhouse.py --accepted-wheelhouse "$OLD_LOCKED" --candidate "$CPU3_WHEEL" --threadpool-wheel "$POOL_WHEEL" --output "$NEW_WHEELHOUSE"
"$PY310" candidate/install_candidate.py --prefix "$NEW_PREFIX" --wheelhouse "$NEW_WHEELHOUSE"
"$NEW_PREFIX/bin/tto-cpu-pilot" verify-install --target --thread-policy-output "$NEW_IDENTITY/thread-policy.json"
```

这些模板不创建现场授权；本轮到此停止。
