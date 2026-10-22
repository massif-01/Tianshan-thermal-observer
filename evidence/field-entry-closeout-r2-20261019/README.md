# 收尾交付复审入口

先读《TTO-现场执行入口与诊断候选-收尾报告.md》和《一页操作卡.md》。本包是可运行软件候选和离线证据，不是现场开始许可。

- candidate/：Linux x86_64 CPython3.10离线安装器、实际wheelhouse、SHA及版本锁；拒绝已有安装目录，不动旧TTO或Conda base。
- source/：独立候选源、测试、原样复用的模型/Requester/CSV工具和配置模板。pyproject固定构建依赖；不是生产仓库补丁的自动部署指令。
- patches/：#9诊断补丁及#8投影/#10调度的局部接口差异。
- I02/：原通讯专项修正包展开件、本次6项重跑、5319行差异核对及原脚本；owner文件原字节不改。
- verification/：最终目标环境离线安装、7个一体化场景、14项入口检查、完整冻结虚拟回放、实际CLI信号/双启动/退出、有在途请求时采集退出、目标数值库兼容、2秒阶段超时和合成CSV关联。
- review-intake/、prior-accepted/：本次复审合同及已接受旧结果的有限引用。不重复装三份大历史归档。
- rollback/：旧0.2.4来源参考；不是设备侧当前备份。未来现场必须另核原路径/身份。

先运行 `python3 verify_bundle.py` 验证本包。目标容器复现方案见verification/container-reproduction.md；无需访问RM-01或运行历史全仓测试。

所有loopback端点为自己的127.0.0.1临时端口。native原日志沿用真实collect的simulated=false标记，含义是采集函数实际做了网络读取，**不代表连接了真实RM-01**；外层launch/summary和本报告均标synthetic_loopback_only，目录全部为自建测试。

含用户本地历史投影/来源片段和私有路径，仅供复审，不自动上传GitHub。没有新实测温度、模型训练或固件部署。正式下一步优先是经授权的约300秒无新增负载诊断。
