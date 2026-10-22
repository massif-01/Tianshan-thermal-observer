# TTO Web UI v1.0 · 1.0.0rc2

本候选完成独立复审要求的 R1–R6 有限修正。交付、复验和现场边界以以下文件为准：

- `TTO-WebUI-v1-有限修正与验证报告-rc2.md`
- `TTO-WebUI-v1-一页安装与监看操作卡-rc2.md`
- `candidate-identities.json`、`src/tto_web/web-candidate-files.json`
- `evidence/repair-20261021/`、`output/playwright/rc2-*.png`
- `review-20261021/` 原独立复审材料及反例

最终 wheel SHA256：`d035bd24da55450f28f37bd8bc40d50c00b401e3e425632f5d67ced9f518ca70`。

原 rc1 报告、截图、资源轮次及基线保留作历史证据。此次只做本地修正、离线安装、自建服务和真实浏览器核验；不连接设备、不部署 N305、不训练、不发真实负载、不推送或创建 PR。完成后停止，等待独立复审。

安装包带离线 Linux CPython3.10 x86_64 与本机 CPython3.12 macOS ARM64 依赖 wheel。本轮实际执行为 macOS ARM64/3.12；Linux 和 N305 实际运行须后续单独核验。业务端口固定 59009；未配置来源时保持等待，生产服务不内置演示数据。
