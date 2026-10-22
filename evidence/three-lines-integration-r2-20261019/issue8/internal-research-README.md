# Issue #8：缺测状态估计与冷启动R2

按TTO-REVIEW-R2-20261018完整执行模型线，复用旧研究，不按“只补差异”缩小任务。两个G2热状态Tf/Ts和等效边界E明确区分；θ/model.json冻结，E/状态仅用过去信息推断。原始测量、旧评分合同和Y的0状态结果保留。

本目录是独立checkout内的研究实现。主仓脏工作树、生产TTO、通讯/collector、runner、安装器、风扇和WS均未改；无真机、真实请求、部署、重训、CUDA、提交/推送或软件PR。

## 完整重跑

准备独立Python3.12研究环境、requirements.txt科学库、C编译器；绘图可用Noto Sans CJK或系统Arial Unicode。环境准备与运算分开。

~~~sh
python run_study.py --output new-independent-output
~~~

输出目录必须不存在。入口验证私有handoff SHA和冻结vendor/model，重建本地cache，先实际复现原Y严格结果，然后执行M五种预登记遮挡/未遮挡参考、已知状态合成系统、冻结候选后的Y回放、15/45/90秒A/B评价、有限测试和中文报告。所有计算CPU单线程，运算socket阻断，动态θ拟合入口禁用。

handoff含用户提供的私有原件，不能公开上传。无需设备或新数据即可独立执行。source-registration.json保留原checkout基线与输入身份；其中历史私有绝对路径只作来源证明，运行入口不依赖它们。原M/Y会话的时钟/用户override是历史事实，不继承live权限。

## 阅读顺序

- observer-spec.json、design-freeze.json：数值、先验、支持年龄、阶段门槛、mask规则和信息预算，在首个新方法评分前冻结。
- observer.py、stream.py：冻结G2顺序KF和朴素条件保持；manifest匹配native资格；真实测量和条件假设分开。
- prepare_data.py：只按时刻/事件种类制作遮挡，移除整条fan响应。隐藏值只在evaluate.py评价层使用。
- STATE-INTERFACE.md、consume_example.py：五组字段语义和#10只读消费；不提供请求调度。
- runs/final：原0状态复现、全部逐点状态/预测/内部尺度、共同集合与全量覆盖、合成真值、恢复和测试/资源、四张中文图、中文报告。
- implementation-review-fixes.json：初版完整计算后发现的静默长间隔实现修正及评价分层说明；数值设置/模型未调参，初次结果保留。

M用于开发且冻结θ历史上包含M，不能叫留出验证。Y是已分析过的开发记录；新方法没有真实Ts答案，没有外部温度/时钟拟合。真实局部鳍片表面不等于Ts。内部协方差不是校准95%区间，tracking不是现场安全或发负载权限。

最终证据包同时提供代码patch、来源/SHA、公开测量资格与条件状态分开的接口、独立重跑回执。交独立复审后停止；#9/#10各自完成所属离线工作，现场另行授权。
