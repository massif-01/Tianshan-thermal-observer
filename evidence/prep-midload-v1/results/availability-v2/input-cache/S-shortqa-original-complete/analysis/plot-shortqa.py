from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv,json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
from matplotlib import font_manager
p=Path(__file__).parent;j=json.loads((p/'statistics.json').read_text());rows=list(csv.DictReader((p/'measurements.csv').open()));tz=ZoneInfo('Asia/Shanghai')
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Medium.ttc');plt.rcParams.update({'font.family':font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name(),'axes.unicode_minus':False,'font.size':10})
def x(t):return md.date2num(datetime.fromtimestamp(t,tz))
def val(k):return [float(r[k]) if r[k] not in ['','None'] else math.nan for r in rows]
xs=[x(float(r['t'])) for r in rows]
fig,axs=plt.subplots(6,1,sharex=True,figsize=(15,13));fig.subplots_adjust(top=.90,bottom=.08,hspace=.15,left=.08,right=.95)
fig.suptitle('TTO短问答：单路稀疏与连续节奏的同一轮观测',fontsize=18,y=.98)
fig.text(.08,.935,'北京时间 | 单路、固定64生成token上限 | 峰值窗口可能包含热历史，不是独立因果A/B',fontsize=11)
colors={'pilot':'#eee4da','resident-baseline':'#dde8f5','sparse':'#e8efe1','between-groups':'#e3e9ed','continuous':'#f3e3e5','final-cooldown':'#e6e4f0'}
for ph in j['phases']:
 a=x(datetime.fromisoformat(ph['start_utc']).timestamp());b=x(datetime.fromisoformat(ph['end_utc']).timestamp())
 for ax in axs:ax.axvspan(a,b,color=colors.get(ph['phase'],'#eeeeee'),alpha=.6)
 axs[0].text((a+b)/2,1.03,{'pilot':'预试','resident-baseline':'驻模背景','sparse':'稀疏6题','between-groups':'组间回落','continuous':'连续12题','final-cooldown':'最终回落'}.get(ph['phase'],ph['phase']),ha='center',transform=axs[0].get_xaxis_transform(),fontsize=9)
for q in j['requests']:
 a=x(datetime.fromisoformat(q['submit_utc']).timestamp());b=x(datetime.fromisoformat(q['end_utc']).timestamp())
 for ax in axs:ax.axvspan(a,b,color='#bf6c22',alpha=.22)
 axs[0].text(a,1.14,q['request_id'],rotation=90,fontsize=8,transform=axs[0].get_xaxis_transform(),ha='center')
for k,label in [('tj','TJ'),('temp_cpu','CPU'),('temp_gpu','GPU温区')]:axs[0].plot(xs,val(k),label=label,lw=1)
axs[0].legend(loc='upper right',ncol=3,fontsize=8);axs[0].set_ylabel('温度 °C')
for k,label in [('gpu_power','GPU'),('cpu_power','CPU/SOC/MSS'),('vin_power','5V')]:axs[1].plot(xs,val(k),label=label,lw=1)
axs[1].legend(loc='upper right',ncol=3,fontsize=8);axs[1].set_ylabel('独立rail W')
axs[2].plot(xs,val('gpu'),lw=1,color='#5b4b98');axs[2].set_ylabel('GPU利用率 %');axs[2].set_ylim(-3,103)
axs[3].step(xs,val('duty'),where='post',color='#176c56');axs[3].set_ylabel('成功PWM %');axs[3].set_ylim(0,105)
axs[4].step(xs,val('gain'),where='post',color='#936b15');axs[4].set_ylabel('controller_gain')
axs[5].plot(xs,val('slope'),color='#48618f',label='控制斜率 °C/min');axs[5].set_ylabel('斜率 °C/min')
b=axs[5].twinx();b.plot(xs,val('predicted'),lw=.8,color='#ae4747',label='预测温度 °C');b.set_ylabel('预测温度 °C')
for typ,marker,col,label in [('http_timeout','^','#c44327','HTTP超时'),('device_temp_stale','x','#222222','主板失温')]:
 aa=[a for a in j['anomalies'] if a['type']==typ]
 if aa:axs[3].scatter([x(a['t']) for a in aa],[a.get('duty',5) for a in aa],marker=marker,color=col,s=35,label=label,zorder=5)
if j['anomalies']:axs[3].legend(loc='upper right',fontsize=8)
for ax in axs:ax.grid(axis='y',alpha=.25)
axs[-1].xaxis.set_major_locator(md.MinuteLocator(interval=2,tz=tz));axs[-1].xaxis.set_major_formatter(md.DateFormatter('%H:%M',tz=tz));axs[-1].set_xlabel('北京时间；浅橙色为真实请求执行窗口')
fig.savefig(p/'shortqa-timeline.png',dpi=150);fig.savefig(p/'shortqa-timeline.svg')
