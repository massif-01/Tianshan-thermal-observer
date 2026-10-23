"""Reproduce plan/live divergence using the genuine reconstructed 0.2.2 source.
No request is allowed to leave this process. Endpoints are synthetic loopback.
"""
import sys,json,os,subprocess
from pathlib import Path
b=Path(__file__).resolve().parents[1]; c=b/'candidate/code'
from tto.config import load_config
config=load_config(environ={})
for key in ('orin','tianshan'):config[key]['base_url']='http://127.0.0.1:9'
out=b/'import-fixture';out.mkdir(exist_ok=True)
(out/'tto.json').write_text(json.dumps(config))
(out/'trial.json').write_text(json.dumps({'trial_id':'TTO-MIDLOAD-DEV-v1.0','inference':{'base_url':'http://127.0.0.1:9','model':'review-owned-model','messages':[{'role':'user','content':'not sent'}]}}))
wrapper='''import sys,runpy,socket,json
calls=[]
def block(*args,**kwargs):
 calls.append("network_attempt")
 raise RuntimeError("review network blocked")
socket.socket.connect=block;socket.socket.connect_ex=block;socket.getaddrinfo=block
script=sys.argv[1];sys.argv=sys.argv[1:]
from pathlib import Path
sys.path.insert(0,str(Path(script).parent))
try:runpy.run_path(script,run_name="__main__")
finally:
 import tto
 print("REVIEW_IMPORT="+json.dumps({"version":tto.__version__,"file":tto.__file__,"network_attempts":calls}))
'''
env=os.environ.copy();env['PYTHONPATH']=str(b/'legacy-022-source')
results=[]
for mode in ('--plan','--live'):
 cmd=[sys.executable,'-c',wrapper,str(c/'scripts/thermal_trials/run_midload.py'),mode,'--trial-config',str(out/'trial.json'),'--tto-config',str(out/'tto.json'),'--output-root',str(out/'not_started')]
 r=subprocess.run(cmd,env=env,cwd=b,capture_output=True,text=True,timeout=10)
 results.append({'mode':mode,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
print(json.dumps(results,ensure_ascii=False,indent=2))
(b/'results/runner-import-path.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
assert results[0]['returncode']==0 and results[1]['returncode']==2
assert all('"network_attempts": []' in r['stdout'] for r in results)
assert '"version": "0.2.2"' in results[1]['stdout']
print('COUNTEREXAMPLE CONFIRMED: installed 0.2.3; plan succeeds; live resolves old 0.2.2 and fails without networking.')
