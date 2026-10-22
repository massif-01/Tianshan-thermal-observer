"""Bounded GET-only service inspection; no Requester and no inference calls."""
import json,datetime,urllib.request,urllib.error,hashlib
from pathlib import Path
r=Path('/home/rm01/TTO-fixed-anchors-closeout2-20261019/preflight');r.mkdir(exist_ok=False)
for path,limit in [('/v1/models',65536),('/metrics',1048576),('/server_info',262144)]:
 stem={'/v1/models':'models','/metrics':'metrics','/server_info':'server-info'}[path]
 evidence={'path':path,'method':'GET','started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request('http://10.10.99.98:58000'+path,method='GET'),timeout=5) as response:
   b=response.read(limit+1);assert len(b)<=limit,'response budget exceeded'
   (r/(stem+'.raw')).write_bytes(b);evidence.update(status=response.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:evidence.update(error_class=type(e).__name__,http_status=getattr(e,'code',None))
 evidence['ended_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (r/(stem+'-receipt.json')).write_text(json.dumps(evidence,indent=2))
 print(json.dumps(evidence))
