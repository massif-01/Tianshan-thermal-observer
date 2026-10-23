# TTO：首次诊断复审与首轮混合实测

结论：首次300秒只读诊断与closeout.2停止时刻修订接受。没有新的软件返修要求；用户另批安装/现场窗口，独立安装closeout.2并核身份后，按原fixed-anchors执行一轮。正常情况下不再重复单独300秒诊断。

- 01是证据核对与边界；02直接交原“实际安装与测试”对话。
- candidate/是原作者已核对的closeout.2 wheel，字节不变。不是完整新安装包；复用此前作者/执行方已有的依赖wheelhouse和安装器，在新准备副本换唯一候选wheel并重新列SHA。不在设备热改，不再索取历史模型资料。
- results/logs/loopback-evidence是本次独立统计与本地假服务证据，不是真机负载。
- scripts/verify_archives_portable.py可对原诊断ZIP及旧closeout.1 ZIP重新核验。
- scripts/recompute_diagnostic.py保留审查时原样执行脚本，其中/mnt/data/tto_diag_review_20261019为审查工作目录。第三方复算须映射原输入路径并使用相同候选；它只读原日志，不连接其中设备端点。不是现场启动工具。
- 170原包成员、18入口索引及7 native索引有重叠，不相加；42项运行文件与18项单元检查各有独立含义。

所有正式现场动作仍由用户本轮明确授权。主审未访问设备、部署或重训。
