import json,subprocess,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
prefix=Path.home()/'TTO'
before=set((prefix/'runs').glob('run-*'))
log=prefix/'collect-rm01-real-20261012-01.log'
with log.open('x') as f:
    process=subprocess.Popen([str(prefix/'tto'),'collect','--config',str(prefix/'config/local.json'),'--duration','1800','--episode','rm01-real-20261012-01'],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
for _ in range(30):
    if process.poll() is not None:raise RuntimeError(log.read_text())
    new=set((prefix/'runs').glob('run-*'))-before
    if new:
        run=new.pop()
        if (run/'manifest.json').exists():break
    time.sleep(1)
else:raise RuntimeError('No collection run found; inspect process and log')
manifest=json.loads((run/'manifest.json').read_text())
record={'kind':'collection_started','source':'assistant_observed_collector_manifest','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'collection_started_at_utc':manifest['started_at_utc'],'observer_run_id':manifest['observer_run_id'],'episode':manifest['episode'],'run_path':str(run),'launcher_pid':process.pid,'duration_s':1800,'task_started':False,'task_marker_policy':'Human reported task markers are approximate; preserve verbatim report, distinguish reported event time from record write time. Task end does not stop collection.','expected_end_at_utc':(datetime.fromisoformat(manifest['started_at_utc'])+timedelta(seconds=1800)).isoformat(),'log_path':str(log)}
with (run/'operator-records.jsonl').open('x') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
(prefix/'current-run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False,indent=2))
