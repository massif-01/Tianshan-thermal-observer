import csv,json,math
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
from matplotlib import font_manager
out=Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Medium.ttc')
name=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name()
plt.rcParams.update({'font.family':name,'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
r=json.loads((out/'statistics.json').read_text());rows=list(csv.DictReader((out/'measurements.csv').open()));tz=ZoneInfo('Asia/Shanghai')
xs=[];ys={k:[] for k in ('tj','gpu_power','cpu_power','vin_power','gpu','duty')};previous=None
for d in rows:
    t=float(d['t'])
    if previous and (t-previous>5):
        for missing_t in (previous+0.001,t-0.001):
            xs.append(md.date2num(datetime.fromtimestamp(missing_t,tz)))
            for k in ys:ys[k].append(float('nan'))
    xs.append(md.date2num(datetime.fromtimestamp(t,tz)))
    for k in ys:ys[k].append(float(d[k]) if d[k] else float('nan'))
    previous=t
fig,axes=plt.subplots(4,1,figsize=(13.4,10.3),sharex=True,gridspec_kw={'height_ratios':[1.2,1,1,1]})
fig.subplots_adjust(left=.075,right=.98,top=.87,bottom=.10,hspace=.13)
fig.suptitle('RM-01 七个工况的温度、独立功耗、GPU 和成功 PWM',x=.075,ha='left',y=.973,fontsize=18)
fig.text(.075,.932,'北京时间 2026-10-13  |  工况边界采用人工上报近似时间  |  灰色缺口无数据，不连线',fontsize=11,color='#4b5563')
colors=['#e8eef8','#f4e9d8','#e5f0e8','#eee6f4','#f5e3e1','#e1edf1','#ebefdf']
for i,ph in enumerate(r['phases']):
    a=md.date2num(datetime.fromtimestamp(ph['start'],tz));b=md.date2num(datetime.fromtimestamp(ph['end'],tz))
    for ax in axes:ax.axvspan(a,b,color=colors[i],alpha=.62,zorder=0)
    axes[0].text((a+b)/2,1.03,str(ph['id']),transform=axes[0].get_xaxis_transform(),ha='center',fontsize=12,fontweight='bold')
gap=r['gap'];ga=md.date2num(datetime.fromtimestamp(gap['start'],tz));gb=md.date2num(datetime.fromtimestamp(gap['end'],tz))
for ax in axes:
    ax.axvspan(ga,gb,color='#b6bcc5',alpha=.50,zorder=1)
    ax.grid(axis='y',color='#aeb6c2',alpha=.3);ax.tick_params(axis='both',labelsize=10)
axes[0].text((ga+gb)/2,60,'缺口\n6分29秒',ha='center',va='center',fontsize=12,color='#374151')
axes[0].plot(xs,ys['tj'],color='#bd3a39',lw=1.3,label='TJ 实测温度')
axes[0].set_ylabel('TJ 温度（°C）');axes[0].set_ylim(43,73)
p=r['global_peaks']['tj'];px=md.date2num(datetime.fromtimestamp(p['t'],tz))
axes[0].plot(px,p['tj'],'o',color='#bd3a39',ms=5)
axes[0].annotate(f"已测峰值 {p['tj']:.2f}°C",(px,p['tj']),xytext=(-115,10),textcoords='offset points',fontsize=10,arrowprops={'arrowstyle':'-','color':'#bd3a39'})
for k,label,color in [('gpu_power','VDD_GPU','#2161a0'),('cpu_power','VDD_CPU_SOC_MSS','#b36f0f'),('vin_power','VIN_SYS_5V0','#168062')]:axes[1].plot(xs,ys[k],label=label,color=color,lw=1.0)
axes[1].set_ylabel('独立 rail 当前值（W）');axes[1].legend(loc='upper right',ncol=3,fontsize=9,framealpha=.85)
axes[2].plot(xs,ys['gpu'],color='#574798',lw=1.0);axes[2].set_ylabel('GPU 利用率（%）');axes[2].set_ylim(-3,105)
axes[3].step(xs,ys['duty'],where='post',color='#166c55',lw=1.15);axes[3].set_ylabel('成功 PWM（%）');axes[3].set_ylim(10,82)
stale=[d for d in rows if d['temp_stale']=='True' and d['duty']]
if stale:
    sx=[md.date2num(datetime.fromtimestamp(float(d['t']),tz)) for d in stale];sy=[float(d['duty']) for d in stale]
    axes[3].scatter(sx,sy,color='#d13030',marker='x',s=30,zorder=5,label='主板 temp_stale=true');axes[3].legend(loc='upper right',fontsize=9)
axes[-1].xaxis.set_major_locator(md.MinuteLocator(byminute=range(0,60,5),tz=tz));axes[-1].xaxis.set_major_formatter(md.DateFormatter('%H:%M',tz=tz));axes[-1].set_xlabel('北京时间（横向缺口不表示采样为零）')
fig.text(.075,.032,'1 空载待机   2 模型拉起   3 驻模待机（末段有GPU活动）   4 单发推理   5 并发推理（未采到结尾）   6 回落待机   7 卸载后空载',fontsize=10)
fig.savefig(out/'condition-timeline.png',dpi=150)
fig.savefig(out/'condition-timeline.svg')
