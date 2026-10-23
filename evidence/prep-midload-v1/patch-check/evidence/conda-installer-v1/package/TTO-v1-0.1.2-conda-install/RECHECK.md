# Conda安装器独立验证

准备与验证平台/CPU匹配的Conda Python3.10及pip缓存、pip wheelhouse。下面入口仅在新临时目录测试，禁止Conda及pip联网，不访问设备：

```sh
python scripts/verify_install.py --bundle . --conda /path/to/conda/bin/conda --conda-cache /path/to/conda-cache --wheelhouse /path/to/wheelhouse --output /tmp/tto-conda-install-check-NEW
```

验证10类安装场景及原base元数据/解释器不变。Conda缓存验证使用conda-forge；生产安装器默认尊重机器现有channel，不修改全局channel配置。缓存必须带离线求解所需的索引及已下载Python3.10/pip原生包；pip wheels必须匹配系统/CPU/Python。包内实际测试为macOS ARM64 / Conda24.5.0 / TTO Python3.10.22，另在该Conda环境运行原88项软件回归。N305/Linux现场未执行。

SHA256SUMS为逐文件清单，未包含自身。该安装包沿用原0.1.2 wheel，不重建、不改变生产实现或模型。
