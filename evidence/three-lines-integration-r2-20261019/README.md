# 统一复审入口

先读《TTO-三线集成核对与实测准备报告.md》，再看《交回原负责方的问题.md》和《实测操作卡-待复审.md》。现场仍阻断，不能部署或发真实负载。

本包：三边实际报告/关键代码/patch/冻结模型和spec、23项实际接口检查、6类实际估计器假流检查、两份原字节完整Y接口、应用到独立副本的主机诊断候选、原计划和操作卡、历史Y的显式run/CSV关联参考。新增代码只在integration/；issue8/9/10保留源交付，历史验证记录不冒充本次新跑。

原三份完整证据ZIP以source-archives.json路径/字节/SHA引用；不递归装包。旧#10重复合成大流列于omitted-regenerable-streams.json，其全量在原#10 ZIP可取。source-copy-verification记录先核验后省略的复制身份。当前目录清单SHA256.json才是本包实际成员。

已有兼容Python（NumPy/SciPy）下可运行：

```sh
python verify_bundle.py
python integration/run_checks.py
python integration/check_synthetic_chain.py
```

不联网、不读取设备、不拟合。后两项重建派生结果；原封字节核验以ZIP/首次展开为准。本包没有生产安装命令。目标Python依赖等价性未现场核验，不自动安装升级。

含私人原始温度/请求/现场路径，仅交复审，不上传公开GitHub。仪表表面温度、模型Ts和TJ不是同一观测；没有由曲线形状估时或修改原CSV。
