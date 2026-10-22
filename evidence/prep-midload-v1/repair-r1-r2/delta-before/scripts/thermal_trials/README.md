# 中等负载测试工具

入口 `run_midload.py` 默认仅打印离线计划；`--help`、`--plan`、`--dry-run`不建网络会话，不读取headers文件。显式 `--live` 才可能连接配置目标；本轮仅自建loopback测试过协议和缩短的排程集成，真实设备未执行。

计划、预算、健康准入、停止和人工回退见包内 `docs/TTO中等负载测试操作卡.md`。公共 `plan.example.json` 不包含私有地址或凭据；私有目标仅在本地候选包 `site/local-midload.json`。请求工具沿用已有OpenAI兼容接口，针对真实记录中的SSE协议实现DONE/EOF区别；不把首数据行等同于首内容，不把客户端结束等同于GPU计算结束。

离线复核（安装TTO 0.2.3和现有requirements-locked.txt后）：

```sh
python scripts/thermal_trials/run_midload.py --plan
python -m pytest -q scripts/thermal_trials/tests experiments/thermal_identification_prep_v2/tests
```

生产回归单独运行：`python -m pytest -q tests/test_polling_schedule.py tests/test_network.py tests/test_failures.py tests/test_config_storage.py tests/test_quality.py`。旧测试用 `from conftest import …`，不要将生产测试和runner的同名conftest强行合成一次pytest进程。网络测试使用自己的loopback服务，注入时钟测试快进整轮，不向真实接口发预试题。
