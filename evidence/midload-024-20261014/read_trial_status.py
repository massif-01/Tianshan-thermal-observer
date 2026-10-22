"""Read existing trial files only; no telemetry or inference network requests."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

trial=Path('/home/rm01/TTO-midload-0.2.4/trials/midload-20261013T162317890886Z')


def tail_records(path,limit=160000):
    if not path.exists():return []
    with path.open('rb') as f:
        size=path.stat().st_size;start=max(0,size-limit);f.seek(start);data=f.read(limit)
    lines=data.splitlines()
    if start:lines=lines[1:]
    result=[]
    for line in lines:
        try:result.append(json.loads(line))
        except json.JSONDecodeError:pass  # Concurrent append may leave one incomplete final line.
    return result


events=tail_records(trial/'events.jsonl')
phases=[e for e in events if e['event']=='phase_start']
records=[]
for p in trial.glob('collection/run-*/observations-*.jsonl'):records=tail_records(p)
fan=next((r for r in reversed(records) if r['kind']=='fan' and r['payload'].get('data',{}).get('fans')),None)
source=next((r for r in reversed(records) if r['kind']=='orin'),None)
summary=json.loads((trial/'summary.json').read_text()) if (trial/'summary.json').exists() else None
phase=phases[-1] if phases else None
requests=tail_records(trial/'requests.jsonl')
state=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),trial=trial.name,
           phase=phase['phase'] if phase else None,
           phase_elapsed_s=time.monotonic()-phase['actual_start_mono_s'] if phase else None,
           phase_started_at_utc=phase['occurred_at_utc'] if phase else None,
           latest_record_utc=records[-1]['received_at_utc'] if records else None,
           newest_source_ref=source['ref'] if source else None,
           TJ=source['payload']['temperature'].get('tj') if source else None,
           GPU=source['payload'].get('gpu',{}).get('utilization_pct') if source else None,
           source_seq=source['payload'].get('telemetry_meta',{}).get('sample_seq') if source else None,
           fan=fan['payload']['data']['fans'][0] if fan else None,
           completed_request_records=len(requests),last_request=requests[-1] if requests else None,
           latest_events=events[-6:],summary=summary)
print(json.dumps(state,ensure_ascii=False))
