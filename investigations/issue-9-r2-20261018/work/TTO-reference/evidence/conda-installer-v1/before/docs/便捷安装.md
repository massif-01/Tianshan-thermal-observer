# TTO 0.1.2便捷安装

目标为N305上的Ubuntu 22.04 / Python 3.10，也可用于有兼容Python的观察电脑。安装包使用已审0.1.2 wheel，软件源码、模型和采集规则不变。

下载并解压《TTO-v1-0.1.2-便捷安装包.zip》，进入解压出的目录，在终端执行：

```sh
sh install.sh
```

脚本自动检查Python、核对安装包SHA、创建`~/TTO/.venv`、安装锁定依赖和wheel、核对实际导入文件与版本，并执行离线doctor。默认需要联网下载Python依赖；准备依赖后也可完全离线安装。

如果Ubuntu提示没有Python或venv，先安装系统提供的Python工具，再重跑：

```sh
sudo apt install python3 python3-venv
sh install.sh
```

脚本本身不执行sudo、安装系统软件或修改系统Python。Python需3.10或更高，优先使用python3.10；本轮验证用3.10.18。

安装完成后，检查版本：

```sh
~/TTO/tto --version
```

应输出`0.1.2`。安装身份保存在`~/TTO/installation.json`，实际程序位于独立虚拟环境。

设备地址可以稍后填写。配置文件为`~/TTO/config/local.json`，默认两处地址为空；程序已放好风扇、温度及Orin接口规则。记录默认存入`~/TTO/runs`。本次安装只运行离线检查，没有采集、设备连接、训练、后台服务或开机启动。

重复运行同一安装脚本，会核对并重装同一wheel，保留已有配置、模型和数据。若目标目录已有其他内容且并非本安装器创建，脚本会停止并提示改用新目录。依赖下载等步骤失败时，可处理提示后重跑。

## 自选目录与离线依赖

```sh
sh install.sh --prefix "$HOME/TTO-observer"
sh install.sh --offline-wheelhouse /path/to/wheelhouse
```

离线wheelhouse必须匹配目标系统、CPU与Python。例如目标N305是Linux x86_64 / Python 3.10，不能使用Mac ARM64的依赖轮子。

可在联网且系统/CPU/Python匹配的电脑上准备依赖：

```sh
python3.10 -m pip download --only-binary=:all: \
  -r requirements-locked.txt -d wheelhouse
```

复制wheelhouse至目标机后传给`--offline-wheelhouse`。指定此参数后pip使用`--no-index`，不访问包索引。默认完整依赖锁也含训练/测试库，但安装不会执行训练或回归。

需指定Python解释器时：

```sh
TTO_INSTALL_PYTHON=/path/to/python3.10 sh install.sh
```

## 本轮验证范围

在本机macOS ARM64 / CPython 3.10.18的全新临时目录，用预先准备的离线依赖实际验证七类结果：完整安装、重复安装保留配置/记录/模型、其他目录保护、缺离线依赖目录、wheel哈希不匹配拒绝、虚拟环境初始化中断后重试恢复pip、未创建采集run；目录含空格，启动器可直接运行。安装包解压后还会独立重跑安装验证。

Ubuntu 22.04 / N305实机安装未执行。本机没有运行中的Docker守护进程，未启动它来做Linux容器测试。该限制与测试日志如实保存。原0.1.2 wheel及R3b复审交付包SHA保持不变；本轮只是安装入口与文档。
