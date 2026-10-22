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
def percentile(a,q):
    a=sorted(a)
    if not a:return None
    x=(len(a)-1)*q;i=int(x);j=min(i+1,len(a)-1)
    return a[i]+(a[j]-a[i])*(x-i)
def summarize(a):
    if not a:return None
    return {'n':len(a),'mean':statistics.mean(a),'median':statistics.median(a),'min':min(a),'max':max(a),'p95':percentile(a,.95),'first':a[0],'last':a[-1]}

rows.sort(key=lambda r:r['t'])
start=runs[0]['start'];end=runs[0]['end']
kill=stamp(next(r for r in ops if r.get('event_id')=='round2-condition7-human-start')['recorded_at_utc'])
boundaries=[('1','空载待机',start,stamp('2026-10-13T03:46:24+00:00'),'采集开始时已处于空载；结束时间人工提供'),('2','模型拉起',stamp('2026-10-13T03:46:24+00:00'),stamp('2026-10-13T03:48:58+00:00'),'起止均由用户提供，秒级精度'),('3','模型驻留待机',stamp('2026-10-13T03:48:58+00:00'),stamp('2026-10-13T03:50:06.612375+00:00'),'起点人工提供，结束为实际负载程序启动'),('4','单发推理',stamp('2026-10-13T03:50:06.612375+00:00'),stamp('2026-10-13T04:00:06.717543+00:00'),'负载程序真实日志'),('I1','单发后短暂驻模待机',stamp('2026-10-13T04:00:06.717543+00:00'),stamp('2026-10-13T04:02:06.854871+00:00'),'额外间隔，独立保留'),('5a','4路并发',stamp('2026-10-13T04:02:06.854871+00:00'),stamp('2026-10-13T04:12:06.986734+00:00'),'负载程序真实日志'),('I2','两批并发之间驻模待机',stamp('2026-10-13T04:12:06.986734+00:00'),stamp('2026-10-13T04:12:56.845267+00:00'),'额外间隔，独立保留'),('5b','16路请求并发测试',stamp('2026-10-13T04:12:56.845267+00:00'),stamp('2026-10-13T04:17:56.958847+00:00'),'16路客户端请求，9路有过输出，不等同16路同时执行；到期超时保留'),('6','推理后模型驻留待机',stamp('2026-10-13T04:17:56.958847+00:00'),kill,'结束用人工报告记录时刻作近似，实际kill更早，末段可能包含卸载过程'),('7','模型kill后空载待机',kill,end,'起点为人工报告记录时刻，非实际kill精确时间')]
phases=[]
metrics=('tj','temp_cpu','temp_gpu','temp_soc012','temp_soc345','gpu','gpu_power','cpu_power','vin_power','duty','ram_mb')
for id,label,a,b,precision in boundaries:
 sample=[r for r in rows if a<=r['t']<b]
 ph={'id':id,'label':label,'start':a,'end':b,'start_local':local(a),'end_local':local(b),'duration_s':b-a,'boundary':precision,'samples':len(sample),'metrics':{k:summarize([r[k] for r in sample if r[k] is not None]) for k in metrics},'fan_state_counts':{k:dict(collections.Counter(str(r[k]) for r in sample)) for k in ('fan_mode','temp_stale','fan_fault','guard_active')}}
 ph['fan_coverage']=ph['metrics']['duty']['n']/len(sample) if sample else None
 phases.append(ph)
 for r in sample:r['phase']=id
raw=[json.loads(l) for run in ROOT.glob('run-*') for f in run.glob('observations-*.jsonl') for l in f.read_text().splitlines()]
errs=[r for r in raw if r.get('error_class')];stale=[f for f in fans_raw if f.get('temp_stale')]
gaps=[{'before':local(a['t']),'after':local(b['t']),'delta_s':b['t']-a['t']} for a,b in zip(rows,rows[1:]) if b['t']-a['t']>2]
result={'runs':runs,'phases':phases,'total_new_samples':len(rows),'raw_records':len(raw),'method':'Stored accepted TJ refs, valid GPU quality, fan PWM as-of <=2.5sec. Arithmetic valid sample means; separate power rails; no imputation; human and log event precision preserved.','fan_modes':dict(collections.Counter(f['mode'] for f in fans_raw)),'http_errors':errs,'board_stale':stale,'accepted_sample_gaps_gt2s':gaps,'max_sample_gap_s':max(b['t']-a['t'] for a,b in zip(rows,rows[1:])),'peaks':{k:max((r for r in rows if r[k] is not None),key=lambda r:r[k]) for k in ('tj','gpu','gpu_power','cpu_power','vin_power','duty')}}
(OUT/'statistics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'operator-records-consolidated.json').write_text(json.dumps(ops,ensure_ascii=False,indent=2)+'\n')
with (OUT/'measurements.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for ph in phases:
 print(ph['id'],ph['label'],ph['samples'],{k:{n:round(ph['metrics'][k][n],3) for n in ['mean','min','max','first','last']} for k in ['tj','gpu','gpu_power','cpu_power','vin_power','duty'] if ph['metrics'][k]})
print('raw',len(raw),'accepted',len(rows),'http errors',[(local(stamp(r['received_at_utc'])),r['kind'],r['error_class']) for r in errs],'stale',[(local(f['t']),f['duty']) for f in stale],'maxgap',result['max_sample_gap_s'])
for k,r in result['peaks'].items():print('peak',k,r[k],r['local_time'])
for r in rows:
 if stamp('2026-10-13T04:20:00+00:00')<=r['t']<=kill and r['ram_mb']<5000:print('RAM below 5GB before kill report',r['local_time'],r['ram_mb']);break
