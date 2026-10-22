import json,datetime,os
from pathlib import Path
R=Path('/home/rm01/TTO-fixed-anchors-closeout2-20261019');run=R/'run'
def read(p):return json.loads(p.read_text()) if p.exists() else None
def rows(p):
 result=[]
 if not p.exists():return result
 for line in p.read_text().splitlines():
  try:result.append(json.loads(line))
  except json.JSONDecodeError:pass
 return result
launch=read(R/'actor-launch.json');exit=read(R/'actor-exit.json');scheduler=rows(run/'scheduler-events.jsonl');protocol=rows(run/'protocol.jsonl');binding=read(run/'native-binding.json');summary=read(run/'summary.json')
cmd=Path('/proc')/str(launch['runner_pid'])/'cmdline';alive=cmd.exists() and b'/bin/tto-field' in cmd.read_bytes()
print(json.dumps({'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'launch':launch,'exit':exit,'native_binding':binding,'runner_identity_alive':alive,'scheduler':scheduler,'protocol':protocol,'summary':summary},ensure_ascii=False))
