# 本轮证据包入口

先读《YET-TTO-同步短问答-归档与建模交接说明.md》。这是唯一完整新轮1ae9a7d7，不含旧M轨迹或拼接旧轮。

- remote-result/：N305本轮完整电脑侧文件，含原始TTO run、请求响应与事件、执行脚本及配置；原生与本轮执行政策分开。
- original-csv/：实际仪表原件；imported-instrument-v2/：2027条规范化记录、逐行台账、来源行号、实际映射和导入回执。
- clock-evidence/：本轮结束原照片及早于重开轮次的历史时间对应照片（明确标historical），Mac—N305括号及未测同步误差说明。
- probe-description.json：用户测点及完整性确认；authorization.json、policy.json、plan.json：本轮授权与边界。
- checks/：实际验证与历史失败记录。csv-source-unavailable.json是外置盘卸载时的历史失败，csv-source-resolved.json说明本地原件已成功导入。
- mapping/import_yet610l.py和import-tool/：局部格式映射及已审查通用导入源码；没有新的解析系统、生产修改或模型拟合。

需要独立重做格式导入时，在已有Python3.10+下，使用包内原件和包内工具，在一个全新输出目录运行：

```sh
python3 mapping/import_yet610l.py --file original-csv/26071081-20261018002850.csv --output /private/tmp/yet-independent-import-NEW --trial-id yet610l-sync-shortqa-retry-20261017T162947Z --probe-description probe-description.json --tool import-tool/ref.py
```

此命令仅离线导入，不重开TTO、不发推理、不改仪表。先前外置盘失败只建立空输出目录，该空目录不打包；不以失败目录充当有效导入。重复的computer-side-result.tar.gz下载封装不打包，完整解压内容与下载校验回执保留。旧run files.json与下载文件清单原样保留，包内SHA256.json为归档时文件身份。原始CSV未加时区/偏移，秒级严格对齐尚未证实。
