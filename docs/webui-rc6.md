# TTO Web UI 1.0.0rc6 仓库入口

项目保持在 [work/webui-v1](../work/webui-v1)，本次不移动目录、不重新构建或修改已经验证的 rc6。
[交付入口](../work/webui-v1/DELIVERY-rc6.json) · [候选目录](../work/webui-v1/candidate-rc6) · [验证报告](../work/webui-v1/review-sonnet-rc6/01-rc6小修与验证报告.md) · [安装卡](../work/webui-v1/review-sonnet-rc6/安装与监看操作卡-rc6.md) · [前端接入合同](../work/webui-v1/review-sonnet-rc6/前端接入卡-rc6.md)。

| 产物 | SHA256 |
| --- | --- |
| tto_web_ui-1.0.0rc6-py3-none-any.whl | f8a05e6107463832c1fb807dd290b2a0c2849f17d9d33ed4f2772fc207899892 |
| TTO-WebUI-v1-rc6-Claude-Sonnet-5.5-审查交接包.zip | 4d6e9eba94f388e7a0f20e32a1ec9381c22c12c6b3a4194a3ddf1e56d4d12420 |

## 当前身份与历史

rc6 后端/产品静态资产与 Sonnet 的 frontend 源目录分开登记：候选首页仍是封存 rc3 资产；frontend/ 保存了待后续集成验证的前端源文件。本次全部原样纳入 Git，不把前端源文件的存在当作已经构建或接入产品的证据。
rc1–rc5、历史 ZIP、源码副本、补丁、浏览器记录、安装候选和 wheelhouse 均保留；选择安装版本时以 DELIVERY-rc6.json 的版本与哈希为准。
历史文档里“等待复审”“未授权提交”等是封包时记录；此后 Alfred 已明确授权仓库同步与合并，本次不回写这些原件。

## 本地离线入口

从候选目录执行（需要独立 Python；此处只创建临时 prefix，不安装服务、不连接设备）：

```sh
cd work/webui-v1/candidate-rc6
python3 tools/install.py --prefix /private/tmp/tto-web-local-review --service none --access local
/private/tmp/tto-web-local-review/tto-web serve --config /private/tmp/tto-web-local-review/web.json
```

访问 http://127.0.0.1:59009/；无源等待，不生成假数据，停止使用 Ctrl+C。
已有 rc6 最终安装 wheel 的测试记录为 75 passed、8 个既有告警；对应测试日志及产物身份未改。同步不扩展 N305、systemd、真实负载、资源长稳或 Sonnet 前端接入的验证结论。
