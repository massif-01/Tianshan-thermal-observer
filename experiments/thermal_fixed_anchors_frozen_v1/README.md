# 首轮fixed-anchors冻结模型离线对照

先读`results/TTO-首轮fixed-anchors冻结模型对照报告.md`（作者目录中为`runs/final/`）。这是2026-10-19唯一run `5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3`的冻结比较，没有模型训练、设备动作或控制收益结论。

独立证据包的根目录就是本README所在目录，不依赖作者绝对路径。`vendor/src`逐字节复用现场身份对应的封存原生处理器、I02和状态计算源；`inputs`包含本轮原始观测、现场状态、阶段事件、原CSV/规范化原行、时钟照片/附注及来源身份。原始远端tar和历史ZIP不递归打包，索引和SHA仍保留。完整199项入口及7项native索引已在作者机器核对；包内只带重放所需当前run成员，而非原生旧评分/请求响应全文。

`spec.json`和`design-freeze.json`冻结于评分前；阶段交界细分另标首次结果后的描述性诊断。`prepare.py`只供作者首次从本地原件准备，独立复跑不执行它。不要把包内旧路径或配置中的设备URL作为访问指令。

使用已有、具备`requirements.txt`所列库的Python环境：

```sh
python verify.py
python rerun.py --output /tmp/tto-fixed-anchors-replay-new
```

输出目录必须不存在；程序不会覆盖原结果，数值回放时显式禁止socket连接。完整图文重建可加`--figures`，需Matplotlib及中文字体；作者使用macOS STHeiti，Linux可用Noto Sans CJK。不要求用户安装USB/串口驱动，也不需要网络/设备凭据。

`verification/independent-replay.json`记录全新目录从包内输入重跑的对比。科学JSON/JSONL应逐字节一致；`environment-resource.json`含机器/资源时间，`figure-generation.json`含字体路径，测试日志含耗时，不要求这些环境产物逐字节一致。

- `results/`：逐点状态、质量、A-long、A-roll/B-HOLD、共同集合SHA、自有覆盖率、表面时间情景、图表和报告。
- `verification/`：测试、独立重跑、受保护原件、图表目检回执；`execution-attempts.json`保留两次实际执行及首次结果SHA，首次与正式科学结果相同。
- `new-research-code.patch`：只新增独立研究代码、配置、冻结源副本及说明；不含原始数据，不修改生产软件。
- `SHA256.json`：包内所有有效成员的字节/SHA（索引自身除外）。外部交付SHA另列，不作自我哈希。

CH1为局部鳍片接触温度；未成为状态/参数/控制输入。−3/−4秒是假定网页为原生UTC时钟的情景，不是校准结论。Ts真值、探头响应、绝对时钟误差仍未验证。本次工作到离线复审停止。
