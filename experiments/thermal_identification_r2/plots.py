"""Static research figures, rendered from sealed point artifacts only."""
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent;os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'plot-cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=ROOT/'runs/main';PLOTS=OUT/'figures';PLOTS.mkdir(exist_ok=True)
read=lambda p:json.loads(Path(p).read_text())
lines=lambda p:[json.loads(x) for x in Path(p).read_text().splitlines()]
data=read(OUT/'registered/data.json');sample_lookup={r['ref']:r for r in data['accepted']}
old=lines(OUT/'evaluation/LS-fit-on-LSM/A-long.jsonl');new=lines(OUT/'evaluation/D-LSM/A-long.jsonl');a24=lines(OUT/'evaluation/D-LSM-G2-A24/A-long.jsonl')
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120})


def save(fig,name):
    fig.savefig(PLOTS/f'{name}.png',dpi=170,bbox_inches='tight');fig.savefig(PLOTS/f'{name}.svg',bbox_inches='tight');plt.close(fig)


def trajectory(ax,rows,run,key,label,color,start,window=None,style='-'):
    records=[r for r in rows if r['run']==run and (window is None or window[0]<=sample_lookup[r['ref']]['wall']<=window[1])]
    for j,seg in enumerate(dict.fromkeys(r['segment'] for r in records)):
        group=[r for r in records if r['segment']==seg]
        ax.plot([sample_lookup[r['ref']]['wall']-start for r in group],[r['A'][key] for r in group],style,c=color,lw=1.1,label=label if j==0 else None)


fig,axs=plt.subplots(3,1,figsize=(11,8),constrained_layout=True)
for ax,run in zip(axs,['L','S','M']):
    samples=[r for r in data['accepted'] if r['run']==run];start=samples[0]['wall']
    ax.plot([r['wall']-start for r in samples],[r['values']['tj'] for r in samples],c='black',lw=.8,label='Observed TJ')
    trajectory(ax,old,run,'G2','Old LS-fit G2','#7f7f7f',start,style='--');trajectory(ax,new,run,'G2','New D-LSM G2','#0072b2',start)
    trajectory(ax,a24,run,'G2','A24 G2 diagnostic','#d55e00',start)
    ax.set(ylabel='TJ (deg C)',title=f'{run}: full causal-prefix free response'+(' | ambient confirmed 24 C' if run=='M' else ' | ambient unconfirmed'))
    ax.grid(alpha=.15)
axs[0].legend(ncol=4,fontsize=8);axs[-1].set_xlabel('Seconds since first accepted TJ')
fig.suptitle('A-long: recorded input paths; no TJ feedback after each legal prefix. D-LSM uses all three runs for fitting.')
save(fig,'A-long-all-runs')

run=next(r for r in data['runs'] if r['run']=='M');events=[p for p in run['phases'] if p['macro']=='work']
fig,axs=plt.subplots(1,3,figsize=(12,3.8),constrained_layout=True)
for ax,event in zip(axs,events):
    start=event['start'];end=event['end'];samples=[r for r in data['accepted'] if r['run']=='M' and start-15<=r['wall']<=end+300]
    ax.plot([r['wall']-start for r in samples],[r['values']['tj'] for r in samples],c='black',lw=1.1,label='Observed TJ')
    for rows,label,color,style in [(old,'Old LS-fit','#7f7f7f','--'),(new,'D-LSM Efree','#0072b2','-'),(a24,'A24 diagnostic','#d55e00','-')]:
        trajectory(ax,rows,'M','G2',label,color,start,(start-15,end+300),style)
    ax.axvline(end-start,c='black',ls=':',lw=1,label='Actual block end');ax.set(title=f"{event['id']}: actual {event['actual_s']:.2f}s",xlabel='Seconds from actual block start',ylabel='TJ (deg C)');ax.grid(alpha=.15)
axs[0].legend(fontsize=7);fig.suptitle('M at confirmed 24 C: one continuous thermal process; G2 is never reset at block switches')
save(fig,'M-blocks-and-cooldown')

run=next(r for r in data['runs'] if r['run']=='S');events=[q for q in run['requests'] if q['id'] in ('S02','S03','D01')]
fig,axs=plt.subplots(1,3,figsize=(12,3.7),constrained_layout=True)
for ax,event in zip(axs,events):
    start=event['start'];end=event['end'];window=(start-15,end+30);samples=[r for r in data['accepted'] if r['run']=='S' and window[0]<=r['wall']<=window[1]]
    ax.plot([r['wall']-start for r in samples],[r['values']['tj'] for r in samples],'o-',c='black',ms=2,lw=.8,label='Observed 1s TJ')
    trajectory(ax,old,'S','G2','Old LS-fit','#7f7f7f',start,window,'--');trajectory(ax,new,'S','G2','D-LSM Efree','#0072b2',start,window)
    trajectory(ax,a24,'S','G2','A24 diagnostic','#d55e00',start,window)
    ax.axvline(end-start,c='black',ls=':',lw=1);ax.set(title=f"{event['id']} | actual client request",xlabel='Seconds from submit',ylabel='TJ (deg C)');ax.grid(alpha=.15)
axs[0].legend(fontsize=7);fig.suptitle('S short peaks remain underexplained; client completion is not GPU kernel completion')
save(fig,'S-short-peaks')

predictions=lines(OUT/'evaluation/D-LSM/predictions.jsonl')
fig,axs=plt.subplots(3,2,figsize=(12,9),constrained_layout=True)
for i,run in enumerate(['L','S','M']):
    start=min(r['wall'] for r in data['accepted'] if r['run']==run)
    rows=[r for r in predictions if r['run']==run and r['h']==45 and r['control_context']=='confirmed_normal' and r['label'] and all(k in r['B'] for k in ('B0','G2-HOLD','G2-RELAX30'))]
    for j,strategy in enumerate(['HOLD','RELAX30']):
        ax=axs[i,j];x=[sample_lookup[r['label']['ref']]['wall']-start for r in rows]
        def with_gaps(values):
            xx=[];yy=[]
            for k,(t,v) in enumerate(zip(x,values)):
                if k and (x[k]-x[k-1]>2.5 or rows[k]['segment']!=rows[k-1]['segment']):xx.append(np.nan);yy.append(np.nan)
                xx.append(t);yy.append(v)
            return xx,yy
        ax.plot(*with_gaps([r['label']['value'] for r in rows]),c='black',lw=.8,label='Actual TJ answer')
        ax.plot(*with_gaps([r['B']['B0'] for r in rows]),c='#009e73',lw=.7,alpha=.7,label='B0')
        ax.plot(*with_gaps([r['B']['G2-'+strategy] for r in rows]),c='#0072b2' if j==0 else '#e69f00',lw=.8,label='G2 '+strategy)
        ax.set(title=f'{run}: B45 {strategy}',ylabel='TJ (deg C)');ax.grid(alpha=.15)
axs[0,0].legend(fontsize=8);axs[0,1].legend(fontsize=8);axs[-1,0].set_xlabel('Answer time: seconds from first TJ');axs[-1,1].set_xlabel('Answer time: seconds from first TJ')
fig.suptitle('B45: two fixed future scenarios, plotted separately on identical normal-context origins/labels; in-sample theta')
save(fig,'B45-HOLD-and-RELAX30')

fig,axs=plt.subplots(1,3,figsize=(11,3.5),constrained_layout=True)
for ax,run in zip(axs,['L','S','M']):
    rows=[r for r in data['accepted'] if r['run']==run and r.get('research_segment')]
    x=[r['values']['vdd_gpu'] for r in rows];y=[r['values']['vdd_cpu_soc_mss'] for r in rows]
    ax.scatter(x,y,s=3,alpha=.3);ax.set(title=f'{run}: r={np.corrcoef(x,y)[0,1]:.5f}',xlabel='GPU rail W',ylabel='CPU/SOC/MSS rail W');ax.grid(alpha=.15)
fig.suptitle('Power inputs are separate measured rails; collinearity limits coefficient attribution')
save(fig,'rail-collinearity')

diag=read(OUT/'diagnostics/fit-diagnostics.json');fig,ax=plt.subplots(figsize=(10,3.8),constrained_layout=True)
for i,a in enumerate(diag):
    ax.scatter([i]*6,[t['J'] for t in a['attempts']],s=22,c='#0072b2',alpha=.65)
    ax.plot(i,a['J'],'rx',ms=8)
ax.set_xticks(range(len(diag)),[a['candidate'] for a in diag],rotation=15,ha='right');ax.set_ylabel('Training weighted Huber J (knee 0.3 C)');ax.grid(axis='y',alpha=.15)
ax.set_title('All six starts retained for every structure; choice uses training objective only')
save(fig,'six-start-objectives')
print('Six PNG/SVG figure pairs rendered from sealed outputs.')
