# YET-610L真实同步短问答：冻结模型比较

本轮真实CSV格式/原值核对通过，得到2027条局部鳍片表面记录；冻结模型的原生合法状态为0，不能据此作G2/LP30表面胜负或Ts物理验证。原因分别是352个原生严格片段最长26.013秒，未满足原60秒初始化；仪表时钟误差界未知，严格秒级配对也不可用。没有放宽质量规则、改初态协议、拟合外部温度或借用旧M轨迹。

报告在delivery/及runs/deliverable/results/，同目录中文结果索引.html可离线查看三张图。models/是原冻结主G2、旧LS、A24动态参数；A24没有给新run强设24°C。数据角色、时钟情景及唯一背景规则在spec.json，模型生成前冻结信息在runs/deliverable/stage1-freeze.json。

## 独立重跑

使用已有Python3.12与requirements.txt列出的研究库、C编译器，在全新输出目录运行：

```sh
python run.py --archive inputs/本轮完整原始证据.zip --output 一个不存在的新输出目录
```

入口验证原ZIP SHA/CRC及255份成员，解包副本，使用与run manifest全部22份源文件SHA相同的TTO副本做原生回放，执行三模型的原60秒资格/状态生成、CSV逐行核对、全部时间情景、中文图/报告及8项测试。不会调用collector/live接口、训练或Git。只在新输出及本研究cache中写派生文件；此前停止尝试69a567d7等不在本轮输入。

代码与研究依赖未部署到N305，不修改生产依赖锁。环境安装日志是独立临时研究运行时准备；运算阶段有socket审计阻断，网络尝试0，动态拟合入口禁用。旧TTO源副本只为离线原生处理，不运行设备采集。

## 阅读关键证据

- comparison-summary.json、model-coverage.json：温度记录已取得，当前输入资格与已初始化状态分开。
- model-initialization-attempts.jsonl：三模型共1056个片段的60秒资格检查，不冒称1056次参数拟合。
- new-run-trajectory-availability.jsonl：5529条本轮模型/起点空值及原因，保留原始引用。
- states-causal60.jsonl、states-A-long.jsonl：本次数值轨迹合法为空；不存在可发布的G2/QS/LP状态。
- native-input-qualification-ledger.jsonl：5319个原始事件的资格、原temp_stale/valid/source等字段及TTL截止；执行继续政策不放宽建模。
- actual-CSV-mapping-verification.json：原CSV SHA与提取表SHA分别列，原行32—2058、2027温度与日期/时间逐行一致，1340对等温不合并。
- fixed-reference.json：驻模背景实际开始+150秒后的固定原记录，所有时钟情景沿用同一ID，不因模型不可用而换背景。
- surface-comparison-points.jsonl：0及±5/±10/±30秒全部情景、原始钟域、近似阶段归属、严格未配对标记。情景不是误差界，未选最佳偏移/拟漂移。
- source-identity.json、completion.json、tests.log、environment-resources.json：原件/模型不变、8项测试与CPU资源。原包内历史pending/失败记录原样保留，新的实际格式核对回执说明当前结果。

原始instrument run_id是本轮trial名称；研究另保存与真实TTO UUID 1ae9a7d7-bec7-4e45-a9d6-4415b4a8dece的证据绑定，不改原会话或时间。局部表面不是空气/整块均温/实测Ts；新室温未知，未复制旧M24°C。

结果不要求重跑实验。下一步只交独立复审，若讨论短控制缺口内传播状态，须另立明确诊断合同；本轮没有自行更改旧资格或初始化规则。
