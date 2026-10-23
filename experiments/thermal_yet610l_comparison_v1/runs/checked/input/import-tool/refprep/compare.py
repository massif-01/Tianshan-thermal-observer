"""Independent external-reference description: as-of/ranges, never curve fitting."""
from pathlib import Path
from collections import Counter,defaultdict
import bisect
import html
import os
import shutil
import subprocess
import sys
from .files import read,write,lines,sha,dump_lines
from .records import latest_records,load_session
from .clocks import align_time

FIELDS=['measured_TJ_C','Tf_A_long_C','Ts_A_long_C','STATE_G2_C','STATE_LP30_C','STATE_QS_C','STATE_LP120_C',
        'actual_successful_PWM_percent_at_state_origin']


def asof_interval(rows,start,end):
    """Piecewise as-of values only. Original freshness cannot be extended or crossed."""
    if not rows:return dict(status='trajectory_run_missing',ranges=None)
    times=[r['utc_s'] for r in rows]
    i=bisect.bisect_right(times,start)-1
    if i<0:return dict(status='before_first_legal_state',ranges=None)
    first=rows[i];selected=[first]
    if start>=first['valid_until_utc_s']:return dict(status='asof_state_expired',ranges=None)
    cursor=start
    while i+1<len(rows) and rows[i+1]['utc_s']<=end:
        nxt=rows[i+1]
        if rows[i]['valid_until_utc_s']<nxt['utc_s']:
            return dict(status='interval_crosses_quality_gap',ranges=None)
        if (nxt['segment'],nxt.get('source_epoch'))!=(first['segment'],first.get('source_epoch')):
            return dict(status='interval_crosses_source_or_segment_boundary',ranges=None)
        selected.append(nxt);i+=1;cursor=nxt['utc_s']
    if end>=rows[i]['valid_until_utc_s']:
        return dict(status='interval_reaches_expiry_or_missing_future_state',ranges=None)
    ranges={}
    for key in FIELDS:
        values=[r.get(key) for r in selected]
        ranges[key]=[min(values),max(values)] if all(v is not None for v in values) else None
    assert all(r['state_input_cutoff_utc_s']<=r['utc_s'] for r in selected)
    return dict(status='matched_asof' if start==end else 'matched_whole_interval_range',ranges=ranges,
        source_refs=[r['ref'] for r in selected],segment=first['segment'],
        first_asof_lag_s=start-first['utc_s'],query_interval_utc_s=[start,end],
        method='all legal as-of values/range, never closest-temperature point or interpolation')


def coverage(rows):
    if not rows:return dict(rows=0,span_s=0,legal_asof_hold_s=0)
    duration=0.;demand_duration=0.
    for i,r in enumerate(rows):
        next_time=rows[i+1]['utc_s'] if i+1<len(rows) else r['valid_until_utc_s']
        valid=max(0,min(next_time,r['valid_until_utc_s'])-r['utc_s'])
        duration+=valid
        if r.get('offline_extra_demand') is not None:demand_duration+=valid
    span=rows[-1]['valid_until_utc_s']-rows[0]['utc_s']
    return dict(rows=len(rows),span_s=span,legal_asof_hold_s=duration,
        legal_asof_fraction=duration/span if span else None,
        demand_legal_hold_s=demand_duration,
        population='only supplied frozen trajectory window; not whole-run historical forecast coverage')


def pick_plot_python(explicit=None):
    candidates=[explicit] if explicit else [sys.executable,'/private/tmp/tto-analysis-20261013-env/bin/python']
    for value in candidates:
        if value and Path(value).is_file():
            r=subprocess.run([str(value),'-c','import matplotlib'],capture_output=True)
            if r.returncode==0:return str(value)
    return None


def source_report_text(summary):
    """One result-owned description for JSON, Markdown and HTML; flags are declarations."""
    declared=summary['real_numeric_points'];synthetic=summary['synthetic_numeric_points']
    if not declared and not synthetic:
        source='no_numeric_records'
        message='未导入外部数值记录；现有遥测、冻结状态和覆盖仍可读取。'
    elif not declared:
        source='synthetic_only'
        message='本报告外部数值均为合成演示，不构成现场测温证据。'
    elif not synthetic:
        source='declared_external_only'
        message='已导入按输入声明分类的外部测量记录；仪表/探头响应及局部表面与Ts的物理对应尚未验证。'
    else:
        source='mixed_declared_external_and_synthetic'
        message='本报告包含按输入声明分类的外部测量记录和合成数值；两类分别计数，合成值不计为现场测温证据。'
    return dict(source_status=source,measurement_status=message,
        counts=f"数值点{summary['numeric_points']}；声明为外部测量的数值点{declared}；合成点{synthetic}；配对点{summary['paired_points']}。n是记录点，不是独立试验。",
        format_status='尚无真实YET-610L样例验收回执；通用导入不代表厂商格式已验收。',
        validation_status='输入类别不证明品牌、校准或现场来源；仪表精度、探头安装/响应及表面与Ts的物理对应未验证。')


def compare(store,trajectory,output,plot_python=None,draw=True):
    store=Path(store);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if output==store or output==Path(trajectory):raise ValueError('Report output must be separate from original inputs')
    records=latest_records(store)
    traj=lines(trajectory);byrun=defaultdict(list)
    for row in traj:
        if row.get('external_temperature_used') or row.get('parameter_learning'):raise ValueError('Trajectory is not an independent frozen reference')
        byrun[row['run_id']].append(row)
    for rows in byrun.values():rows.sort(key=lambda r:r['utc_s'])
    sessions={r['session_id']:load_session(store,r['session_id']) for r in records}
    if (store/'sessions').exists():
        for path in sorted((store/'sessions').glob('*.json')):
            s=read(path);sessions[s['session_id']]=s
    joined=[]
    events=lines(store/'session-events.jsonl')
    for rec in records:
        rows=byrun.get(rec['run_id'],[])
        pair=dict(run_id=rec['run_id'],utc_s=rows[0]['utc_s'],mono_s=rows[0]['mono_s']) if rows else None
        timing=align_time(rec,sessions[rec['session_id']],pair)
        window=timing['interval_utc_s']
        match=asof_interval(rows,*window) if window else dict(status=timing['status'],ranges=None)
        for event in events:
            if event['session_id']!=rec['session_id'] or not event['event_type'].startswith('probe_'):continue
            event_window=align_time(event,sessions[rec['session_id']],pair)['interval_utc_s']
            if event_window is None or (window and window[1]>=event_window[0]):
                match=dict(status='probe_integrity_event_requires_new_session' if event_window else 'probe_event_time_unknown_session_integrity_unverified',
                           ranges=None,event_id=event['event_id'])
        joined.append(dict(record=rec,time_alignment=timing,model_match=match,
                           delta=None,reference_status='not_predeclared',physical_mapping_validated=False))
    byrecord={(x['record']['session_id'],x['record']['record_id']):x for x in joined}
    for row in joined:
        rec=row['record'];session=sessions[rec['session_id']]
        ref_id=session.get('reference_record_id')
        ref=byrecord.get((rec['session_id'],ref_id))
        if not ref_id:continue
        if ref is None:row['reference_status']='predeclared_reference_not_measured';continue
        if ref['record']['temperature_c'] is None or rec['temperature_c'] is None:
            row['reference_status']='reference_or_current_has_no_numeric_reading';continue
        if row['model_match']['ranges'] is None or ref['model_match']['ranges'] is None:
            row['reference_status']='reference_or_current_not_time_paired';continue
        delta=rec['temperature_c']-ref['record']['temperature_c']
        values={}
        for key in ['STATE_G2_C','STATE_LP30_C','STATE_QS_C','STATE_LP120_C']:
            a=row['model_match']['ranges'][key];b=ref['model_match']['ranges'][key]
            if a is None or b is None:values[key]=None;continue
            dr=[a[0]-b[1],a[1]-b[0]]
            sign='uncertain_or_zero' if dr[0]<=0<=dr[1] or delta==0 else (
                'same_direction' if (dr[0]>0)==(delta>0) else 'different_direction')
            values[key]=dict(model_delta_range_C=dr,
                external_minus_model_delta_range_C=[delta-dr[1],delta-dr[0]],
                direction=sign,interpretation='uncalibrated descriptive difference, NOT Ts accuracy')
        row['delta']=dict(reference_record_id=ref_id,external_delta_C=delta,models=values,
            one_reference_per_session=True,reference_not_cold_or_equilibrium=True,
            measurement_quality_provisional=bool(session.get('quality_limitations')),
            temperature_uncertainty_unknown=session.get('instrument',{}).get('accuracy') is None)
        row['reference_status']='one_fixed_reference_used'
    numeric=[x for x in joined if x['record']['temperature_c'] is not None]
    real=[x for x in numeric if not x['record']['synthetic']]
    status='not_measured' if not numeric else ('synthetic_demo_only' if not real else 'descriptive_unvalidated_surface_reference')
    summary=dict(contract='TTO-REF-PREP-v1.0',status=status,physical_mapping_validated=False,
        surface_measurement_performed=bool(real),instrument_profile_confirmed=False,
        instrument_selection_confirmed_by_user='YET-610L + K型探头；耐温聚酰亚胺胶带已购买',
        real_YET_CSV_mapping_accepted=False,continuous_logging_field_verified=False,
        model_refit=False,external_model_input=False,control_authorization='none',
        distinct_records=len(records),history_revisions=len(lines(store/'records.jsonl')),
        numeric_points=len(numeric),real_numeric_points=len(real),synthetic_numeric_points=len(numeric)-len(real),
        paired_points=sum(x['model_match']['ranges'] is not None and x['record']['temperature_c'] is not None for x in joined),
        unpaired_reasons=dict(Counter(x['model_match']['status'] for x in joined if x['model_match']['ranges'] is None)),
        reference_statuses=dict(Counter(x['reference_status'] for x in joined)),
        trajectory_sha256=sha(trajectory),coverage={r:coverage(rows) for r,rows in byrun.items()},
        model_sha256=sorted({r['model_sha256'] for r in traj}),
        sparse_peak='peak_not_directly_observed; sparse samples do not establish complete peak or second-scale lag',
        import_quality=lines(store/'imports.jsonl'),session_events=events,
        continuous_limit='1s target is sampling cadence, not calibrated probe response or automatically valid surface/Ts mapping',
        ambient='only original M had user-confirmed 24C; no automatic assignment to any new run',
        sessions={k:dict(run_id=v['run_id'],site_id=v['site_id'],measurement_kind=v['measurement_kind'],
            statistic=v.get('geometry',{}).get('statistic'),absolute_status=v['absolute_status'],
            quality_limitations=v.get('quality_limitations',[]),reference_record_id=v.get('reference_record_id')) for k,v in sessions.items()},
        figures=dict(status='not_requested'))
    summary['report_text']=source_report_text(summary)
    dump_lines(output/'paired-points.jsonl',joined)
    write(output/'comparison.json',summary)
    telemetry_path=Path(trajectory).with_suffix('.telemetry.jsonl')
    telemetry=lines(telemetry_path)
    summary['measured_telemetry_sha256']=sha(telemetry_path) if telemetry_path.exists() else None
    chart=dict(summary=summary,sessions=sessions,paired=joined,trajectory=traj,measured_telemetry=telemetry)
    write(output/'chart-data.json',chart)
    if draw:
        exe=pick_plot_python(plot_python)
        if exe:
            env=os.environ.copy();env['MPLCONFIGDIR']=str(output/'plot-cache')
            worker=Path(__file__).absolute().parent.parent/'plot_reference.py'
            r=subprocess.run([exe,str(worker),str(output/'chart-data.json'),str(output)],env=env,capture_output=True,text=True)
            (output/'plot.log').write_text(r.stdout+r.stderr)
            if r.returncode:raise ValueError('Local plot failed; see plot.log')
            summary['figures']=dict(status='generated',runtime=exe)
        else:summary['figures']=dict(status='matplotlib_unavailable',note='JSON/Markdown/HTML report complete; plotting requires local Matplotlib only')
    write(output/'comparison.json',summary)
    _report(output,summary,joined)
    return summary


def _report(output,summary,joined):
    reasons='；'.join(f'{k}: {v}' for k,v in summary['unpaired_reasons'].items()) or '无'
    wording=summary['report_text'];intro=wording['measurement_status']
    rows=[]
    for row in joined:
        rec=row['record'];m=row['model_match'];delta=row['delta']
        rows.append([rec['record_id'],rec['session_id'],rec['measurement_kind'],str(rec['temperature_c']),
            str(rec['measured_at_raw'] if rec['measured_at_raw'] is not None else rec['measured_interval_raw'] or '未知'),m['status'],
            str(delta['external_delta_C']) if delta else '—',', '.join(rec['measurement_flags'])])
    header=['记录','会话/测点','被测对象','表面读数°C','原始测量时间','配对资格','固定参考温升°C','限制']
    md=['# 外部局部表面参照：中文对照报告',intro,
        wording['counts'],wording['format_status'],wording['validation_status'],
        '未配对原因：'+reasons,
        'TJ是实测目标；Tf A-long是原G2的TJ估计；Ts与LP30是潜在状态。接触探头及红外均只代表所选局部表面，不是出风空气、整块结构平均温度或直接测得Ts；背板另列。',
        '一个同run/同测点/同设置会话只使用预登记参考一次；不按阶段重置、不调时、不缩放。时间区间给完整模型范围，不挑最接近温度的点。接触式不要求IR发射率/反射/ROI，仪表精度、表面接触和探头响应仍须单列；IR备用路径不默认金属0.95。',
        '仪表采样、记录开始锚点、导出、导入、提醒、按键各自保存。连续CSV相邻等温行不去重；缺失/异常行保留原因，不补零不插值。每秒采样不等于已标定探头响应；稀疏点不证明完整峰值。']
    table=['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']
    table+=['| '+' | '.join(str(c).replace('|','／').replace('\n',' ') for c in row)+' |' for row in rows]
    md.append('\n'.join(table))
    md+=['','冻结轨迹覆盖（仅所提供窗口，原有效期未延长）：',
         '```json',__import__('json').dumps(summary['coverage'],ensure_ascii=False,indent=2),'```',
         '图表状态：'+summary['figures']['status']+'。',
         '物理对应未验证；未训练模型，未改变风扇，未授予控制权。24°C只属于旧M，不复制到新过程。']
    md+=['连续CSV导入与会话事件：','```json',__import__('json').dumps(dict(imports=summary['import_quality'],events=summary['session_events']),ensure_ascii=False,indent=2),'```']
    (output/'中文对照报告.md').write_text('\n\n'.join(md)+'\n')
    body=''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows)
    figure='<img src="同测点对照.png" alt="同测点绝对读数、一次参考增量、现场PWM">' if summary['figures']['status']=='generated' else '<p>本环境未生成图；所有配对/范围/覆盖保留在JSON与表格。</p>'
    status_text=''.join('<p>'+html.escape(wording[key])+'</p>' for key in ['counts','format_status','validation_status'])
    (output/'中文对照报告.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>局部表面独立对照</title><style>body{font-family:system-ui;margin:24px;line-height:1.7;color:#253348}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:7px}img{max-width:100%}p{max-width:1100px}</style><h1>局部表面参照：'+html.escape(summary['status'])+'</h1><p>'+html.escape(intro)+'</p>'+status_text+'<p>三种时钟与写入记录分开；普通伪彩图不做数值解码。局部表面不等于Ts，外部点不进入模型；空测温不阻挡其他软件/建模。</p>'+figure+'<table><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in header)+'</tr>'+body+'</table><p>未配对原因：'+html.escape(reasons)+'</p><p>稀疏点不能证明完整峰值、秒级时滞或物理热容；未联网设备、未改变控制。完整模型取值范围、源引用及限制见paired-points.jsonl。</p></html>')
