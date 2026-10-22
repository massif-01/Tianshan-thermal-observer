"""Standard Matplotlib static figures; observed surface points never joined as dense truth."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager,FontProperties


def main(source,out):
    data=json.loads(Path(source).read_text());out=Path(out)
    for p in ['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/System/Library/Fonts/STHeiti Medium.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if Path(p).exists():
            fontManager.addfont(p);plt.rcParams['font.family']=FontProperties(fname=p).get_name();break
    plt.rcParams['axes.unicode_minus']=False
    sessions=list(data['sessions']) or [None]
    fig,axes=plt.subplots(3,len(sessions),figsize=(max(9,7*len(sessions)),10),squeeze=False,sharex='col')
    fig.suptitle('局部表面独立对照｜'+('合成数值演示，未进行现场测温' if data['summary']['status']=='synthetic_demo_only' else '外部未测；物理对应未验证' if data['summary']['status']=='not_measured' else '未经标定；不是Ts准确率'),fontsize=16)
    for col,sid in enumerate(sessions):
        s=data['sessions'].get(sid)
        rows=[r for r in data['trajectory'] if s is None or r['run_id']==s['run_id']]
        pairs=[p for p in data['paired'] if p['record']['session_id']==sid]
        start=min((r['utc_s'] for r in rows),default=0)
        telemetry=[r for r in data.get('measured_telemetry',[]) if s is None or r['run_id']==s['run_id']]
        if telemetry:
            tx=[];ty=[];prev=None
            for r in telemetry:
                if prev and (r['utc_s']>=prev['source_valid_until_utc_s'] or r['source_epoch']!=prev['source_epoch']):tx.append(np.nan);ty.append(np.nan)
                tx.append(r['utc_s']-start);ty.append(r['measured_TJ_C']);prev=r
            axes[0,col].plot(tx,ty,color='#202d3c',lw=1.2,label='实测TJ（独立保留）')
        for key,label,color,style in [('measured_TJ_C','实测TJ','#202d3c','-'),('Tf_A_long_C','原G2 Tf：TJ估计','#ad4b34','--'),
                ('STATE_G2_C','因果G2潜在Ts','#bb4d3c','-'),('STATE_LP30_C','同G2的QS经LP30','#167f92','-')]:
            if key=='measured_TJ_C' and telemetry:continue
            x=[];y=[];prev=None
            for r in rows:
                if prev and (prev['segment']!=r['segment'] or prev['valid_until_utc_s']<r['utc_s']):x.append(np.nan);y.append(np.nan)
                x.append(r['utc_s']-start);y.append(r[key] if r.get(key) is not None else np.nan);prev=r
            axes[0,col].plot(x,y,style,lw=1.3,label=label,color=color)
        axes[0,col].set_title((s['site_id']+'｜'+s['measurement_kind']) if s else '无外部会话：已有冻结轨迹')
        axes[0,col].set_ylabel('绝对读数/潜在状态（°C）\n未经局部表面标定')
        for pair in pairs:
            rec=pair['record'];v=rec['temperature_c'];timing=pair['time_alignment']
            interval=timing.get('interval_utc_s')
            if v is None:continue
            if interval is None:
                center=timing.get('center_interval_utc_s')
                if center:axes[0,col].scatter((center[0]+center[1])/2-start,v,marker='s',color='#888',label='时间误差未知，仅材料' if '时间误差未知，仅材料' not in axes[0,col].get_legend_handles_labels()[1] else None)
                continue
            center=(interval[0]+interval[1])/2-start;error=(interval[1]-interval[0])/2
            qualified=pair['model_match']['ranges'] is not None
            label=('CSV原始采样点' if rec.get('input_path')=='numeric_export' else '局部表面人工点') if qualified else '仅保留原值：无对照资格'
            axes[0,col].errorbar(center,v,xerr=error,fmt='o',ms=3 if rec.get('input_path')=='numeric_export' else 5,
                color='#3d9b57' if qualified else '#bc852d',capsize=2,
                label=label if label not in axes[0,col].get_legend_handles_labels()[1] else None)
            if pair['delta']:
                delta=pair['delta'];axes[1,col].errorbar(center,delta['external_delta_C'],xerr=error,fmt='o',color='#3d9b57',capsize=4)
                for key,color in [('STATE_G2_C','#bb4d3c'),('STATE_LP30_C','#167f92')]:
                    val=delta['models'][key]
                    if val:
                        a,b=val['model_delta_range_C'];axes[1,col].vlines(center,a,b,color=color,lw=3)
                        axes[1,col].scatter(center,(a+b)/2,color=color,marker='x')
        axes[1,col].set_ylabel('一次固定参考后的增量（°C）\n绿点=表面，红×=G2，蓝×=LP30')
        if not any(p['delta'] for p in pairs):axes[1,col].text(.5,.5,'无合法固定参考配对\n不自动挑背景、不每阶段归零',ha='center',va='center',transform=axes[1,col].transAxes,color='#666')
        x=[r['utc_s']-start for r in rows];y=[r['actual_successful_PWM_percent_at_state_origin'] for r in rows]
        # Separate units; display original successful snapshots only, no new actuator command.
        axes[2,col].scatter(x,y,s=2,color='#4a6078',label='原状态采样时的成功PWM')
        axes[2,col].set_ylabel('原成功PWM（%）');axes[2,col].set_xlabel('距所供轨迹窗口起点（秒）；各面板独立纵轴')
        for row in range(3):
            if rows:axes[row,col].set_xlim(min(r['utc_s'] for r in rows)-start,max(r['utc_s'] for r in rows)-start)
            if pairs and all(p['record'].get('input_path')=='numeric_export' for p in pairs):
                windows=[p['time_alignment'].get('interval_utc_s') for p in pairs]
                windows=[w for w in windows if w]
                if windows:axes[row,col].set_xlim(min(w[0] for w in windows)-start-2,max(w[1] for w in windows)-start+2)
            axes[row,col].grid(alpha=.18)
            h,l=axes[row,col].get_legend_handles_labels()
            if l:axes[row,col].legend(fontsize=8,loc='best')
    fig.text(.5,.01,'原始外部点不插值；连续CSV面板显示导入时段，完整轨迹仍保留。横棒=时间区间，模型竖线=范围；局部表面不等于空气/整块均温/Ts。',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96))
    fig.savefig(out/'同测点对照.png',dpi=150);fig.savefig(out/'同测点对照.svg');plt.close(fig)
    print('中文对照图已生成，外部点未插值/连成连续真值。')


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
