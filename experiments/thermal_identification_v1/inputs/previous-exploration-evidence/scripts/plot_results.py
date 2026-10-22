"""Static research figures; measured signals and hypothetical replay are labeled separately."""
import bisect
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
font='/System/Library/Fonts/STHeiti Medium.ttc'
font_manager.fontManager.addfont(font)
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),
                     'axes.unicode_minus':False,'font.size':10})
CHARTS=OUT/'charts';CHARTS.mkdir(exist_ok=True)


def save(fig,name):
    fig.savefig(CHARTS/(name+'.png'),dpi=150)
    fig.savefig(CHARTS/(name+'.svg'))
    plt.close(fig)


def main():
    req=json.loads((ROOT/'evidence/short-qa-20261013/normalized-requests.json').read_text())
    s01=next(q for q in req if q['request_id']=='S01')
    run=next((ROOT/'evidence/short-qa-20261013').glob('run-*'))
    fan=[]
    for line in (run/'observations-0001.jsonl').open():
        o=json.loads(line)
        if o['kind']=='fan':
            for f in o['payload'].get('data',{}).get('fans',[]):
                if f['id']==0:fan.append(dict(f,mono=o['mono_s']))
    selected=[f for f in fan if -8<=f['mono']-s01['end_mono_s']<=100]
    s02=next(q for q in req if q['request_id']=='S02')
    next_start=s02['submit_mono_s']-s01['end_mono_s']
    x=[f['mono']-s01['end_mono_s'] for f in selected]
    alltimes=[f['mono'] for f in fan]
    fast=[]
    for f in selected:
        i=bisect.bisect_right(alltimes,f['mono']-5)-1
        old=fan[i]
        dt=f['mono']-old['mono']
        fast.append((f['control_temperature']-old['control_temperature'])*60/dt if 4<=dt<=6 else float('nan'))
    fig,axs=plt.subplots(3,1,sharex=True,figsize=(11.5,8.5),layout='constrained')
    fig.suptitle('S01 实测：先被长趋势挡住退档，随后才限速下降',fontsize=15)
    axs[0].plot(x,[f['control_temperature'] for f in selected],color='#bd5a23',label='实测主板控制温度')
    axs[0].set_ylabel('温度 °C');axs[0].legend()
    axs[1].plot(x,[f['slope_c_per_min'] for f in selected],label='控制器报告：约30秒斜率',color='#465e9b')
    axs[1].plot(x,fast,label='快照计算：约5秒斜率（离线派生）',color='#aa8170',linestyle='--')
    axs[1].axhline(0,color='#555555',lw=.7);axs[1].set_ylabel('斜率 °C/min');axs[1].legend()
    axs[2].step(x,[f['duty'] for f in selected],where='post',color='#177755',label='实测成功PWM')
    axs[2].set_ylabel('PWM %');axs[2].set_xlabel('距客户端协议结束（秒）；不是GPU内核结束时刻')
    axs[2].legend()
    for a in axs:
        a.axvline(0,color='#555555',linestyle=':')
        a.axvspan(.69,30.69,color='#efe2c9',alpha=.45)
        a.grid(alpha=.2)
        a.axvspan(next_start,100,color='#ead8d0',alpha=.4)
    axs[0].text(next_start+.5,.95,'S02开始\n后题影响',transform=axs[0].get_xaxis_transform(),va='top',fontsize=9)
    save(fig,'s01-observed-mechanism')

    first=fan[0]['mono'];fig,axs=plt.subplots(2,1,sharex=True,figsize=(11.5,7),layout='constrained')
    fig.suptitle('同温度序列的离线控制回放：只比较输出规则',fontsize=15)
    axs[0].plot(x,[f['control_temperature'] for f in selected],color='#bd5a23',label='输入：原实测温度快照')
    axs[0].set_ylabel('输入温度 °C');axs[0].legend()
    axs[1].step(x,[f['duty'] for f in selected],where='post',color='#888888',lw=1.7,label='原实测PWM（供参考）')
    variants=[('reference-native-gain','#465e9b','参考C规则＋原gain更新规则'),
              ('release-native-gain','#177755','仅增加退出许可＋原gain更新规则'),
              ('reference-fixed-gain','#bc5b78','仅固定起始gain：1.868695')]
    for name,color,label in variants:
        rows=list(csv.DictReader((OUT/'results'/f'control-{name}.csv').open()))
        rows=[r for r in rows if -8<=float(r['second'])-(s01['end_mono_s']-first)<=100]
        axs[1].step([float(r['second'])-(s01['end_mono_s']-first) for r in rows],
                    [int(r['successful_pwm']) for r in rows],where='post',color=color,label=label,linestyle='--')
    axs[1].set_ylabel('PWM %');axs[1].legend(fontsize=9)
    axs[1].set_xlabel('距客户端结束（秒）｜当前曲线假设、隐藏历史不完整；不能据此证明减少风量后的温度安全')
    for a in axs:
        a.grid(alpha=.2);a.axvline(0,color='#555555',linestyle=':')
        a.axvspan(next_start,100,color='#ead8d0',alpha=.4)
    axs[0].text(next_start+.5,.95,'S02开始\n后题影响',transform=axs[0].get_xaxis_transform(),va='top',fontsize=9)
    save(fig,'s01-offline-permission-comparison')

    e=json.loads((OUT/'model-exploration/short-qa/evaluation/evaluation.json').read_text())
    fig,ax=plt.subplots(figsize=(11.5,5.5),layout='constrained')
    methods=[('persist','B0 保持当前TJ','#777777'),('trend30','B1 长趋势外推','#bd5a23'),
             ('ridge_tj','Ridge TJ','#465e9b'),('ridge_full','Ridge 完整输入','#177755')]
    for i,(method,label,color) in enumerate(methods):
        ax.bar([h+i*.19-.285 for h in range(3)],
               [e['same_origin_metrics'][str(h)][method]['time_pooled']['mae'] for h in [15,45,90]],
               width=.18,color=color,label=label)
    ax.set_xticks(range(3),[f'{h}秒（共同起点 n={e["same_origin_intersection_count"][str(h)]}）' for h in [15,45,90]])
    ax.set_ylabel('MAE °C');ax.legend();ax.grid(axis='y',alpha=.2)
    ax.set_title('单过程后段开发窗口：Ridge未胜过B0，主要覆盖待机',fontsize=15)
    ax.set_xlabel('26/20/11个起点高度相关；验证仅5个，不能宣称跨过程效果或控制收益')
    save(fig,'ridge-development-comparison')
    print('PASS three labeled figures')


if __name__=='__main__':main()
