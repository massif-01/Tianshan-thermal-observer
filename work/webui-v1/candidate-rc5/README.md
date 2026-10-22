# TTO Web UI 1.0.0rc5｜Claude Sonnet 5.5 审查交接包

先读 review-sonnet-rc5/00-给-Claude-Sonnet-5.5-审查说明.md，再读自审报告、接入卡和批准方案。

这是可安装的后端修正候选，正式首页静态资产沿用 rc3；Sonnet 新首页未集成。
只做本地审查，不连接设备、部署、真实负载、推送。

离线试装：python3 tools/install.py --prefix /private/tmp/tto-web-sonnet-review --service none --access local

启动：/private/tmp/tto-web-sonnet-review/tto-web serve --config /private/tmp/tto-web-sonnet-review/web.json

访问 http://127.0.0.1:59009/，无源时等待。Ctrl+C 停止自己的进程。
安装器核对 candidate-identities.json 后使用唯一新 wheel；包根 PAYLOAD-MANIFEST.json 核对全部载荷。
源码构建工具供作者工作区复现，需已保留 rc3 封存 wheel 和离线构建环境；现成安装不需前端工具链。
