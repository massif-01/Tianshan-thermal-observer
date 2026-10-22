# 中等负载测试工具

安装入口 `tto-midload` 默认仅打印离线计划并核对本地安装身份；`--help`、`--plan`、`--dry-run`不建网络会话，不读取headers文件。显式 `--live` 才可能连接配置目标；本轮仅自建loopback测试过协议和缩短的排程集成，真实设备未执行。

计划、预算、健康准入、停止和人工回退见包内 `docs/TTO中等负载测试操作卡.md`。公共 `plan.example.json` 不包含私有地址或凭据；私有目标仅在本地候选包 `site/local-midload.json`。请求工具沿用已有OpenAI兼容接口，针对真实记录中的SSE协议实现DONE/EOF区别；不把首数据行等同于首内容，不把客户端结束等同于GPU计算结束。

离线复核（安装TTO 0.2.4和现有requirements-locked.txt后）：新增R2测试实际调用安装生成的入口，需要把 `TTO_MIDLOAD_INSTALLED_PREFIX` 设为该安装prefix，把 `TTO_MIDLOAD_LEGACY_SOURCE` 设为真实0.2.2源码的src目录。本次返修证据包已提供旧源副本和完整复跑命令；不得用虚构模块替代旧源，也不要把未安装入口的环境当作R2通过。

```sh
python -I scripts/thermal_trials/run_midload.py --plan
python -m pytest -q scripts/thermal_trials/tests experiments/thermal_identification_prep_v2/tests
```

生产回归单独运行：`python -m pytest -q tests/test_polling_schedule.py tests/test_network.py tests/test_failures.py tests/test_config_storage.py tests/test_quality.py`。旧测试用 `from conftest import …`，不要将生产测试和runner的同名conftest强行合成一次pytest进程。网络测试使用自己的loopback服务，注入时钟测试快进整轮，不向真实接口发预试题。
