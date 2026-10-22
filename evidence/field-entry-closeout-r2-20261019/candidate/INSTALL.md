# 独立目录安装（仅未来授权窗口或自建容器）

目标：Ubuntu22.04/Linux x86_64，CPython3.10及venv/ensurepip。使用新目录，不能指向生产旧环境。

```sh
python3.10 candidate/install_candidate.py --prefix /home/rm01/TTO-field-closeout-1 --wheelhouse candidate/wheelhouse
/home/rm01/TTO-field-closeout-1/bin/tto-field verify-install --target
```

安装器先核全部wheel SHA，创建新venv，以no-index安装，核实际导入位置和42份文件。不访问设备、不创建服务、不启动采集/推理。旧TTO和Conda base不变。现有prefix拒绝；若目标缺venv，先报告这个系统前提，不自动污染生产环境。

运行命令与当轮配置/授权字段见一页操作卡和source/examples。模式A默认300秒，且没有模型Requester；模式B只能由既定推理监控入口在另行许可后运行。任何一个模式均需明确--allow-network和当前绑定文件，preview不联网。

```sh
/home/rm01/TTO-field-closeout-1/bin/tto-field preview --config /home/rm01/tto-config.json --mode diagnose
```

actual source identity应为06d17ec5205cea268d4d42eeeb87169d3ca64c91a81acd0b4bdafe2f57e49806；native版本0.2.4，独立候选版本0.2.4+closeout.1。校验不符就停止，不要改授权文件中的SHA“适配”错误安装。

回退：Ctrl-C/本轮STOP停止自己的入口，保留目录，再使用原TTO路径。没有覆盖旧安装，所以不需要刷板或恢复风扇参数。rollback/内容仅供来源核对，不能冒称设备实际备份。
