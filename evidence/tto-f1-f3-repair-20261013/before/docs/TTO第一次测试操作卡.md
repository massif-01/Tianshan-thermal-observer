# TTO 第一次测试操作卡

适用0.2.0与出厂Conda。第一次操作请先看《TTO测试者使用说明》，这张卡用于现场查命令。

## 装好软件

在解压后的 `TTO-v1-0.2.0-conda-install` 文件夹中打开终端：

```bash
sh install.sh
~/TTO/tto --version
```

版本应为0.2.0。编辑 `~/TTO/config/local.json`，填写计算模块监控服务（Orin/Thor）、TianshanOS两处真实地址。源采样周期只填已确认值，不知道就保留null；不要改风扇或源频率。

## 检查配置

```bash
~/TTO/tto doctor --config "$HOME/TTO/config/local.json"
```

离线检查不连接设备。看到 `offline_config_valid` 表示配置格式通过。

## 在准备好的现场检查连接并录制

下面两条会连接你填写的设备，分别运行，不要同时开两轮：

```bash
~/TTO/tto doctor --config "$HOME/TTO/config/local.json" --live --duration 180
```

```bash
~/TTO/tto collect --config "$HOME/TTO/config/local.json" --duration 1800 --episode "办公使用01"
```

正常使用设备即可，不额外启动负载。提前结束按一次Ctrl+C，等“本轮TTO已停止”。同一持续过程跨录制沿用同名，下一次独立过程换新名字。

## 打开报告

从终端输出复制 `run` 的完整路径，替换第一行的提示文字：

```bash
RUN="这里替换为本次run完整路径"
REPORT="$HOME/TTO/reports/$(date +%Y%m%d-%H%M%S)"
~/TTO/tto report --run "$RUN" --output "$REPORT"
xdg-open "$REPORT/report.html"
```

生成报告不连接设备。先看有效新测量、质量缺口、停止原因；没有模型成绩也可交回数据。

## 交回资料

完整run文件夹、完整报告文件夹、installation.json、填好的测试记录。不要改原始观测/预测/评分，不附认证文件。模型旁路步骤在完整说明书第8节。


新版先看报告的平台声明、GPU状态和实际控制温度来源。CURVE是支持范围；不改mode、绑定或风扇来通过资格。GPU=0合法，“不可用”不是0。旧模型只用于旧合同离线评估；现场旁路需匹配的新冻结模型。
