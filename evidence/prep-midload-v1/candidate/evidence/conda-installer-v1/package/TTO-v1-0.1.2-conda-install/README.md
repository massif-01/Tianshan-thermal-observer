# TTO 0.1.2：出厂Conda便捷安装

所有出厂N305已经预装Conda。TTO默认复用预装Conda，在独立目录创建Python 3.10环境，再安装已审0.1.2 wheel及锁定依赖。无需安装系统Python或venv；不往Conda的base环境安装TTO依赖。

下载并解压《TTO-v1-0.1.2-Conda便捷安装包.zip》，进入解压目录，在已有Conda的终端执行：

```sh
sh install.sh
```

默认目录为`~/TTO`：

- `conda-env/`：独立TTO Conda环境，Python 3.10。
- `tto`：运行入口，自动使用上述环境，无需手动activate。
- `config/local.json`：本机配置，设备地址可以稍后填写。
- `runs/`：默认记录目录。
- `installation.json`：实际解释器、Conda版本、wheel SHA、导入文件和依赖身份。

安装会核对SHA、创建环境、安装锁定依赖和非editable wheel、检查实际导入文件，最后执行离线doctor。未连接设备、启动采集、训练、后台服务或开机自启动。

安装后检查版本：

```sh
~/TTO/tto --version
```

应输出`0.1.2`。重复安装保留配置、模型和记录。如果目录是旧TTO venv安装器创建的，保留旧环境及数据，另建Conda环境并切换运行入口；不会删除旧环境。其他已有目录会被拒绝，请另选独立目录。

## 可选参数

指定安装目录：

```sh
sh install.sh --prefix "$HOME/TTO-observer"
```

预装Conda不在当前终端PATH时，明确指定其可执行文件：

```sh
CONDA_EXE=/path/to/conda/bin/conda sh install.sh
```

默认允许Conda和pip按机器配置下载依赖，不改全局channel、base包或`.condarc`。TTO环境使用Python 3.10，其他依赖保留原requirements-locked.txt版本；Conda只负责环境及解释器，TTO依赖继续由pip按已审锁安装。

完全离线安装需要提前准备两类材料：目标系统/CPU对应的Conda Python 3.10及pip缓存，以及同平台/Python的pip wheelhouse：

```sh
sh install.sh --offline --offline-wheelhouse /path/to/wheelhouse
```

`--offline`同时禁止Conda与pip访问索引。只传`--offline-wheelhouse`时，仅pip使用本地轮子，Conda创建环境仍可能需要下载。已有企业Conda缓存可通过CONDA_PKGS_DIRS指定；未指定时使用TTO目录内的缓存。缓存与wheelhouse必须匹配N305的Linux x86_64平台，不能用Mac ARM64依赖替代。

## 验证与范围

本机实际使用预装Conda 24.5.0、独立环境Python 3.10.22 / macOS ARM64验证。安装验证覆盖正常安装、重复安装保持配置/记录/模型、初始化后pip缺失重试、非TTO目录保护、离线材料缺失、wheel SHA不符、无采集run、旧venv内容保留、base元数据/解释器SHA不变及缺Conda时明确停止。

首次诊断调用conda list时，本机启用的pip互操作触发了尝试清理base元数据的警告，写入被文件系统隔离拒绝。最终检查改成直接读取SHA，并在安装进程中关闭该元数据协调行为；不修改全局Conda配置。初始诊断及最终验证分开保留。

原0.1.2 wheel、生产源码、依赖锁、R3b复审证据包和此前venv安装包均保持原SHA。此次只调整安装入口及文档。N305/Linux现场安装和真实连接未执行；不要将本机Conda验证当成现场部署证明。
