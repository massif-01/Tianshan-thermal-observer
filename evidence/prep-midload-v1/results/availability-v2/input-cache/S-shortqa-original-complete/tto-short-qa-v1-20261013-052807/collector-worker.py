import json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
prefix=Path.home()/'TTO'
session=Path(sys.argv[1])
settings=json.loads((session/'settings.json').read_text())
before=set((prefix/'runs').glob('run-*'))
def save(state):
    (session/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    (prefix/'current-run.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
with (session/'collection.log').open('x') as log:
    process=subprocess.Popen([str(prefix/'tto'),'collect','--config',str(prefix/'config/local.json'),'--duration','2400','--episode',settings['episode']],stdout=log,stderr=subprocess.STDOUT)
    for _ in range(30):
        if process.poll() is not None:raise RuntimeError('Collection exited before run creation; inspect collection.log')
        new=set((prefix/'runs').glob('run-*'))-before
        if new:
            run=new.pop()
            if (run/'manifest.json').exists():break
        time.sleep(1)
    else:raise RuntimeError('No run created; inspect collection.log and process')
    m=json.loads((run/'manifest.json').read_text())
    state={'status':'running','formal_collection':True,'observer_run_id':m['observer_run_id'],'episode':m['episode'],'run_path':str(run),'session_path':str(session),'launcher_pid':process.pid,'duration_s':2400,'collection_started_at_utc':m['started_at_utc'],'expected_end_at_utc':(datetime.fromisoformat(m['started_at_utc'])+timedelta(seconds=2400)).isoformat(),'condition_plan':settings['condition_plan'],'active_condition':None,'task_started':False,'task_marker_policy':'Preserve human report verbatim and approximate event timing separately from file-write time. Task end does not stop cooldown collection.','log_path':str(session/'collection.log')}
    authorization={'kind':'collection_authorized','source':'human_instruction','verbatim':settings['authorization'],'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'observer_run_id':m['observer_run_id'],'duration_s':2400,'condition_plan':settings['condition_plan'],'actual_condition':'not_yet_reported','event_time_precision':'instruction authorizes collection; this is not a reported condition start time'}
    started={'kind':'collection_started','source':'assistant_observed_collector_manifest','observer_run_id':m['observer_run_id'],'collection_started_at_utc':m['started_at_utc'],'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'expected_end_at_utc':state['expected_end_at_utc'],'condition_id':None}
    with (run/'operator-records.jsonl').open('x') as f:
        for r in (authorization,started):f.write(json.dumps(r,ensure_ascii=False)+'\n')
    save(state)
    code=process.wait()
    # Read the latest state so user-reported condition metadata is preserved.
    state=json.loads((prefix/'current-run.json').read_text())
    state.update(status='stopped',exit_code=code)
    if (run/'summary.json').exists():
        summary=json.loads((run/'summary.json').read_text())
        state.update(ended_at_utc=summary['ended_at_utc'],stop_reason=summary['stop_reason'])
    else:state.update(stop_reason='missing_final_summary')
    save(state)
report=prefix/'reports'/settings['episode']
with (session/'report.log').open('x') as log:
    result=subprocess.run([str(prefix/'tto'),'report','--run',str(run),'--output',str(report)],stdout=log,stderr=subprocess.STDOUT)
state.update(report_path=str(report),report_exit_code=result.returncode)
save(state)
