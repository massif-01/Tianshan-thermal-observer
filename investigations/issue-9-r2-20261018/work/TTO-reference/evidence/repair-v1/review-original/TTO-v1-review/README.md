# TTO v1 独立复审证据

先阅读`TTO-v1-全链路独立复审.md`。四项问题均基于本轮上传候选；没有修改候选源码。**candidate是被审原版，不是修复版；不要把本包当部署包。**

## 范围与身份

原wheel SHA-256：2498062c139b70241a42c942305e269d2c4f88bf153fe6b35ba4bc3d5299b03b。
118项作者清单匹配、18项wheel内源码/配置一致，详见results/identity-initial.json。独立54项通过、7项未跑及环境差异见results/review-scope.json。默认doctor无外联。

## 读取结果

- `results/model-probes.json`：跨run切分、M1缺字段与M0判断、旁路报告三个反例。
- `results/ws-redirect.json`：真实loopback WebSocket重定向反例。
- `results/tests-partial.txt`、`.xml`：独立原回归子集。
- `results/failure-notes.md`：夹具更正与未验证范围。
- `candidate/src/tto`、`candidate/wheels`：按原字节保留；不含修补方案实现。

## 独立重现

使用已有隔离Python环境，或新建venv。准备依赖是环境操作，不是访问设备；依赖完整的执行端优先使用candidate/requirements-locked.txt对应Python3.10。这里的已执行结果来自Python3.13.5与现有数值依赖，不能冒称锁定版本/目标机运行。

```sh
python -m pip install --no-index --no-deps --force-reinstall candidate/wheels/tianshan_thermal_observer-0.1.0-py3-none-any.whl
python scripts/check_model_paths.py /绝对路径/一个尚不存在的输出目录
python scripts/check_ws_redirect.py
```

第一个脚本完全离线，使用生产演示生成器、切分、训练、评分和报告，产生合成文件；需为重建的模拟记录留出磁盘空间。它不加载真实记录、不改变源服务，输出findings.json。第二个脚本在本机127.0.0.1创建两个随机端口的aiohttp服务，再调用候选生产session；不访问局域网设备。完成后关闭自己的服务。

两者是原候选反例记录器，不是修复后验收标准。修复者应根据报告增加明确正确结果断言；不能靠篡改反例的实质输入使测试变绿。

原回归子集复跑方式：
```sh
python -m pytest candidate/tests/test_quality.py candidate/tests/test_modeling.py candidate/tests/test_config_storage.py candidate/tests/test_failures.py -q -k 'not bounded_disconnect_storm_and_slow_api and not full_disk_stops_observer_only'
```

候选测试只访问其自己创建的loopback，仍应先读conftest和脚本。环境缺Socket.IO时不能运行完整协议项；依赖具备后应重跑作者全部61项与新增回归，而不把此子集当最终固定配额。

完整作者演示文件未重复打包；原完整ZIP由用户上传材料保留。包内checksums.sha256仅为本复审包文件身份，不把原作者的身份清单路径强行改写成新路径。可能出现审查机绝对路径，只用于证据溯源，重跑脚本不依赖这些旧路径。
