"""Chinese descriptive figures from frozen results, never used for candidate choice."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT, read, lines
from analyse import seconds


def plots(result,out):
    out.mkdir(parents=True,exist_ok=False)
    local=Path('/System/Library/Fonts/STHeiti Medium.ttc')
    if local.exists():
        font_manager.fontManager.addfont(str(local))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=str(local)).get_name()
    else:
        plt.rcParams['font.family']=['Noto Sans CJK SC','DejaVu Sans']
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,'svg.hashsalt':'TTO-CPU-ACTIVITY-v1'})
    c=read(ROOT/'candidate.json')
    frames=list(lines(result/'feature-frames.jsonl'))
    blocks=read(result/'block-onset-reference.json')
    names=['gpu_pct','gpu_W','cpu_soc_mss_W','cpu_mean_pct','cpu_max_pct']
    labels=['GPU利用率','GPU rail','CPU/SOC/MSS rail','CPU全核均值','每时刻CPU最大值']
    colors=['#2b9348','#ef7d00','#8c510a','#9b59b6','#00a6a6']
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=160,metadata={'Software':'TTO offline CPU increment v1'})
        fig.savefig(out/(name+'.svg'),metadata={'Date':None})
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,8),sharex=True,sharey=True)
    maximum=1.0
    for ax,b,title in zip(axes.ravel(),blocks,['首次单路','双路','四路','重复单路']):
        selected=[f for f in frames if -2.1<=seconds(f['arrived_at_utc'])-b['start']<=6.1]
        ts=[seconds(f['arrived_at_utc'])-b['start'] for f in selected]
        for n,l,color in zip(names,labels,colors):
            ys=[(f['features'][n]['value']-c['levels']['idle'][n])/(c['levels']['active'][n]-c['levels']['idle'][n]) for f in selected]
            maximum=max(maximum,max(ys))
            ax.plot(ts,ys,'o-',label=l,color=color,markersize=4,linewidth=1.6)
        ax.axvline(0,color='black',ls='--',lw=1)
        ax.axhline(c['on'],color='#cc3333',ls=':',lw=1)
        ax.set_title(title+'：客户端提交以后收到的信息')
        ax.grid(alpha=.2)
        ax.set_xlim(-2.1,6.1)
        ax.set_xlabel('距真实提交的接收时间（秒）')
        ax.set_ylabel('相对开发背景／活跃幅差的比例')
    axes.ravel()[0].set_ylim(-.12,maximum+.1)
    handles,leg=axes.ravel()[0].get_legend_handles_labels()
    fig.legend(handles,leg,loc='upper center',bbox_to_anchor=(.5,.945),ncol=5,fontsize=9)
    fig.suptitle('四次启动的已到达信息：CPU须与已有两rail公平比较',y=.995,fontsize=15)
    fig.text(.5,.955,'旧1秒开发记录；竖虚线为客户端提交，红横线为活动阈值。它们不标定GPU内核起点。',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.9))
    save(fig,'01-四次启动的已到达信息')
    tables=read(result/'temperature-common.json')
    common={r['h']:r for r in tables if r['posthoc_stratum']=='all'}
    activity=read(result/'activity-metrics.json')['groups']
    methods=['B0','B1','G2-HOLD','INPUT-BASE','INPUT-MEAN','INPUT-CORE']
    cn=['B0','B1','原G2-HOLD','已有输入','加CPU均值','再加CPU最大值']
    cs=['#888888','#b5b5b5','#1f77b4','#e79f00','#9b59b6','#00a6a6']
    fig,axes=plt.subplots(2,2,figsize=(14,9))
    x=np.arange(3);w=.12
    for i,(n,l,color) in enumerate(zip(methods,cn,cs)):
        axes[0,0].bar(x+(i-2.5)*w,[common[h]['errors'][n]['MAE_C'] for h in (15,45,90)],w,label=l,color=color)
    axes[0,0].set_xticks(x,['15秒','45秒','90秒']);axes[0,0].set_ylabel('平均绝对温度误差（°C）')
    axes[0,0].set_title('同起点、同标签：新转换整体未胜出')
    axes[0,0].legend(fontsize=8,ncol=3)
    vals=[a['active_while_no_client_inflight_s'] for a in activity]
    bars=axes[0,1].bar(['已有输入','加CPU均值','再加CPU最大值'],vals,color=cs[3:])
    axes[0,1].bar_label(bars,fmt='%.1f秒',padding=3)
    axes[0,1].set_ylim(0,400);axes[0,1].set_ylabel('无客户端在途时仍判断活跃（秒）')
    axes[0,1].set_title('共同可用背景：CPU版本的活动误报增加')
    axes[0,1].text(.5,.92,'协议参照；不能解释为GPU内核真值',transform=axes[0,1].transAxes,ha='center',fontsize=9)
    x=np.arange(len(methods));w=.35
    axes[1,0].bar(x-w/2,[common[45]['errors'][n]['P95_absolute_C'] for n in methods],w,label='绝对误差P95',color='#d95f02')
    axes[1,0].bar(x+w/2,[common[45]['errors'][n]['max_under_C'] for n in methods],w,label='最大低估',color='#1b9e77')
    axes[1,0].set_xticks(x,cn,rotation=15);axes[1,0].set_ylabel('45秒温度误差（°C）')
    axes[1,0].set_title('不能用“低估比例下降”代替整体收益');axes[1,0].legend(fontsize=9)
    strata=['submitted_not_yet_observed','observed_startup_15s','sustained','after_DONE_90s','background']
    sl=['已提交\n尚未观察到','已观察到\n启动15秒','持续','DONE后\n90秒','背景']
    x=np.arange(len(strata));w=.24
    for j,n in enumerate(['G2-HOLD','INPUT-BASE','INPUT-CORE']):
        vals=[next(r for r in tables if r['h']==45 and r['posthoc_stratum']==s)['errors'][n]['MAE_C'] for s in strata]
        axes[1,1].bar(x+(j-1)*w,vals,w,color=cs[methods.index(n)],label=cn[methods.index(n)])
    axes[1,1].set_xticks(x,sl,fontsize=9);axes[1,1].set_ylabel('45秒平均绝对误差（°C）')
    axes[1,1].set_title('事后分层只解释误差，不是预测特征');axes[1,1].legend(fontsize=9)
    for ax in axes.ravel():ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('唯一候选的开发对照：CORE与MEAN相同，均未支持上线',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.96))
    save(fig,'02-增量活动与温度预测的成功及失败')
    stale=read(result/'stale4682-addendum.json')
    t0=stale['start_mono_s'];t1=stale['recovery_observation_mono_s']
    raw=list(lines(ROOT/'inputs/inputs/native/observations-0001.jsonl'))
    fan=[r for r in raw if r['kind']=='fan' and t0-8<=r['mono_s']<=t0+10]
    samples=[r for r in lines(ROOT/'inputs/results/samples-and-causal-states.jsonl') if t0-8<=r['t']<=t0+10]
    fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True)
    axes[0].plot([r['mono_s']-t0 for r in fan],[r['payload']['data']['fans'][0]['duty'] for r in fan],'o-',color='#ef7d00')
    axes[0].set_ylabel('原成功PWM（%）');axes[0].set_ylim(0,85)
    axes[0].annotate('4682：25%\ntemp_stale=true',xy=(0,25),xytext=(1,10),arrowprops={'arrowstyle':'->'},fontsize=10)
    axes[1].plot([r['t']-t0 for r in samples],[r['current'] for r in samples],'o-',color='#d73027',label='独立源的有效TJ')
    axes[1].set_ylabel('实测TJ（°C）');axes[1].legend(fontsize=9)
    states={'tracking':1.,'degraded':0.,'provisional':.5}
    axes[2].scatter([r['t']-t0 for r in samples],[states[r['states']['AUGMENTED-KF']['phase']] for r in samples],color='#1f77b4')
    axes[2].set_yticks([0,1],['降级','tracking']);axes[2].set_ylim(-.2,1.2)
    axes[2].set_ylabel('TJ起点模型资格');axes[2].set_xlabel('距18:05:38.535886明确失温反馈（秒）')
    for ax in axes:
        ax.axvspan(0,t1-t0,color='red',alpha=.13)
        ax.grid(alpha=.2)
    fig.suptitle('4682号记录：HTTP成功与明确失温反馈同时存在',fontsize=15)
    fig.text(.5,.935,'阴影到下一份非stale反馈，约1.012秒；不是精确失温持续时间或新控制政策。原图、PWM与分数均保留。',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.91))
    save(fig,'03-明确失温反馈及恢复说明')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();plots(a.result,a.output)
