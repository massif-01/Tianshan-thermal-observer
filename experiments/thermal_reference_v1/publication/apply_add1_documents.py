"""Limited ADD1 amendment to the same docs PR; no Issue/PR creation here."""
from pathlib import Path
import json
import re
ROOT=Path(__file__).absolute().parents[1]
DEC='| DEC-020 | 主参照采用已购YET-610L+K型探头的固定表面连续CSV；人工/红外为备用 | 用户ADD1确认已购仪表与耐温聚酰亚胺胶带；不等于现场/响应已验证；通用映射先用合成数据，真实格式待1～2分钟样例 |'
OLD_ROW='| 外部参照工具 | 人工打点/迟录、图像关联、通用导入、时钟对齐、固定提醒与零测温报告已完成本地离线验证，待复审 | 本PR不发布软件；没有新外部读数，仪器/固定测点未确认，物理对应未验证 |'
NEW_ROW='| 外部参照工具 | 连续CSV通用导入、人工/红外备用、独立时钟与事件、冻结对照和零测温报告已本地验证，待复审 | 已购YET-610L/K型探头与聚酰亚胺胶带；真实CSV映射待样例，固定接触/现场测温/物理对应未验证；本PR不发软件 |'
ACTION='''本轮记录/导入/对齐及固定事件提醒软件已经本地实现并完成离线验证；ADD1将YET-610L接触式连续CSV作为默认路径，人工/红外和稀疏提醒保留备用。新软件仍在独立研究目录等待复审，未随文档PR发布；本轮不实测、不重训、不改风扇、采集器、runner准入/调度或TTL。

用户已购买YET-610L、K型探头与耐温聚酰亚胺胶带，计划同一局部表面固定、仪表独立连续记录、结束后批量导入，目标1秒保存并按实际设置/CSV核对。通用软件已完成；真实CSV列映射待1～2分钟样例；现场接触测温与物理对应未验证。开始/结束独立时钟核对、仪表采样、导出/导入分开，不能按温度贴合调时。探头移动/重贴/松脱另记事件并换会话，不按每个稀疏提醒抄读数。

外部局部表面测温**不是TTO软件、模型生成、遥测预测或持续校准的全局前置**。真实样例到后只补必要映射与回归，不重设整套工具、不以购置或照片阻塞软件。下一次现场窗口尚待另行授权；测试对话本轮暂停。'''
PARAGRAPH='''ADD1主路径为已购YET-610L配K型探头，以耐温聚酰亚胺胶带固定同一局部散热表面，仪表独立连续记录后导入原CSV。背板另设测点，接触式不要求红外发射率、反射温度或ROI；记录实际表面、固定方式与探头变化。计划1秒保存只表示采样设置，不能当探头响应标定或Ts物理验证。真实CSV未知时不猜厂商格式；配置时间/温度/单位/通道与测点映射，保留原CSV/SHA/原行号/值及异常原因；等温新行不去重，缺失不补零。相对秒或序号须明确开始锚点与间隔依据，开始/结束独立校时不看温度贴合。移动/重贴/松脱另记事件并换测量会话。连续模式只需开始记录、独立首末校时、结束与探头异常标记；既有人工/红外稀疏提醒是备用，不要求十几次抄温度。'''

def amend():
    repo=Path(json.loads((ROOT/'publication/local-checkout.json').read_text())['directory'])
    for name in ['README.md','PROGRESS.md','docs/roadmap/TTO-roadmap.md','docs/research/TTO-research-status-20261014.md']:
        p=repo/name;s=p.read_text();s=s.replace(OLD_ROW,NEW_ROW)
        s=s.replace('下一次现场窗口、仪器能力、测点和计划尚待确认；测试对话本轮暂停。','用户已购YET-610L/K型探头和耐温聚酰亚胺胶带；真实CSV映射待样例、现场接触与测温未验证，下一次现场窗口待另行授权；测试对话本轮暂停。')
        if name=='README.md':
            s+='\nADD1主参照已确定为YET-610L/K型探头固定表面接触连续CSV，人工/红外为备用；通用软件已离线验证，真实CSV映射待1～2分钟样例，现场测温未执行。已购买不等于物理对应已验证。\n'
        elif name=='PROGRESS.md':
            s=s.replace('本轮外部表面参照工具已在独立研究目录完成本地离线验证，', '本轮外部表面参照工具已在独立研究目录完成本地离线验证（ADD1：26项检查、连续CSV默认路径），')
            anchor='详见[稳定路线图]';pos=s.index(anchor)
            s=s[:pos]+PARAGRAPH+'\n\n'+s[pos:]
        elif name.startswith('docs/roadmap/'):
            s=s.replace('**文档版本：TTO-ROADMAP-v1.1｜','**文档版本：TTO-ROADMAP-v1.1+ADD1｜',1)
            anchor='### 6.2 未来跨硬件记录建议';s=s.replace(anchor,'#### ADD1：已确定的接触式连续主参照\n\n'+PARAGRAPH+'\n\n通用软件26项本地检查通过，含240行双通道合成CSV及零测温报告；真实YET-610L格式待用户1～2分钟试记录，不将采购事实写成现场验证。无USB/串口/厂商上位机驱动，也无第二TTO采集器。\n\n'+anchor,1)
            line=next(l for l in s.splitlines() if l.startswith('| DEC-019 |'))
            s=s.replace(line,line+'\n'+DEC,1)
            s=s.replace('外部测点为条件性研发支线，用户可见鳍片与背板只是候选，仪器/几何/表面条件未确认；不拆壳、不遮风道，不默认贴胶带或涂黑。','外部测点为条件性研发支线；用户已购YET-610L/K型探头及聚酰亚胺胶带，明确采用固定局部表面接触连续记录，背板另列；实际固定位置、接触/表面、仪器精度与响应待现场说明，真实CSV映射待样例。不拆壳、不遮风道。')
        else:
            s=s.replace('新增DEC-014—019。','新增DEC-014—020（含用户ADD1）。')
            s=s.replace('21项针对性测试通过','26项针对性测试通过（原21项保留并新增5项连续路径检查）')
            s=s.replace('未知仪器/表面设置不阻塞软件','已购仪器与胶带不代表现场验证，未知实际表面/接触/精度不阻塞软件')
            s=s.replace('## 来源与保管',PARAGRAPH+'\n\n合成连续CSV240行，其中239条规范化记录（238数值、1空值），1行ERR保存拒绝原因，原CSV归档SHA校验通过；无真实YET格式/现场测温验收。\n\n## 来源与保管',1)
        p.write_text(s)
    # Keep Issue builder constants consistent with the same accepted amendment.
    p=ROOT/'publication/prepare_documents.py';s=p.read_text().replace(OLD_ROW,NEW_ROW)
    a=s.index("CURRENT_ACTION='''");b=s.index("'''",a+18)
    s=s[:a]+"CURRENT_ACTION='''"+ACTION+"'''"+s[b+3:]
    p.write_text(s)
    print('ADD1 appended to the existing four Markdown documents and Issue drafting constants.')

if __name__=='__main__':amend()
