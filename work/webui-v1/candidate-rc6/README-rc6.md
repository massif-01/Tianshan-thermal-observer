# TTO Web UI 1.0.0rc6 安装与审查候选

从 review-sonnet-rc6/00-给-Claude-Sonnet-5.5-审查说明.md 开始，报告、差异、提交方案、前端接入卡和一页安装卡在同目录。
这是 rc5 的测试/schema/合同小修；后端运行逻辑与产品静态资源不变，没有合入 Sonnet 的正式前端改版。

本地离线试装只运行：

```sh
python3 tools/install.py --prefix /private/tmp/tto-web-review-rc6 --service none --access local
/private/tmp/tto-web-review-rc6/tto-web serve --config /private/tmp/tto-web-review-rc6/web.json
```

59009 无源等待，不会生成假数据。用 Ctrl+C 停止自己的进程。
服务安装默认选项会触及 systemd，本轮必须显式 --service none；不连接设备、不部署。

运行 wheel 来自 wheelhouse，candidate-identities.json 在安装前校验，PAYLOAD-MANIFEST.json 覆盖整包文件。
ZIP 自身 SHA256 和从最终 ZIP 解包安装的结果在包外交付核验回执；这两项封包后生成。
测试需自备 pytest/pytest-asyncio/jsonschema。以 TTO_WEB_TEST_INSTALLED=1 运行，确认实际导入 site-packages，不能默认跑源码冒充安装验证。
构建工具为 rc6 版本，构建同名已有 stage/wheel 会拒绝；复现应在新工作目录准备封存 rc3 对照 wheel、依赖 wheelhouse 和 evidence/self-review-rc6 目录，不覆盖既有候选。

Git 只提供方案与白名单，未提交、推送、创建 PR 或发布；须 Alfred 明确同意后再执行。
