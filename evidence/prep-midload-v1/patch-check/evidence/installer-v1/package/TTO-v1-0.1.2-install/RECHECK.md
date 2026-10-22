# 独立验证安装器

准备匹配验证系统/CPU/Python的依赖wheelhouse后，在新的临时输出目录执行：

```sh
python3.10 scripts/verify_install.py --bundle . --wheelhouse /path/to/wheelhouse --output /tmp/tto-install-check-NEW
```

脚本仅在给出的新目录创建测试安装，使用--offline-wheelhouse，不访问设备；验证安装、重跑不覆盖配置/记录/模型、目录冲突、缺依赖目录、wheel SHA失败、无采集run。结果包含实际平台是否Linux。Linux目标机验证未执行，包内日志来自本机macOS ARM64 / Python3.10.18。源码与原0.1.2 wheel及R3b审查包均未改。
