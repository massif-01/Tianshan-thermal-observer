# TTO-SHORTQA-NEXT-v1.0 复审材料

先读《TTO-短问答后续核对与有限优化方案.md》。本包是本轮核对、离线对照和有限方案，未实施固件或控制修改。

## 身份与结论

- 原七工况run：929742d7-6f4d-4d80-b53e-4436d45ac12c；原短问答run：d2a7593a-e68a-4b6f-9d4d-875fafa73c02。
- 用户已纠正此前JSON的归属，确认当前Thor曲线40°C=15%；完整当前曲线见只读回执，历史字节配置仍缺。
- 唯一控制候选是增加历史额外PWM的退出许可；同温度输入的回放不能证明减少风量后的安全/噪音收益。
- 一次原工具固定网格Ridge探索已执行，全部材料都是开发资料。文件名test/test-used来自原工具，不代表新的未使用独立测试。
- 灰箱是具体辨识设计，尚未拟合热参数。

## 路径

| 路径 | 用途 |
|---|---|
| identity/ | 当前只读GET、用户纠正、软件身份、既有部署回执、命令与环境 |
| results/ | 原ZIP/原run/SSE核验、原快照复算、离线输出、窄用例与数据资格 |
| scripts/ | 本轮新增离线分析、源抽取C原型、图表与校验；无网络或负载脚本 |
| sources/ | 必要的固定参考源码、host测试头文件/stubs与外部审查数字/脚本 |
| charts/ | 3幅PNG与SVG，实测与离线假设分开标注 |
| model-exploration/ | 完整accepted序列、sealed dataset/split、一次Ridge、评价及新使用记录 |
| SHA256.json | 本包每个数据文件的字节数与SHA；清单不自包含 |

## 并列原附件

没有把历史大包递归收入新包。以下完整原附件及60项补交另交，字节与SHA见`results/original-archive-verification.json`和`results/complement-verification.json`。

1. TTO-第二轮七工况数据与分析-20261013-929742d7.zip
2. TTO-短问答实测证据包-20261013-d2a7593a.zip
3. TTO-短问答缺失60项补交-20261013.zip：从完整原ZIP提取的60项，与审查方39项并集覆盖99项。不是截断副本重压缩。

完整分享原包沿用既有脱敏版本。新派生模型来源哈希对应本机未脱敏原run；原附件中的脱敏回执和original-run-file-hashes说明这两种字节身份。数值/原引用关系保留，不用公开副本反向覆盖本机原件。

为减少重复，包内不再收录两个逐字节重复dataset：短问答使用`short-qa/exploratory-split/dataset.json`，七工况使用`seven-conditions/all-origins-dataset.json`。对应去重关系由`results/packaging-deduplication.json`登记，没有重分episode或改sealed切分。作者本机派生目录中仍保留重复原文件。

## 已执行与离线复核

实际命令见`identity/executed-commands.json`，C编译/运行参数另在`results/control-prototype-identity.json`。Ridge使用本机既有.venv Python 3.12.3、numpy 2.2.6、sklearn 1.6.1；绘图使用既有分析环境；C使用已有Apple clang及ASAN/UBSAN。没有安装或升级依赖。

复核SHA可用包内`scripts/check_delivery.py`：给出本证据ZIP；附上并列原ZIP时也会核其原清单和CRC。它仅读ZIP，不依赖私有原run路径，不做网络请求。

本轮作者脚本默认在原工作区`evidence/shortqa-next-20261013`运行，引用本机原run。复审方若用分享原ZIP重建序列，其原件SHA会因既有脱敏而不同，不能冒充作者私有原件SHA。所需固定TTO源副本在`sources/tto-reference/src`；设置PYTHONPATH到该目录即可使用对应版本的原split/train/evaluate工具。**不要重跑已经记录为使用过的评价、调参后称同一test未使用。** 检查现有sealed产物即可。

原型会在系统临时目录抽取/编译，使用原快照重建时明确假定报告新鲜与初始隐藏状态；source-extracted需求、退出许可及限速中间量是离线执行结果，不能作为现场遥测。

本轮完成后停止。审查结果不自动授权配置应用、固件实施、新实测或GitHub发布。
