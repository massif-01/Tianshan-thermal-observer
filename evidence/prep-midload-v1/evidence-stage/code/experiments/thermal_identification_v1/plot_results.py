"""Static, exportable scientific plots; run with the recorded plotting environment."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).open()]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=a.output;out.mkdir(parents=True,exist_ok=False);root=a.run;data=read(root/'data.json')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130,'savefig.dpi':170})
    def save(fig,name):
        fig.savefig(out/f'{name}.png',bbox_inches='tight');fig.savefig(out/f'{name}.svg',bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(4,2,figsize=(15,11),sharex='col',layout='constrained')
    starts={}
    for col,run in enumerate(('L','S')):
        rows=[r for r in data['accepted'] if r['run']==run];start=rows[0]['mono_s'];starts[run]=start;t=np.array([r['mono_s']-start for r in rows])/60
        ax[0,col].plot(t,[r['values']['tj'] for r in rows],color='#152532',lw=.8,label='Accepted TJ')
        for field,color,label in [('vdd_gpu','#287fa5','GPU'),('vdd_cpu_soc_mss','#b87820','CPU/SOC/MSS'),('vin_sys_5v0','#888888','5V (diagnostic)')]:
            ax[1,col].plot(t,[r['values'][field] for r in rows],lw=.7,color=color,label=label)
        ax[2,col].plot(t,[r['values'].get('duty') if r['values'].get('duty') is not None else np.nan for r in rows],color='#794999',lw=.8,label='Successful PWM')
        for s in data['segments']:
            if s['run']!=run:continue
            x=(s['rows'][0]['mono_s']-start)/60;width=s['span_s']/60
            ax[3,col].broken_barh([(x,width)],(.15,.25),facecolors='#248772')
            ax[3,col].broken_barh([(x,min(width,1))],(.48,.25),facecolors='#dbb25c')
        ax[0,col].set_title(f'{run}: {len(rows)} accepted samples; one physical episode')
        ax[3,col].set_yticks([.28,.6],['valid input span','60 s initialization']);ax[3,col].set_ylim(0,.9);ax[3,col].set_xlabel('Minutes from first accepted sample')
        ax[0,col].set_ylabel('TJ (C)');ax[1,col].set_ylabel('Independent rails (W)');ax[2,col].set_ylabel('PWM (%)')
        for j in range(4):ax[j,col].grid(alpha=.18)
        ax[1,col].legend(fontsize=8,ncol=3)
    fig.suptitle('Recorded data and strict continuous coverage (no interpolation through TTL gaps)',fontsize=15)
    save(fig,'01-inputs-and-coverage')
    fig,axs=plt.subplots(4,1,figsize=(15,12),layout='constrained')
    for ax,(eid,run) in zip(axs,[('F-LS','S'),('F-SL','L'),('F-POOL','L'),('F-POOL','S')]):
        rows=[r for r in data['accepted'] if r['run']==run];start=starts[run]
        ax.plot([(r['mono_s']-start)/60 for r in rows],[r['values']['tj'] for r in rows],c='#111111',lw=.9,label='Recorded TJ')
        pred=[r for r in lines(root/'evaluation'/eid/'A-long.jsonl') if r['run']==run]
        for k,model in enumerate(('G1','G2')):
            for j,seg in enumerate(sorted({r['segment'] for r in pred})):
                group=[r for r in pred if r['segment']==seg]
                ax.plot([(r['t']-start)/60 for r in group],[r['A'][model] for r in group],lw=1.1,c=['#c9792d','#168b88'][k],label=model if j==0 else None)
        ax.set_title(f'{eid}, target {run}: '+('in-sample parameters AND initial states' if eid=='F-POOL' else 'parameters frozen on other run; causal 60 s prefix'))
        ax.set_ylabel('Temperature (C)');ax.set_xlabel('Minutes');ax.grid(alpha=.15);ax.legend(loc='upper left',ncol=3)
    fig.suptitle('A-long: known recorded inputs; no TJ feedback after initialization',fontsize=15)
    save(fig,'02-free-response')
    models=['B0','B1','R_TJ','R_IO','G1-HOLD','G1-RELAX30','G2-HOLD','G2-RELAX30']
    fig,axs=plt.subplots(1,2,figsize=(16,7),layout='constrained',gridspec_kw={'width_ratios':[1,2]})
    def heat(ax,values,labels,title):
        vals=np.array(values).T;im=ax.imshow(vals,aspect='auto',cmap='YlOrRd',norm=LogNorm(vmin=.05,vmax=max(10,np.nanmax(vals))))
        ax.set_xticks(range(len(labels)),labels,rotation=30,ha='right');ax.set_yticks(range(len(models)),models);ax.set_title(title)
        for i in range(vals.shape[0]):
            for j in range(vals.shape[1]):
                if np.isfinite(vals[i,j]):ax.text(j,i,f'{vals[i,j]:.3f}',ha='center',va='center',color='white' if vals[i,j]>4 else 'black',fontsize=9)
        fig.colorbar(im,ax=ax,label='45 s time-weighted MAE (C)',shrink=.75)
    values=[];labels=[]
    for eid in ('F-LS','F-SL','F-POOL'):
        metrics=read(root/'evaluation'/eid/'B-metrics.json');r=next(r for r in metrics if r['h']==45 and r['scope']=='all' and r['layer']=='all_methods')
        values.append([r['metrics'][m]['mae'] for m in models]);labels.append(f'{eid}\nn={r["metrics"]["B0"]["n"]}')
    heat(axs[0],values,labels,'B only: identical origin + label sets')
    metrics=read(root/'evaluation/F-POOL/B-metrics.json');groups=[r for r in metrics if r['h']==45 and r['scope']=='regime' and r['layer']=='all_methods']
    heat(axs[1],[[r['metrics'][m]['mae'] for m in models] for r in groups],[f'{r["value"]}\nn={r["metrics"]["B0"]["n"]}' for r in groups],'F-POOL regimes: in-sample description only')
    fig.suptitle('Future input scenarios are fixed separately; no per-point oracle selection',fontsize=15)
    save(fig,'03-causal-forecast-comparison')
    fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    params=read(root/'diagnostics/parameters.json')
    for ax,eid in zip(axs[:2],['F-LS','F-SL']):
        row=next(r for r in params if r['experiment']==eid and r['model']=='G2')
        for key,label in [('weighted_raw_residual_full','incl. nuisance'),('projected_dynamic','dynamic after nuisance projection')]:
            s=np.array(row[key]['singular_values']);ax.semilogy(np.arange(1,len(s)+1),s/s[0],'.-',label=label)
        ax.set_ylim(1e-20,2);ax.set_title(f'{eid} / G2 sensitivity');ax.set_xlabel('Singular value index');ax.set_ylabel('Relative singular value');ax.grid(alpha=.2);ax.legend(fontsize=8)
    state=read(root/'diagnostics/state-sensitivity.json');v=[next(r for r in state if r['experiment']==eid and r['h']==45 and r['mode']=='HOLD') for eid in ['F-LS','F-SL']]
    x=np.arange(2);axs[2].bar(x-.18,[r['mae60'] for r in v],.36,label='60 s history');axs[2].bar(x+.18,[r['mae180'] for r in v],.36,label='180 s history')
    axs[2].set_xticks(x,[f'{r["experiment"]}\nn={r["n"]}' for r in v]);axs[2].set_ylabel('45 s HOLD MAE (C)');axs[2].set_title('Fixed state-window sensitivity\nSame >=180 s origins');axs[2].legend();axs[2].grid(axis='y',alpha=.2)
    save(fig,'04-identifiability-and-state')
    requests=read(root/'evaluation/F-LS/request-windows.json');ids=sorted({r['request'] for r in requests if r['request']!='P01'},key=lambda q:(q.startswith('D'),q))
    windows=['pre15','during','post0_15','post15_45','post45_90'];Z=np.zeros((len(ids),len(windows)));notes=[]
    for i,q in enumerate(ids):
        note=[]
        for j,w in enumerate(windows):
            r=next(r for r in requests if r['request']==q and r['window']==w and r['h']==45)
            Z[i,j]=r['shared_n']/max(1,r['raw_accepted']);note.append(f'{r["shared_n"]}/{r["raw_accepted"]}'+('*' if r['any_other_request_overlap'] else ''))
        notes.append(note)
    fig,ax=plt.subplots(figsize=(9,11),layout='constrained');im=ax.imshow(Z,vmin=0,vmax=1,cmap='Blues',aspect='auto')
    ax.set_xticks(range(len(windows)),windows);ax.set_yticks(range(len(ids)),ids)
    for i in range(len(ids)):
        for j in range(len(windows)):ax.text(j,i,notes[i][j],ha='center',va='center',color='white' if Z[i,j]>.65 else 'black')
    ax.set_title('Short requests: shared 45 s forecast origins / raw accepted points\n* another request overlaps this window; requests are not independent episodes')
    fig.colorbar(im,ax=ax,label='Common comparison coverage',shrink=.65);save(fig,'05-request-coverage')
    (out/'plot-environment.json').write_text(json.dumps({'matplotlib':matplotlib.__version__,'numpy':np.__version__,'source':'saved results only; no refit'},indent=2)+'\n')


if __name__=='__main__':main()
