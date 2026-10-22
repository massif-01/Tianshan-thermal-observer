import json,math,statistics,csv,hashlib,collections
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'analysis';TZ=ZoneInfo('Asia/Shanghai')
def stamp(s):return datetime.fromisoformat(s).timestamp()
def local(t):return datetime.fromtimestamp(t,TZ).isoformat(timespec='milliseconds')
rows=[];ops=[];runs=[];fans_raw=[]
for run in sorted(ROOT.glob('run-*')):
    index=json.loads((run/'files.json').read_text())
    assert all(hashlib.sha256((run/n).read_bytes()).hexdigest()==h for n,h in index.items())
    m=json.loads((run/'manifest.json').read_text());summary=json.loads((run/'summary.json').read_text())
    runs.append({'path':str(run),'run_id':m['observer_run_id'],'start':stamp(m['started_at_utc']),'end':stamp(summary['ended_at_utc']),'summary':summary})
    events={e['ref']:e for e in map(json.loads,(run/'events.jsonl').read_text().splitlines()) if e.get('accepted')}
    fan=None
    for raw in map(json.loads,(run/'observations-0001.jsonl').read_text().splitlines()):
        t=stamp(raw['received_at_utc']);mono=raw['mono_s']
        if raw['kind']=='fan':
            data=(raw.get('payload') or {}).get('data',{});entries=data.get('fans',[])
            fan=next((f for f in entries if f.get('id')==0),None)
            if fan is not None:
                fan=dict(fan,mono=mono,t=t,ref=raw['ref'])
                fans_raw.append(dict(fan,run_id=m['observer_run_id']))
            continue
        if raw['ref'] not in events:continue
        e=events[raw['ref']];p=raw['payload'];v=e['values']
        validfan=fan is not None and 0<=mono-fan['mono']<=2.5 and fan.get('duty_valid') is True
        duty=fan.get('duty') if validfan else None
        if duty is not None and (not isinstance(duty,(int,float)) or not math.isfinite(duty) or not 0<=duty<=100):duty=None
        gpu=e['gpu']['value']
        d={'t':t,'local_time':local(t),'run_id':m['observer_run_id'],'ref':raw['ref'],'tj':v['tj'],'temp_cpu':v.get('temp_cpu'),'temp_gpu':v.get('temp_gpu'),'temp_soc012':v.get('temp_soc012'),'temp_soc345':v.get('temp_soc345'),'gpu':gpu,'gpu_power':v.get('vdd_gpu'),'cpu_power':v.get('vdd_cpu_soc_mss'),'vin_power':v.get('vin_sys_5v0'),'duty':duty,'fan_age_s':mono-fan['mono'] if fan else None,'fan_mode':fan.get('mode') if fan else None,'temp_stale':fan.get('temp_stale') if fan else None,'fan_fault':fan.get('fault') if fan else None,'guard_active':fan.get('guard_active') if fan else None,'ram_mb':p.get('memory',{}).get('ram',{}).get('used')}
        rows.append(d)
    ops.extend(json.loads(s) for s in (run/'operator-records.jsonl').read_text().splitlines())
late=[json.loads(s) for s in (ROOT/'late-operator-records.jsonl').read_text().splitlines()]
ops.extend(late);rows.sort(key=lambda r:r['t']);runs.sort(key=lambda r:r['start'])
markers={}
for r in ops:
    if r.get('condition_id') in (1,2,3,4,5,7) and r['kind'] not in ('collection_authorized','condition_6_continuation_reported','late_condition_transition_reported'):
        markers[r['condition_id']]=stamp(r['recorded_at_utc'])
completion=next(r for r in late if r.get('reported_completion_at_utc'))
end5=stamp(completion['reported_completion_at_utc'])
end4=datetime(2026,10,13,10,43,tzinfo=TZ).timestamp()
phases=[
 {'id':1,'label':'空载待机','start':markers[1],'end':markers[2],'boundary':'当前状态人工上报，开始和切换用写入时刻作近似边界'},
 {'id':2,'label':'模型拉起','start':markers[2],'end':markers[3],'boundary':'刚点击启动到报告拉起完成，均为人工近似边界'},
 {'id':3,'label':'驻模待机','start':markers[3],'end':markers[4],'boundary':'模型保持运行、不推理，人工近似边界'},
 {'id':4,'label':'单发推理','start':markers[4],'end':end4,'boundary':'结束只精确到10:43这个分钟；统计明确区间到10:43:00，排除10:43整分钟不确定区间'},
 {'id':5,'label':'并发推理（部分）','start':markers[5],'end':end5,'boundary':'开始以记录时刻近似；结束10:56:35.734由用户提供，最后约3分49秒未采到'},
 {'id':6,'label':'推理后驻模待机','start':end5,'end':markers[7],'boundary':'从推理完成到卸载后状态上报；只观察到10:59:15以后，实际卸载及进入空载时刻未知'},
 {'id':7,'label':'卸载后空载待机','start':markers[7],'end':runs[-1]['end'],'boundary':'用户上报已经进入；实际卸载开始/完成时间未知'},
]
def percentile(a,q):
    a=sorted(a)
    if not a:return None
    x=(len(a)-1)*q;i=int(x);j=min(i+1,len(a)-1)
    return a[i]+(a[j]-a[i])*(x-i)
def summarize(a):
    if not a:return None
    return {'n':len(a),'mean':statistics.mean(a),'median':statistics.median(a),'min':min(a),'max':max(a),'p95':percentile(a,.95),'first':a[0],'last':a[-1]}
for ph in phases:
    sample=[r for r in rows if ph['start']<=r['t']<ph['end']]
    ph['wall_duration_s']=ph['end']-ph['start'];ph['samples']=len(sample)
    ph['first_observed_at']=local(sample[0]['t']) if sample else None;ph['last_observed_at']=local(sample[-1]['t']) if sample else None
    ph['observed_interval_s']=sample[-1]['t']-sample[0]['t'] if len(sample)>1 else 0
    ph['observed_fraction']=ph['observed_interval_s']/ph['wall_duration_s']
    ph['metrics']={k:summarize([r[k] for r in sample if r[k] is not None]) for k in ('tj','temp_cpu','temp_gpu','temp_soc012','temp_soc345','gpu','gpu_power','cpu_power','vin_power','duty','ram_mb')}
    ph['fan_coverage']=ph['metrics']['duty']['n']/len(sample) if sample else None
    ph['gpu_nonzero_fraction']=sum(r['gpu'] is not None and r['gpu']>0 for r in sample)/len(sample) if sample else None
    ph['fan_state_counts']={k:dict(collections.Counter(str(r[k]) for r in sample)) for k in ('fan_mode','temp_stale','fan_fault','guard_active')}
    for r in sample:r['phase']=ph['id']
# Each metric average is the sample mean of valid new measurements; typical spacing ~1s.
# No interpolation or propagation across missing intervals; rail identity stays separate.
result={'method':'Valid new TJ samples via stored accepted refs. GPU from saved quality checks. Successful PWM as-of same run, age <=2.5s; unavailable not zero. Arithmetic sample means, no cross-gap interpolation. Human write times are approximate phase boundaries, not exact event times.','runs':runs,'phases':phases,'gap':{'start':runs[0]['end'],'end':runs[1]['start'],'seconds':runs[1]['start']-runs[0]['end']},'uncertain_end4_interval':{'start':end4,'end':end4+60},'total_new_samples':len(rows),'total_raw_records':sum(r['summary']['observations'] for r in runs),'fan_modes_observed':dict(collections.Counter(f['mode'] for f in fans_raw)),'global_peaks':{k:max((r for r in rows if r[k] is not None),key=lambda r:r[k]) for k in ('tj','gpu','gpu_power','cpu_power','vin_power','duty')}}
(OUT/'statistics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'operator-records-consolidated.json').write_text(json.dumps(ops,ensure_ascii=False,indent=2)+'\n')
with (OUT/'measurements.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0])+(['phase'] if 'phase' not in rows[0] else []));writer.writeheader();writer.writerows(rows)
for ph in phases:
    ms=ph['metrics']
    def get(k,field='mean'):return round(ms[k][field],3) if ms[k] else None
    print(ph['id'],ph['label'],ph['samples'],ph['first_observed_at'],ph['last_observed_at'],{'tj_mean':get('tj'),'tj_max':get('tj','max'),'tj_first':get('tj','first'),'tj_last':get('tj','last'),'gpu_mean':get('gpu'),'gpu_max':get('gpu','max'),'gpu_nonzero':round(ph['gpu_nonzero_fraction'],3),'PGPU':get('gpu_power'),'PCPU':get('cpu_power'),'P5V':get('vin_power'),'duty_mean':get('duty'),'duty_min':get('duty','min'),'duty_max':get('duty','max'),'duty_first':get('duty','first'),'duty_last':get('duty','last'),'fan_coverage':round(ph['fan_coverage'],3),'RAMfirst':get('ram_mb','first'),'RAMlast':get('ram_mb','last')})
print('Peak TJ',result['global_peaks']['tj']['tj'],result['global_peaks']['tj']['local_time'])
