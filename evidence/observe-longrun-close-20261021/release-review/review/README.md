# TTO observe.1：三线复审与长时运行有限收尾

先读01报告；完整ZIP交原「实际安装与测试」，执行02。03给原模型线/推理监控知悉，二者本轮无需新增开发。04只是修后获准现场的衔接，不授予当前部署权。

## 结论

接受模型和推理线的限定离线成果；观察软件主体可保留，但先一起修实时quality无界保留和轮转后history错序，再进入原2小时→24小时小批只读试跑。CPU支线继续暂停；候选没胜旧版不要求重训到胜出。

## 包内内容

- 01：独立复审、两个实际反例、通过项目、环境限制。
- 02：测试线唯一有限软件任务。
- 03：其他两线接受范围与停止边界。
- 04：原试跑计划的衔接，不是新的试验路线。
- results：身份、重算、测试、资源反例和本地服务回执。
- reproductions：可离线运行的两个反例脚本。
- source_excerpts：被审原件中的相关完整模块，仅供定位，不是修复补丁。
- evidence：本次自建65秒和STOP完整运行资料；全部合成/本地，无设备操作。

## 反例复验

用候选已有解释器；--package-root可指已解压的候选src，已正常安装时省略。引用你原observe证据包的一个合成native/run-*，不是访问设备。输出必须新目录。

```sh
python reproductions/reproduce_quality_retention.py --native-run PATH_TO_OWNED_LOOPBACK_NATIVE_RUN --count 86400 --output NEW-quality.json
python reproductions/reproduce_live_history.py --output NEW-history
```

前者加速一个1Hz数据日的条数，不是真的跑24小时，也不测CPU性能。`--quality-cap 4096`仅为审查机制反事实，不能作为生产修复交付。后者仅缩小本地文件chunk触发轮转，实际history命令应与关闭后同样返回17/18/19；observe.1运行中返回1/2/3。

没有附加模型权重/依赖轮子或递归打入原大历史包。原件SHA见01与results/identity.json；本包SHA256.json只绑定本次审查交付。主审未修改用户仓库/原包、未重训/部署/执行推理。
