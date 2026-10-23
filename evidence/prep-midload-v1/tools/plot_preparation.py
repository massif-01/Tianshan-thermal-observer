"""Figures read the same saved JSON used by the report; no modelling."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parents[1];out=root/'results/charts';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
def read(p):return json.loads((root/p).read_text())
poll=read('results/polling-before-after.json')
fig,ax=plt.subplots(1,2,figsize=(11,3.5),gridspec_kw={'width_ratios':[2,1]})
for i,key in enumerate(('before','after')):
    d=poll[key];start=min(t['t'] for t in d['trace']);times=np.array(d['fan_return_times'])-start
    ax[0].scatter(times,np.full(len(times),i),s=38,label=f'{key}: fan returns')
    temps=[x for x in d['trace'] if x['endpoint']=='temp'];pairs=[];sent=None
    for e in temps:
        if e['event']=='sent':sent=e['t']
        elif sent is not None:pairs.append((sent-start,e['t']-sent));sent=None
    ax[0].broken_barh(pairs,(i-.18,.12),facecolors='#666666',alpha=.35)
ax[0].set(yticks=[0,1],yticklabels=['Old sequential','Independent 0.2.3'],xlabel='Seconds since first HTTP launch',title='Owned loopback: fan 1s / temp 5s')
ax[0].set_ylim(-.5,1.5);ax[0].grid(axis='x',alpha=.2)
gaps=[max(poll[k]['fan_return_gaps']) for k in ('before','after')]
ax[1].bar(['Old','0.2.3'],gaps,color=['#888888','#287894'])
ax[1].axhline(2.5,color='#b34a36',ls='--',lw=1,label='Unchanged fan TTL: 2.5s')
for i,g in enumerate(gaps):ax[1].text(i,g+.05,f'{g:.3f}s',ha='center')
ax[1].set(ylabel='Maximum fan return gap (s)',ylim=(0,3.2));ax[1].legend(loc='upper right',fontsize=8)
fig.text(.02,.015,'Dots = actual received fan responses. Shaded spans = actual temp requests. Device timing has not been tested.',fontsize=8)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'polling-before-after.png');plt.close(fig)

wf=read('results/availability-v2/waterfall.json');methods=['B0','B1','R_TJ','R_IO','G2-HOLD']
rows=[next(r for r in wf if r['experiment']=='F-LS' and r['scope']=='continuous_short' and r['h']==45 and r['method']==m) for m in methods]
fig,ax=plt.subplots(figsize=(10,3.7));left=np.zeros(len(rows))
for key,label,color in [('confirmed_normal','Confirmed normal','#33816e'),('aux_observation_gap','Auxiliary visibility gap','#d49a35'),('observed_abnormal_or_changed','Observed abnormal / changed','#b65750')]:
    values=np.array([r['subsets'][key] for r in rows]);ax.barh(methods,values,left=left,label=label,color=color)
    for i,v in enumerate(values):
        if v:ax.text(left[i]+v/2,i,str(v),ha='center',va='center',fontsize=9)
    left+=values
missing=np.array([r['raw_TJ']-r['saved_predictions'] for r in rows]);ax.barh(methods,missing,left=left,label='No saved prediction',color='#dddddd')
ax.set(xlim=(0,178),xlabel='Origins (raw TJ denominator = 169)',title='Continuous short QA, L-fit to S-check, 45s')
ax.invert_yaxis();ax.legend(loc='lower right',fontsize=8);ax.grid(axis='x',alpha=.15)
fig.text(.02,.01,'Old strict normal answers: 6. Frozen prediction values unchanged; no missing predictions recreated.',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(out/'availability-45s.png');plt.close(fig)

ev=read('results/availability-v2/event-metrics.json');ids=['S02','S03','D01'];rows=[next(r for r in ev if r['event']['id']==i) for i in ids]
fig,ax=plt.subplots(figsize=(8,3.7));x=np.arange(3);width=.23
for j,(key,label,color) in enumerate([('actual','Measured','#444444'),('G1','Frozen G1','#819fa7'),('G2','Frozen G2','#267c93')]):
    values=[r['model_peak_comparison']['G2']['actual_peak_C'] if key=='actual' else r['model_peak_comparison'][key]['model_peak_C'] for r in rows]
    ax.bar(x+(j-1)*width,values,width,label=label,color=color)
    for k,v in enumerate(values):ax.text(x[k]+(j-1)*width,v+.04,f'{v:.2f}',ha='center',fontsize=8)
ax.set(xticks=x,xticklabels=[f'{i} (n={r["model_peak_comparison"]["G2"]["common_n"]})' for i,r in zip(ids,rows)],ylabel='TJ peak (C)',ylim=(44,50.2),title='Same valid timestamps: pooled free response')
ax.legend(loc='upper left',fontsize=8);ax.grid(axis='y',alpha=.2)
fig.text(.02,.01,'Existing development data; in-sample model response. Peak window = submit to client end + 5s. Not future prediction.',fontsize=8)
fig.tight_layout(rect=(0,.06,1,1));fig.savefig(out/'pulse-peaks.png');plt.close(fig)
(out/'plot-environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'matplotlib':matplotlib.__version__,'numpy':np.__version__,
   'inputs':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ('results/polling-before-after.json','results/availability-v2/waterfall.json','results/availability-v2/event-metrics.json')}},indent=2)+'\n')
