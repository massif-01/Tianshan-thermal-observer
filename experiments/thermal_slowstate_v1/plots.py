"""Four static scientific figure classes. Reads derived files, never recomputes fits."""
from pathlib import Path
import json
import os
import sys
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager

ROOT=Path(__file__).absolute().parent
OUT=ROOT/'figures'


def read(path):return json.loads(Path(path).read_text())
def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x]


def setup():
    for font in ['/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                 '/System/Library/Fonts/STHeiti Medium.ttc',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if Path(font).exists():
            fontManager.addfont(font)
            plt.rcParams['font.family']=FontProperties(fname=font).get_name()
            break
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,'axes.titlesize':12,
        'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.17,
        'figure.facecolor':'#fcfcfd','axes.facecolor':'#ffffff','savefig.facecolor':'#fcfcfd',
        'svg.fonttype':'none'})
    OUT.mkdir(exist_ok=True)


BRANCHES=['STATE-G2','STATE-QS','STATE-LP30','STATE-LP120']
NAMES={'STATE-G2':'G2过去60秒慢态','STATE-QS':'无慢记忆（代数状态）',
       'STATE-LP30':'30秒因果滤波','STATE-LP120':'120秒因果滤波'}
COLORS={'STATE-G2':'#b3412e','STATE-QS':'#9b9283','STATE-LP30':'#1b7e91','STATE-LP120':'#7256a3'}


def window(rows,run,start,end):return [r for r in rows if r['run']==run and start<=r['wall']<=end]


def trace(ax,rows,key,start,label,color,style='-',segment=True):
    x,y=[],[]
    prev=None
    for row in rows:
        if prev is not None:
            broken=(row.get('segment')!=prev.get('segment')) if segment else (row['t']>prev.get('source_valid_until',prev['t']+5))
            if broken:
                x.append(np.nan);y.append(np.nan)
        x.append(row['wall']-start);y.append(key(row));prev=row
    ax.plot(x,y,style,label=label,color=color,lw=1.6)


def unavailable(ax,ledger,run,start,end):
    for r in ledger:
        if r['run']!=run or r['ordinary_available']:
            continue
        a=max(start,r['wall']);b=min(end,r['wall']+r['duration_s'])
        if b>a:ax.axvspan(a-start,b-start,color='#a0a5ae',alpha=.1,lw=0)


def events(ax,runs,run,start,end):
    r=next(r for r in runs if r['run']==run)
    if run=='L':
        ranges=[p for p in r['phases'] if p.get('macro')=='work']
    else:ranges=r['requests']
    for ev in ranges:
        a=max(start,ev['start']);b=min(end,ev['end'])
        if b>a:ax.axvspan(a-start,b-start,color='#deb46b',alpha=.12,lw=0)


def pwm(ax,ledger,run,start,end):
    rows=window(ledger,run,start,end)
    x,y=[],[]
    last=None
    for r in rows:
        if r['event']!='original_observation':continue
        if r['fast_status']['fan_ref']==last:continue
        last=r['fast_status']['fan_ref']
        x.append(r['wall']-start)
        y.append(r['fast_status']['successful_PWM_percent'] if r['fast_status']['successful_PWM_percent'] is not None else np.nan)
    ax.step(x,y,where='post',color='#425466',lw=1.3,label='成功PWM原快照（现场参考）')
    ax.set_ylabel('实测PWM（%）')


def finish(fig,name,caption):
    fig.savefig(OUT/f'{name}.png',dpi=165,bbox_inches='tight')
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)
    return dict(name=name,png=f'{name}.png',svg=f'{name}.svg',caption=caption)


def main():
    started=time.perf_counter();setup()
    data=read(ROOT/'sources/registered/data.json')
    runs=data['runs'];accepted=data['accepted']
    long=[r for r in lines(ROOT/'results/states-A-long.jsonl') if r['model']=='primary']
    causal=[r for r in lines(ROOT/'results/states-causal60.jsonl') if r['model']=='primary']
    origins=lines(ROOT/'results/four-state-origins.jsonl')
    demand=lines(ROOT/'results/normal-demand-origins.jsonl')
    ledger=lines(ROOT/'results/fast-status-and-demand-ledger.jsonl')
    metrics=read(ROOT/'results/temperature-metrics.json')
    s=next(r for r in runs if r['run']=='S');m=next(r for r in runs if r['run']=='M')
    sparse=next(r for r in s['requests'] if r['id']=='S02')
    continuous=next(p for p in s['phases'] if p['id']=='continuous')
    mid=next(p for p in m['phases'] if p['id']=='M60')
    cols=[('S',sparse['start']-15,sparse['end']+80,'稀疏短问答 S02'),
          ('S',continuous['start']-15,continuous['end']+25,'连续短问答全组'),
          ('M',mid['start']-20,mid['end']+100,'中等工作块 M60（实际约65秒）')]
    figs=[]
    fig,axs=plt.subplots(4,3,figsize=(17,11),squeeze=False)
    fig.suptitle('图1｜TJ、原定义Tf、真正Ts与现场PWM分开读',fontsize=19,y=1.015)
    for col,(run,start,end,title) in enumerate(cols):
        ar=window(accepted,run,start,end);lr=window(long,run,start,end);cr=window(causal,run,start,end)
        trace(axs[0,col],ar,lambda r:r['values']['tj'],start,'实测TJ','#202d3c',segment=False)
        trace(axs[0,col],lr,lambda r:r['Tf'],start,'A-long Tf：TJ估计','#b3412e')
        trace(axs[1,col],lr,lambda r:r['Ts'],start,'A-long同次传播的潜在Ts','#466ba7')
        trace(axs[2,col],cr,lambda r:r['Ts'],start,'过去60秒因果Ts','#137d72')
        pwm(axs[3,col],ledger,run,start,end)
        axs[0,col].set_title(title)
        for row in range(4):
            ax=axs[row,col];unavailable(ax,ledger,run,start,end);events(ax,runs,run,start,end)
            ax.set_xlim(0,end-start);ax.legend(fontsize=8,loc='best')
            if row==3:ax.set_xlabel('相对本窗起点（秒）')
        for row,label in enumerate(['TJ / Tf（°C）','A-long Ts（°C）','因果Ts（°C）']):axs[row,col].set_ylabel(label)
    fig.text(.5,-.008,'各面板独立纵轴；灰色：普通状态/需求资格不足，实测TJ仍保留；浅黄：请求执行。因果Tf锚到当前TJ，未当预测得分。',ha='center',fontsize=10)
    fig.tight_layout()
    figs.append(finish(fig,'图1-四种量的对应',[
        '横轴是每个放大窗口内的秒数，纵轴分别是实测TJ/模型Tf、自由响应Ts、因果Ts的°C，以及另轴的实际成功PWM快照%。',
        '主要看短TJ峰仍然存在、原Tf仍会欠峰，而真正Ts取自第二状态；连续组后半灰区明确断开，M工作块未重置。',
        '不能把Tf欠峰改名成测准散热体，也不能把Ts或另轴PWM解释成新的安全风扇指令。']))

    fig,axs=plt.subplots(3,3,figsize=(17,10.2),squeeze=False)
    fig.suptitle('图2｜慢态的价值：看共同标签的温度误差，同时看简单滤波',fontsize=18,y=1.015)
    for col,run in enumerate(['L','S','M']):
        rr=[r for r in origins if r['run']==run];start=min(r['wall'] for r in accepted if r['run']==run)
        for b in BRANCHES:trace(axs[0,col],rr,lambda r,b=b:r['states'][b],start,NAMES[b],COLORS[b])
        end=max(r['wall'] for r in accepted if r['run']==run)
        unavailable(axs[0,col],ledger,run,start,end);axs[0,col].set_title(f'{run}记录｜潜在状态，无Ts真值')
        axs[0,col].set_ylabel('状态来源（°C）');axs[0,col].set_xlabel('距本轮记录起点（秒）')
        axs[0,col].legend(fontsize=7,ncol=2)
        for row,kind,title in [(1,'A_roll','给定真实未来输入：A-roll'),(2,'B_HOLD','仅当前输入保持：B-HOLD')]:
            ax=axs[row,col];ns=[]
            for bi,b in enumerate(BRANCHES):
                values=[]
                for h in [15,45,90]:
                    cell=next(v for v in metrics if v['kind']==kind and v['h']==h and v['stratum']=='confirmed_normal' and v['scale']=='run' and v['group']==run)
                    values.append(cell['metrics'][b]['MAE'])
                    if bi==0:ns.append(cell['n'])
                ax.bar(np.arange(3)+(bi-1.5)*.19,values,width=.18,color=COLORS[b],label=NAMES[b])
            ax.set_xticks(range(3),[f'{h}秒\nn={n}' for h,n in zip([15,45,90],ns)])
            ax.set_title(title,fontsize=11);ax.set_ylabel('温度MAE（°C）')
            if col==0 and row==2:ax.legend(fontsize=7,ncol=2)
    fig.text(.5,-.008,'全部为开发/拟合内诊断；每根并列柱使用同一起点、同一温度答案。主图为未来控制状态可确认正常层；其他层与完整覆盖另存。各面板独立纵轴。',ha='center',fontsize=9)
    fig.tight_layout()
    figs.append(finish(fig,'图2-四慢态与共同温度误差',[
        '上排横轴为各轮经过的秒数、纵轴为四种潜在状态来源的°C；下两排横轴为15/45/90秒时距、纵轴为共同标签上的温度MAE。',
        '主要看同一G2只换Ts后误差怎样改变：G2有增量信息，但M上30秒滤波接近；柱下n和灰区给出覆盖边界。',
        '这些是可观测TJ的误差，不能读成Ts的准确率、独立留出验证、未来输入已知的现场预测，或控制收益。']))

    fig,axs=plt.subplots(3,3,figsize=(17,10),squeeze=False)
    fig.suptitle('图3｜离线增量需求形态；没有执行风扇指令',fontsize=19,y=1.015)
    for col,(run,start,end,title) in enumerate(cols):
        rows=window(demand,run,start,end)
        axs[0,col].set_title(title)
        for b in BRANCHES:
            trace(axs[0,col],rows,lambda r,b=b:r['branches'][b]['z_raw'],start,NAMES[b],COLORS[b])
            trace(axs[1,col],rows,lambda r,b=b:r['branches'][b]['z_output'],start,NAMES[b],COLORS[b])
        axs[0,col].axhline(0,color='#888',ls=':',lw=1,label='下限0；上限1在本窗外' if col==0 else None)
        axs[1,col].axhline(0,color='#888',ls=':',lw=.8)
        axs[0,col].set_ylabel('裁剪前增量（无量纲）')
        axs[1,col].set_ylabel('相同塑形后（无量纲）')
        pwm(axs[2,col],ledger,run,start,end)
        for row in range(3):
            ax=axs[row,col];unavailable(ax,ledger,run,start,end);events(ax,runs,run,start,end)
            ax.set_xlim(0,end-start)
            if row==2:ax.set_xlabel('相对本窗起点（秒）')
        axs[0,col].legend(fontsize=7,ncol=2)
        axs[2,col].legend(fontsize=8)
        if col==0:
            axs[1,col].text(.03,.48,'本窗G2低于已热参考\n零值不等于无需散热',fontsize=9,
                color='#6a4638',transform=axs[1,col].transAxes)
    fig.text(.5,-.008,'纵轴独立缩放，不是PWM换算。固定尺度10°C、死区0.02、全幅升30秒/降120秒；所有分支相同。参考可能已热，0不等于无需散热。灰区不续龄。',ha='center',fontsize=9)
    fig.tight_layout()
    figs.append(finish(fig,'图3-平稳需求信号',[
        '横轴为窗口秒数，上排是未裁剪无量纲增量，中排是同一死区及限速后的需求指数，下排另轴保留现场PWM百分比。',
        '主要看G2与30秒滤波都能减少短峰追随，持续M负载仍有升量；同时检查原始幅度、低于已热参考的负值和灰区，不把平直零线叫胜利。',
        '更平稳不等于真实更安静或更安全，指数不能直接代入现有TJ—PWM曲线；本轮没有执行任何新风扇动作。']))

    mend=next(p for p in m['phases'] if p['id']=='M180')
    tails=[('S',sparse['end']-8,sparse['end']+85,sparse['end'],'S02结束后（下一题前）'),
           ('S',continuous['end']-15,continuous['end']+180,continuous['end'],'连续组结束后：资格不足'),
           ('M',mend['end']-15,mend['end']+300,mend['end'],'M180结束后300秒')]
    fig,axs=plt.subplots(3,3,figsize=(17,10.4),squeeze=False)
    fig.suptitle('图4｜结束后分清：TJ回落、状态残留和塑形尾部',fontsize=19,y=1.015)
    for col,(run,start,end,taskend,title) in enumerate(tails):
        ar=window(accepted,run,start,end);lr=window(long,run,start,end);dr=window(demand,run,start,end)
        trace(axs[0,col],ar,lambda r:r['values']['tj'],start,'实测TJ','#202d3c',segment=False)
        trace(axs[0,col],lr,lambda r:r['Tf'],start,'原定义A-long Tf','#b3412e')
        for b in BRANCHES:
            trace(axs[1,col],dr,lambda r,b=b:r['branches'][b]['state']-r['branches'][b]['reference'],start,NAMES[b],COLORS[b])
        for b in ['STATE-G2','STATE-LP30']:
            trace(axs[2,col],dr,lambda r,b=b:r['branches'][b]['z_target'],start,NAMES[b]+'：状态目标',COLORS[b],style='--')
            trace(axs[2,col],dr,lambda r,b=b:r['branches'][b]['z_output'],start,NAMES[b]+'：塑形输出',COLORS[b])
        axs[1,col].axhline(.2,color='#888',ls=':',lw=1,label='参考附近：+0.2°C')
        axs[2,col].axhline(.02,color='#888',ls=':',lw=1,label='参考附近：0.02')
        axs[0,col].set_title(title)
        for row in range(3):
            ax=axs[row,col];unavailable(ax,ledger,run,start,end)
            ax.axvline(taskend-start,color='#333',ls=':',lw=1)
            ax.set_xlim(0,end-start);ax.legend(fontsize=7,loc='best',ncol=1 if row==0 else 2)
            if row==2:ax.set_xlabel('相对窗口起点（秒）；竖虚线=客户端结束')
        for row,label in enumerate(['TJ / Tf（°C）','相对本段参考的状态（°C）','目标/输出（无量纲）']):axs[row,col].set_ylabel(label)
        if not dr:axs[1,col].text(.5,.5,'原60秒状态资格不足\n不补线、不计算返回时间',ha='center',va='center',transform=axs[1,col].transAxes,color='#666')
        if col==1 and dr:
            recovery=dr[0]['wall']-start
            for row in [1,2]:
                axs[row,col].axvline(recovery,color='#7256a3',ls=':',lw=1)
            axs[1,col].text(.04,.57,'灰区无慢态\n恢复后固定新段参考\n不拼成原任务尾部',fontsize=9,
                color='#7256a3',transform=axs[1,col].transAxes)
    fig.text(.5,-.01,'每格独立纵轴。状态目标仍高的尾部来自状态；目标与实线之差来自固定死区/限速；没有假设新需求会产生与原风扇相同的实测TJ。',ha='center',fontsize=9)
    fig.tight_layout()
    figs.append(finish(fig,'图4-任务结束后的三种尾部',[
        '横轴是任务结束附近的秒数，竖虚线为客户端完成；三排分别显示TJ/Tf、相对本段参考的状态°C、无量纲状态目标与塑形输出。',
        '主要看TJ可以先降而慢态仍高，以及状态目标和塑形输出之间额外尾部；连续组资格不足时保持灰区，恢复后新参考不接成原任务尾部或返回时间。',
        '客户端结束不等于GPU内核结束，尾部更长不自动更好；这些图不能证明降低风量后的温度、安全或噪音效果。']))
    (OUT/'figure-index.json').write_text(json.dumps(figs,ensure_ascii=False,indent=2)+'\n')
    sections=[]
    for f in figs:
        sections.append(f'<section><h2>{f["name"]}</h2><a href="{f["svg"]}"><img src="{f["png"]}" alt="{f["name"]}"></a>'+''.join(f'<p>{s}</p>' for s in f['caption'])+'</section>')
    (OUT/'中文图解.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TTO快慢状态与平稳需求图解</title>
<style>body{max-width:1500px;margin:30px auto;padding:0 24px;font-family:system-ui;color:#213044;background:#fafbfd;line-height:1.7}img{width:100%;border:1px solid #ddd}section{margin:44px 0}p{max-width:1100px}a{color:#1b7e91}</style>
<h1>快慢热状态与平稳需求：四类图解</h1><p>离线开发资料；固定模型，零次重新拟合。灰色表示普通状态/需求资格不足；真实TJ及原风险信息保留。点击图可打开矢量原图。</p>'''+''.join(sections)+'</html>')
    (OUT/'plot-environment.json').write_text(json.dumps(dict(python=sys.version,executable=sys.executable,
        numpy=np.__version__,matplotlib=matplotlib.__version__,font_family=plt.rcParams['font.family'],
        wall_seconds=time.perf_counter()-started),ensure_ascii=False,indent=2)+'\n')
    print('Saved four Chinese figure classes, SVG originals and standalone HTML guide.')


if __name__=='__main__':main()
