"""Independent byte, CPU-counter and source-window review; local files only."""
from pathlib import Path
import argparse,base64,collections,hashlib,json,math,statistics,sys,zipfile

def read(p): return json.loads(p.read_text())
def lines(p): return [json.loads(x) for x in p.read_text().splitlines() if x]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check_manifest(root,manifest):
    passed=[]
    for name,meta in read(manifest).items():
        p=root/name
        assert p.is_file(),str(p)
        expected=meta if isinstance(meta,str) else meta['sha256']
        assert sha(p)==expected,name
        if isinstance(meta,dict) and 'bytes' in meta: assert p.stat().st_size==meta['bytes'],name
        passed.append(name)
    return {'checked':len(passed),'all_match':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();r=a.root
    out=r/'deliverable/results';out.mkdir(parents=True,exist_ok=True)
    def save(n,obj): (out/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    f=r/'field_original';m=r/'model_original/thermal_cpu_capability_review_v1';run=f/'evidence/remote-result/run'
    integrity={'field':check_manifest(f,f/'SHA256.json'),'model':check_manifest(m,r/'model_original/SHA256.json')}
    cm=read(f/'evidence/field/candidate-files.json')
    for name,h in cm['files'].items(): assert sha(r/'delivered_runtime'/name)==h,name
    integrity['wheel_declared_runtime_files']=len(cm['files'])
    expected_model_zip_sha='67509182cfbe5854ef11ae19ce0f1555b0900e55a091d7281dffb46ac339cb5c'
    assert sha(f/'model-line/TTO-cpu.2首次60秒能力记录-模型线判读证据.zip')==expected_model_zip_sha
    integrity['model_nested_equals_separate']=True
    for p in (m/'inputs/remote-result/run').rglob('*'):
        if p.is_file(): assert sha(p)==sha(run/p.relative_to(m/'inputs/remote-result/run')),str(p)
    integrity['shared_run_files_match']=True
    save('integrity.json',integrity)
    rs=lines(run/'resources.jsonl');ev=lines(run/'sidecar-events.jsonl');trip=next(x for x in ev if x['event']=='stop_sidecar_only')
    start=next(x['mono_s'] for x in ev if x['event']=='started');end=trip['mono_s']
    errs=[]
    for pre,cur in zip(rs,rs[1:]):
        delta=sum(cur['cpu_times'][k]-pre['cpu_times'][k] for k in ('user','system'))
        recomputed=100*delta/(cur['mono_s']-pre['mono_s'])
        errs.append(abs(recomputed-cur['cpu_pct_single_core']))
    phases={}
    for label,lo,hi in [('before',0.,start),('during',start,end),('after',end,float('inf'))]:
        xs=[x for x in rs if lo<=x['mono_s']<hi];valid=[x['cpu_pct_single_core'] for x in xs if x['cpu_pct_single_core'] is not None]
        pairs=[(pre,cur) for pre,cur in zip(rs,rs[1:]) if pre['mono_s']>=lo and cur['mono_s']<hi]
        wall=sum(cur['mono_s']-pre['mono_s'] for pre,cur in pairs)
        cpu=sum(sum(cur['cpu_times'][k]-pre['cpu_times'][k] for k in ('user','system')) for pre,cur in pairs)
        phases[label]={'rows':len(xs),'reported_snapshot_mean_pct':statistics.mean(valid),'snapshot_peak_pct':max(valid),
                       'rss_peak_MiB':max(x['rss_bytes'] for x in xs)/2**20,
                       'wholly_inside_intervals':len(pairs),'wall_s':wall,'process_cpu_s':cpu,'weighted_cpu_pct':100*cpu/wall}
    dt=rs[-1]['mono_s']-rs[0]['mono_s'];dc=sum(rs[-1]['cpu_times'][k]-rs[0]['cpu_times'][k] for k in ('user','system'))
    old=lines(r/'previous_diagnostic/diagnostic/run/resources.jsonl')
    odt=old[-1]['mono_s']-old[0]['mono_s'];odc=sum(old[-1]['cpu_times'][k]-old[0]['cpu_times'][k] for k in ('user','system'))
    save('resource-counter-audit.json',{'metric':'100*delta(process user+system CPU seconds)/delta monotonic wall seconds',
         'current_run':read(run/'summary.json')['native_run_id'],'resource_rows':len(rs),'max_recomputed_difference':max(errs),
         'cpu_wall_interval_s':dt,'process_cpu_seconds':dc,'whole_interval_cpu_pct':100*dc/dt,'phases':phases,
         'stop':trip,'previous_300s_reference':{'run_id':read(r/'previous_diagnostic/diagnostic/run/summary.json')['native_run_id'],
          'resource_rows':len(old),'cpu_pct_time_weighted':100*odc/odt,'max_snapshot_pct':max(x['cpu_pct_single_core'] for x in old if x['cpu_pct_single_core'] is not None)},
         'interpretation':'Different versions/time/environment; not a randomized sidecar overhead experiment. Current counter is the receiver process, not host-wide CPU.'})
    arr=lines(run/'cpu-sidecar-arrivals.jsonl');wire=lines(run/'cpu-sidecar-wire.jsonl')
    # Key meanings are examined independently below; no outgoing connection is made.
    print('wire keys',list(wire[0]));print('arrival keys',list(arr[0]));print('source keys',list(arr[0]['source']))
    native=next((run/'native').glob('run-*'));obs=lines(native/'observations-0001.jsonl')
    fieldstates=lines(run/'states.jsonl');ad=lines(run/'admission.jsonl')
    counts=collections.Counter(x['kind'] for x in obs)
    fan=[x for x in obs if x['kind']=='fan'];ft=[x['mono_s'] for x in fan if not x.get('error')]
    save('field-outline.json',{'run':read(run/'summary.json')['native_run_id'],'raw_kinds':dict(counts),'state_records':len(fieldstates),'admission_records':len(ad),
        'source_wire_records':len(wire),'accepted_arrivals':len(arr),'fan_errors':sum(bool(x.get('error')) for x in fan),
        'fan_max_success_interval_s':max(b-a for a,b in zip(ft,ft[1:])),
        'protocol_requests':sum(x.get('event')=='request_start' for x in lines(run/'protocol.jsonl')),
        'original_summary':read(run/'summary.json')['time_coverage'],
        'capability_checks':read(f/'evidence/remote-result/capability-receipt.json')['checks']})
    print(json.dumps(integrity));print(json.dumps(phases,indent=2));print('CPU counters match:',max(errs))
if __name__=='__main__':main()
