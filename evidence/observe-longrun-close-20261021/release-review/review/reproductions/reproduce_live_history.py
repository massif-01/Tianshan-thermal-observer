"""Offline rotation/history reproduction, using the candidate's actual file store and CLI.
No devices, networking, fitting, or original source modifications.
"""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--package-root',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.package_root:sys.path.insert(0,str(a.package_root.resolve()))
from tto_field.observe_storage import SessionStore
a.output.mkdir(parents=True,exist_ok=False)
s=SessionStore(a.output/'session',budget=1000000,segment_bytes=100000,chunk_bytes=160,min_free=0)
for n in range(20):s.append(s.root,'states',dict(n=n,example='synthetic-only'))
# Same interpreter/package for CLI; explicit sys.path supports an unpacked review copy.
launcher='import sys; '+('sys.path.insert(0,'+repr(str(a.package_root.resolve()))+'); ' if a.package_root else '')+'from tto_field.observe_cli import main; main()'
cmd=[sys.executable,'-c',launcher,'history','--session',str(s.root),'--stream','states','--last','3']
def query():
 p=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=15)
 return [x['n'] for x in json.loads(p.stdout)]
live=query();files=[p.name for p in sorted(s.root.glob('states*.jsonl'))];s.close();closed=query()
r=dict(scope='synthetic local files / actual candidate CLI; no field',expected=[17,18,19],live=live,closed=closed,lexical_file_order=files,live_correct=live==[17,18,19],closed_correct=closed==[17,18,19])
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
