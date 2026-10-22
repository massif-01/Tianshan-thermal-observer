# TTO Web UI 1.0.0rc4：模型状态历史后端候选

这是本地可安装、可运行的只读后端增量候选，供独立复审。新增同采样 TJ/Tf/Ts/E 历史及共同抽样、失效缺口和完整响应身份。
首页静态资产逐字节沿用封存 rc3；Sonnet 的前端改版源码保留在原工作目录，本包不包含该未冻结改版。

离线安装（只在获准主机执行；本轮仅临时 prefix、本地 service none 测试）：

```sh
python3 tools/install.py --prefix /private/tmp/tto-web-review --service none --access local
/private/tmp/tto-web-review/tto-web serve --config /private/tmp/tto-web-review/web.json
```

端口固定 59009；无源时等待，不自动注入示例数据。本轮未连接设备或部署 systemd。
真实 follow/observe 入口及安装服务能力保留，现场启用需要另行安排。

本包包含 src/vendor、最终 wheel、离线 wheelhouse、candidate-identities.json、合同与示例、定向测试、源码差异及验证证据。
安装器先核对包内身份，再安装唯一 Web wheel；版本目录从 wheel 文件名取值，不再硬编码旧 rc3。
产品进程加载包内模块和冻结模型，不依赖开发工作目录或前端构建工具。

阅读顺序：实施与验证报告 → 前端接入卡 → 一页安装与监看操作卡 → evidence/history-rc4。
模型历史合同在 src/tto_web/contracts/model-history-contract.md；响应 schema 为 series.schema.json。
作者工作区构建入口为 tools/build_history_candidate.py，需保留的 rc3 封存 wheel 和已有离线构建环境；旧 tools/build_candidate.py 是历史流程，不用其重建 rc4。
新构建只用已有离线构建依赖，不重新训练、不下载模型、不构建 Sonnet 前端。

最终安装环境测试通过仅表示本机 macOS/CPython3.12 候选验证；不能证明 N305/Linux/systemd 运行或新首页视觉已通过。
