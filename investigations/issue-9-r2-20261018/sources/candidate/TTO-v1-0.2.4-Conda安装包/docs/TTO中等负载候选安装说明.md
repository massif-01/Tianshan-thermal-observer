# TTO 0.2.4 中等负载准备候选

本包只提供安装候选和已验证的离线入口。N305安装、设备连接和负载均未执行；未来现场工作需独立复审通过及用户确认窗口。研究模型没有进入wheel，没有控制收益或现场放行结论。

安装沿用原Conda流程，创建 `~/TTO-midload-0.2.4/conda-env`，原TTO入口 `~/TTO-midload-0.2.4/tto`，中等负载入口 `~/TTO-midload-0.2.4/tto-midload`。后者用已安装Conda环境的隔离解释器运行同包runner，忽略旧PYTHONPATH；本包目录的兄弟模块可正常导入。离线预览同时验证版本、非editable导入路径及隔离状态，版本错误单独说明真实原因和正确入口。不安装或升级Conda base，不覆盖 `~/TTO`。安装器核对全包manifest、锁定依赖、wheel和实际导入；默认doctor为离线配置检查，不启动服务。未缓存的依赖可能需要下载；这与现场采集授权分开。

若目标机已具备Python 3.10/pip的Conda本机缓存及匹配Linux x86_64 CP310的完整依赖wheel目录，可把操作卡安装行替换为：

```sh
sh "$HOME/TTO-midload-prep-r1-r2/TTO-v1-0.2.4-Conda安装包/install.sh" --prefix "$HOME/TTO-midload-0.2.4" --offline --offline-wheelhouse "$HOME/Downloads/tto-linux-wheelhouse"
```

依赖锁与0.2.2相同。证据中证明的是开发机macOS arm64 CPython 3.10全新非editable安装与本地loopback；没有把它当作N305实测。bundle内的 `site/local-midload.json` 是本地私有配置，来源是两轮已有记录，不进入公共模板或patch。旧推理接口 `/v1/chat/completions` 支持的SSE和max_tokens字段保持；新工作块为单路顺序请求，题材为非敏感技术说明，不把字数当持续时间保证。运行时只在开始读取一次 `/v1/models`、`/metrics` 来核对驻留和无已知活动/排队任务；不自动加载模型，不重试探测，不运行第二个ESP32轮询器。没有可用的驻留/空闲证据就保留停止记录。

每条请求最多256个生成token，整轮最多256条，单条在途最多30秒。20/60/180秒是发起窗口；正常结束以SSE的DONE或完整普通JSON及finish_reason确认。EOF、timeout、主动取消均不能证明服务器停止；脚本不调用虚构取消接口，不停止服务。发起窗口内当前输入未知只暂停，窗口不因此延长；近期60秒完整输入不满足时不进入该工作块。观察到保护、失温、风扇停用、控制绑定变化等明确异常后，本轮不自动恢复。

室温可选：复制包内 `scripts/thermal_trials/ambient.example.json` 到新的 `~/TTO-midload-0.2.4/ambient.json`，填写实际进风附近读数、测点、仪表、精度和实际观察/写入UTC时刻。未知保留null。若更新侧文件，在现场命令后加 `--ambient-file "$HOME/TTO-midload-0.2.4/ambient.json"`；runner在各阶段起止归档当时侧文件，不把旧读数当新测量。记录此前是否运行过负载、结束多久及机箱状态；180/600秒背景均不代表热平衡。

输出自动生成唯一UTC目录，内含TTO原始观察、原合同质量/控制资格、轮询时序、请求协议原件、事件/请求JSONL、计划和实际时刻、候选/配置SHA、输入覆盖、停止原因及 `trial-result.zip`。服务自报时钟与主机单调钟/UTC分列。未来计划和实际任务结束均不输入预测器；本runner只采集，不训练或加载灰箱模型。

Ctrl-C只关闭本程序的任务与连接；保留所有已落盘结果。未知终止时先人工确认服务状态，禁止自动重跑。回退时继续使用原 `~/TTO/tto`，保留新目录供复核，无需改AUTO、PWM、曲线、gain、WS、天山OS或服务。
