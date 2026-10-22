<!-- TTO-REF-PREP-v1.0-status -->
2026-10-14 / TTO-REF-PREP-v1.0 + ADD1：研究目录软件本地完成，等待独立复审。

主参照改为已购YET-610L+K型探头、聚酰亚胺胶带固定同一局部表面的独立连续CSV；人工/红外及稀疏提醒保留备用。通用映射、原CSV/SHA/原行号与值、空值/ERR台账、通道/测点、首末独立时钟锚点、探头移动事件及冻结G2/QS/LP30/LP120独立对照已完成。相邻等温不去重，缺点不插补，不按温度寻优时差，不进入模型/状态/控制。

26项本地检查及20个CLI/检查调用通过；连续CSV240行双通道明确为合成，238个数值、1空值、1行ERR另留拒绝原因；原模型/既有工作树44612份文件SHA未变。**通用软件已完成／真实YET CSV映射待1～2分钟样例／现场测温未执行。** 购买仪表不是物理验证，24°C只绑定旧M。

文档首版[PR #6](https://github.com/massif-01/Tianshan-thermal-observer/pull/6)已被账号massif-01合并，merge `2155178eab40bc1e1ced1f4eef479d1051eba5d2`；本轮执行端未发起合并。ADD1补充已推同一原分支，固定commit [722d92b](https://github.com/massif-01/Tianshan-thermal-observer/commit/722d92bfca2e847052e410e2f55a28fc9aec6661)，尚未进入main；按用户要求不重复建PR。Issue正文已更新ADD1，M0—M5与历史证据保留，Issue不关闭。

本地软件patch、离线日志、连续测温操作卡及实施报告随证据包交回复审；没有设备访问、新负载、部署、模型重训或控制。下一步只需收到真实短CSV后补必要映射与回归，不启动测试对话。