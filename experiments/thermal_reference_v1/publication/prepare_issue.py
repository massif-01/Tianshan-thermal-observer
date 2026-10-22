"""Merge current status into the saved Issue skeleton; no remote write here."""
from pathlib import Path
import json
import re
from prepare_documents import ROOT,STATUS_TABLE,CURRENT_ACTION,replace_once


def prepare(commit,pr_url,source=None):
    old=(Path(source) if source else ROOT/'publication/before/issue-1.md').read_text()
    text=old
    text=replace_once(text,'**共识快照：2026-10-12。当前执行重点：使用已经完成的软件取得可信的真实运行数据。**',
        '**历史共识：2026-10-12｜状态更新：2026-10-14。M2已有实际灰箱辨识与对照；M3已有固定参数因果状态研究，在线参数学习、跨硬件与控制尚未完成。**')
    text=replace_once(text,'低阶灰箱状态空间模型是下一阶段重点，不以 Ridge 先达到某个漂亮分数为前置条件。',
        '低阶灰箱状态空间模型已进入实际辨识与对照，继续服务于模型生成，不以Ridge先达到某个漂亮分数为前置条件。')
    text=replace_once(text,'现在先确认目标机安装与数据入口，记录正常的待机、工作、结束与回落。第一批数据可用后，运行现有基线和 Ridge，并推进低阶灰箱候选的具体辨识方案。不要继续无限打磨 Ridge，也不要为了未来灰箱/在线学习推倒重做采集器。',CURRENT_ACTION)
    before=text.index('## 已发布入口');after=text.index('## 1. 为什么做这个项目')
    links=f'''## 已发布入口

- [稳定路线图（本轮文档候选，固定commit）](https://github.com/massif-01/Tianshan-thermal-observer/blob/{commit}/docs/roadmap/TTO-roadmap.md)
- [研究状态与证据索引（固定commit）](https://github.com/massif-01/Tianshan-thermal-observer/blob/{commit}/docs/research/TTO-research-status-20261014.md)
- [本轮仅文档PR]({pr_url})：首版已由账号massif-01合并，merge SHA `2155178eab40bc1e1ced1f4eef479d1051eba5d2`。本轮执行端未发起合并；不含新软件、原始日志或凭据。
- ADD1文档补充已推到[同一原分支的固定commit](https://github.com/massif-01/Tianshan-thermal-observer/commit/{commit})，**尚未进入main**。用户要求不重复建PR，因此不另建；已合并PR不能吸收后推提交。主Issue本正文已同步ADD1最新事实。
- [历史文档PR #2](https://github.com/massif-01/Tianshan-thermal-observer/pull/2)已合并，merge SHA `5feb66ff521551dad9dd0bd8e30e8c3c3d636eec`；[原固定版本](https://github.com/massif-01/Tianshan-thermal-observer/blob/28ed31fdc2713bb6af70c7806fdc8ef646c945dd/docs/roadmap/TTO-roadmap.md)继续保留。
- [公开L/S采集报告目录](https://github.com/massif-01/Tianshan-thermal-observer/tree/a27ddb6f41c887fd9f08d4120f98d97eed31f4d0/docs/reports)。

软件新候选只在本地交回复审。本轮没有现场测温、模型重训或风扇控制；文档发布不是软件部署或物理验证。主Issue保持开放。

'''
    text=text[:before]+links+text[after:]
    before=text.index('## 2. 当前基线：');after=text.index('## 3. 已达成的关键决策')
    history=text[before:after].replace('## 2. 当前基线：完成事实与未验证事项分开','### 2026-10-12原基线全文（历史）',1)
    section='''## 2. 当前状态与历史基线分开

已取得L/S/M三个同机Thor开发过程，G1/G2、紧凑Ridge和慢态对照已实际计算，不能再写作“尚未开始”。所有资料已分析，均为开发/探索资料，不因18条请求或6643行记录变成独立试验。

'''+STATUS_TABLE+'''

历史main基线为`a27ddb6f41c887fd9f08d4120f98d97eed31f4d0`，本次回读为PR #6的merge `2155178eab40bc1e1ced1f4eef479d1051eba5d2`；ADD1文档commit另列为未进入main。0.2.4现场过程、本地研究、新参照工具与公开状态分别登记。M的24°C只绑定M；旧E、原始日志、模型、成绩和质量规则不回写。表面测温不是全局前置，无测温时也有报告，物理对应未验证。

<details>
<summary>保留2026-10-12 / 0.1.2历史身份、哈希和独立复审（不是当前未开工状态）</summary>

'''+history+'''
</details>

'''
    text=text[:before]+section+text[after:]
    text=text.replace('| 灰箱是下一阶段重点 |','| 灰箱实际研究继续推进 |',1)
    text=text.replace('下一次现场窗口、仪器能力、测点和计划尚待确认','已购YET-610L/K型探头与聚酰亚胺胶带，真实CSV映射待样例、现场固定接触与测温未验证；下一次现场窗口待另行授权')
    def milestone(start,end,body):
        nonlocal text
        a=text.index(start);b=text.index(end,a)
        text=text[:a]+body+'\n\n'+text[b:]
    milestone('### M1 —','### M2 —','''### M1 — 实测数据与固定参照：已取得开发资料，持续维护

- [x] 已取得TTO候选身份、Orin/Thor及AUTO/CURVE实现与0.2.4过程核对；保留对应软件与现场资料。
- [ ] 其他源服务/固件的完整运行身份及最终确认按缺项继续补齐，不将TTO身份等同于所有来源已确认。
- [x] 已取得L/S/M三个完整开发过程，包括背景、长负载、短问答、中等块及回落；保留质量缺口、原/override与恢复记录。
- [x] 实际运行B0/B1、Ridge与灰箱对照，保存坏例、覆盖和原始引用；不是只给均值。
- [ ] 冻结规则/候选后的新完整过程确认、目标主机长期资源及其他未获实证范围继续维护；旧开发资料不改称全盲终验。

M1资料已支持进入M2，Ridge不胜出不阻塞灰箱；不继续机械重套60/20/20或要求“再凑五次”才允许研究。''')
    milestone('### M2 —','### M3 —','''### M2 — 灰箱候选与模型生成：已有实现，解释与适用范围继续验证

- [x] G1单状态与G2快/慢两状态已经实际拟合；保留原约束、六初值、全部尝试及训练目标择优记录。
- [x] 首轮主拟合36次、第二轮42次、L/S/M角色及冻结模型已保存，不重新搜索或覆盖旧成绩。
- [x] 两rail、成功PWM、等效E、潜在Ts与输出Tf分清，功率不任意相加，不将gain当物理冷却输入。
- [x] A-long/A-roll与B分开，HOLD/RELAX30固定报告，15/45/90各自判标签，同集合对照紧凑Ridge和简单基线。
- [x] 参数/初态/残差/共线/热点/数值及快慢状态对照已有证据，包括不能胜出的情况。
- [ ] 独立确认、适用范围与实际生成/校准成本继续验证；绝对物理解释未验证，但局部表面传感器不是模型生成/遥测预测的全局门槛。

现G2输出仍是Tf对TJ的估计，短峰误差保留；Ts未测，不是实测TTP/热容。正常推理的GPU与VDD_CPU_SOC_MSS共同活动可有组合预测价值，独立贡献及域外迁移另验证。''')
    milestone('### M3 —','### M4 —','''### M3 — 状态估计已有离线研究，持续参数学习未实施

- [x] 固定θ的过去60秒因果慢态、QS及同G2的LP30/LP120对照已计算，M三块未按工作边界重置慢状态。
- [ ] 周期批量重估计/递归参数更新等候选尚未实施，不能把状态变化或固件controller_gain变化当TTO在线参数学习。
- [ ] 完整记录到达顺序及批准窗口旁路的参数学习流程待做；必须先预测、后评分、再允许答案参与后续更新。
- [ ] 候选与稳定版比较、每次更新范围/版本、验收/拒绝/启用理由及回退待实施。
- [ ] 质量不足/异常时冻结学习，保留有效观测及原因；未定遗忘/恢复规则不宣称已完成。
- [ ] 变化后恢复、稳态/欠预测、遗忘代价、CPU/RSS与校准成本仍需对应验证。

RLS、遗忘因子、窗口重估计与卡尔曼类方法是待比较候选，不要求全部采用。外部表面参照可帮助部分物理解释，不永久阻塞在线参数校准主线；通过未来更新验证也只获得观察模型身份，不自动获得调速权。''')
    text=replace_once(text,'讨论范围包括Orin/T234和Thor T4000/T5000。它们是待验证平台，不是已经完成的跨硬件数据集；共同外部热接口不证明内部参数一致。',
        '讨论范围包括Orin/T234和Thor T4000/T5000。Orin/Thor字段适配已有实现，但跨模组模型有效性和迁移仍待验证，不是已完成的跨硬件数据集；共同外部热接口不证明内部参数一致。')
    text=replace_once(text,'### M5 — 工程交付与社区复现\n',
        '### M5 — 工程交付与社区复现\n\n- [x] 已有公开源码、L/S采集报告和路线文档；本轮仅文档PR补研究状态/证据索引，新软件仍先本地复审。\n')
    text=replace_once(text,'未来灰箱必须说明与哪组共享同一起点', '灰箱对照已按实验合同登记；后续新增候选仍须说明与哪组共享同一起点') if '未来灰箱必须说明与哪组共享同一起点' in text else text
    anchor='## 7. 待数据回答的问题，不现在拍脑袋定死'
    text=replace_once(text,anchor,'''补充当前研究合同：A-long为前缀后不吸收TJ的自由响应；A-roll允许实际未来输入但不读未来TJ反馈；B只用预测时已到达信息，HOLD/RELAX30分别报告。按TTO-EVAL-AVAIL-v2.0保留未来辅助缺口下的温度答案，正常/辅助缺口/已观测异常或变化/未分类分别列，未知不写正常。每个时距独立资格；来源/集合不同不混排，旧分数不覆盖。

局部参照只用同位置/同会话一次预登记背景比较温升和回落，不按阶段重设参考、缩放或寻优错时；未知精度不填0，稀疏点不冒充连续峰值。鳍片局部红外、背板、空气与环境备注分开；不从伪彩颜色造数值，不默认裸金属发射率0.95。

'''+anchor)
    text=replace_once(text,'## 9. 当前下一步\n', '''## 8.1 本次追加决策（2026-10-14）

DEC-014记录L/S/M与实际灰箱进展；DEC-015分开TJ/Tf/Ts/需求/动作及平稳目标；DEC-016分开状态估计与参数学习；DEC-017将局部测温改为条件性支线而非全局门槛；DEC-018确认可见鳍片局部表面/背板/空气不同；DEC-019固定事件提醒、采样/打点/写入分离及漏测不延长。完整理由在稳定文档，不另建竞争路线图。

## 9. 当前下一步
''')
    old_action='''**当前不是再选一次模型架构，也不是继续修已关闭R3b。使用v1取得第一批真实、可核对的数据；Ridge作参照，灰箱进入重点研究。**

收到真实结果后更新本Issue，不另开一份相互矛盾的总路线图。若当前仓库已有更晚的实测或版本，先合并事实与链接，再调整勾选项，保留本快照的证据边界。'''
    text=replace_once(text,old_action,CURRENT_ACTION+'\n\n本轮到此停止等待独立复审，不自行部署、实测或训练。')
    add1='''### ADD1：已确定的接触式连续CSV主参照

用户已购买YET-610L、K型探头与耐温聚酰亚胺胶带，计划由用户固定感温端于同一局部表面，仪表独立连续记录后导入原CSV。它是surface_contact，不是出风空气、整块均温或直接测得Ts；背板另测点。接触式不要求红外发射率/反射温度/ROI，人工打点、红外与稀疏提醒保留备用。

通用时间/温度/单位/通道→测点映射、原CSV/SHA/原行号/原值、异常台账与实际间隔核对已本地实现。相邻等温不去重，缺失/异常不补零；相对秒或序号必须有独立开始锚点及间隔依据，首末校时不按温度贴合选择偏移。采样、开始锚点、导出、导入分别保存；计划1秒不代表探头响应已标定。移动/重贴/松脱另记事件并换会话。连续操作卡只提醒开始、独立首末校时、结束与探头变化，无逐点抄读要求。

本地26项针对性检查及20个CLI/检查调用通过；连续数据240行双通道均明确为合成，1行ERR留拒绝原因、1个空数值保留，不宣称真实YET格式验收。**通用软件已完成／真实CSV映射待1～2分钟样例／现场测温未执行。** 已购买不等于物理验证，样例到后只补必要映射与回归。DEC-020在同一稳定路线图追加；没有USB实时驱动、第二采集器、设备请求、重训或控制。

'''
    text=text.replace('## 9. 当前下一步',add1+'## 9. 当前下一步',1)
    if '<!-- TTO-REF-PREP-v1.0-status -->' not in text:text+='\n\n<!-- TTO-REF-PREP-v1.0-status -->\n'
    (ROOT/'publication/issue-body-ready.md').write_text(text)
    for i in range(6):assert f'### M{i} ' in text
    for token in ['bfe55c967c017c45ebe0287a886eb17e30d7e44a0ca7af01d385fd4ad97ab465',
                  '92aed2e4a943b9cc615f3c969081ce4c05a934e0fed26322f443a530f83b5684']:
        assert token in text
    print('Prepared Issue #1 body, preserving old baseline, M0-M5 and actual links.')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--pr-url',required=True);p.add_argument('--source',type=Path)
    a=p.parse_args();prepare(a.commit,a.pr_url,a.source)
