from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
from matplotlib import font_manager
p=Path(__file__).parent.parent;j=json.loads((p/'round2-verification.json').read_text());r=Path('/workspace/Tianshan-thermal-observer/evidence/formal-collection-20261013-round2');raw=[json.loads(l) for l in next(r.glob('run-*/observations-0001.jsonl')).read_text().splitlines()];fan=[];tz=ZoneInfo('Asia/Shanghai')
for v in raw:
 if v['kind']=='fan' and v.get('payload',{}).get('data',{}).get('fans'):fan.append(dict(v['payload']['data']['fans'][0],t=datetime.fromisoformat(v['received_at_utc'])))
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Medium.ttc');plt.rcParams.update({'font.family':font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name(),'axes.unicode_minus':False})
fig,ax=plt.subplots(3,1,figsize=(13,8),sharex=True);fig.suptitle('第二轮补充：成功风扇API中的PWM、增益及预测状态')
x=[v['t'] for v in fan]
ax[0].step(x,[v['duty'] for v in fan],where='post',color='#196852');ax[0].set_ylabel('PWM %')
ax[1].step(x,[v['controller_gain'] for v in fan],where='post',color='#916215');ax[1].set_ylabel('controller_gain')
ax[2].plot(x,[v['temperature'] for v in fan],label='API温度');ax[2].plot(x,[v['predicted_temperature'] for v in fan],label='预测温度',alpha=.8);ax[2].set_ylabel('温度 °C');ax[2].legend()
for c in j['phase_snapshot_checks']:
 if c['phase'] not in ['4','5a','5b']:continue
 f=c['snapshots']['peak'];t=datetime.fromisoformat(f['time']);ax[0].plot(t,f['duty'],'o');ax[0].annotate(f"{c['phase']}：{f['duty']}%",(t,f['duty']),xytext=(5,8),textcoords='offset points')
for v in j['device_stale_impact']:
 f=v['event'];t=datetime.fromisoformat(f['time']);ax[0].plot(t,f['duty'],'x',color='red',ms=9);ax[0].annotate('失温事件及恢复影响，原因未调查',(t,f['duty']),xytext=(10,15),textcoords='offset points',fontsize=9)
for a in ax:a.grid(alpha=.25)
ax[-1].xaxis.set_major_locator(md.MinuteLocator(interval=5,tz=tz));ax[-1].xaxis.set_major_formatter(md.DateFormatter('%H:%M',tz=tz));ax[-1].set_xlabel('北京时间；API接收时刻，不是硬件同步时刻')
fig.tight_layout(rect=(0,0,1,.95));fig.savefig(p/'analysis/round2-gain-supplement.png',dpi=140)
