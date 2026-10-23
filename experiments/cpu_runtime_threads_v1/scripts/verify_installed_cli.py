"""Bounded actual installed entry subprocesses, including rejection before any socket access."""
import argparse,subprocess,os,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);exe=a.prefix/'bin/tto-cpu-pilot';other=a.prefix/'bin/tto-field';env=os.environ.copy();env.pop('PYTHONPATH',None)
keys=['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'];receipts=[]
for name,program,multi in [('clean',exe,False),('inherited8',exe,True),('shared-field-entry',other,True)]:
 e=env.copy()
 for k in keys:
  if multi:e[k]='8'
  else:e.pop(k,None)
 path=a.output/(name+'-thread-policy.json');r=subprocess.run([str(program),'verify-install','--thread-policy-output',str(path)],env=e,capture_output=True,text=True,timeout=20)
 (a.output/(name+'.stderr')).write_text(r.stderr);(a.output/(name+'.identity.json')).write_text(r.stdout);assert r.returncode==0,(name,r.stderr)
 j=json.loads(path.read_text());v=json.loads(r.stdout);assert j['verified'] and v['numeric_thread_policy']['pid']==j['pid'];assert j['modules_already_loaded']==[] and all(x['num_threads']==1 for x in j['loaded_pools']);assert len(j['loaded_pools'])>=2
 assert j['libraries']['numpy']['version']=='2.2.6' and j['libraries']['scipy']['version']=='1.15.3'
 if multi:assert set(j['inherited_environment'].values())=={'8'}
 assert j['applied_at_mono_s']<j['checked_at_mono_s'];receipts.append(dict(scenario=name,returncode=r.returncode,pid=j['pid'],verified=True,pools=j['loaded_pools']))
# Load NumPy before actual console entry with a test-only sitecustomize; deny/log all network attempts.
site=a.output/'early-site';site.mkdir();network=a.output/'forbidden-network-attempts.txt'
(site/'sitecustomize.py').write_text("import numpy,socket\nfrom pathlib import Path\ndef blocked(*a,**k):\n Path("+repr(str(network))+ ").write_text('network attempted')\n raise RuntimeError('TEST forbids networking')\nsocket.create_connection=blocked\nsocket.socket.connect=blocked\nsocket.socket.connect_ex=blocked\n")
e=env.copy();e['PYTHONPATH']=str(site);out=a.output/'must-not-run';receipt=out.with_name(out.name+'.startup')/'thread-policy.json'
r=subprocess.run([str(exe),'capability','--config',str(a.output/'not-read-config.json'),'--binding',str(a.output/'not-read-binding.json'),'--output',str(out),'--allow-network'],env=e,capture_output=True,text=True,timeout=20)
(a.output/'preloaded-rejection.stderr').write_text(r.stderr);j=json.loads(receipt.read_text());assert r.returncode!=0 and not j['verified'] and 'numpy' in j['modules_already_loaded'];assert not network.exists() and not out.exists();receipts.append(dict(scenario='preloaded_numpy',returncode=r.returncode,verified=False,network_attempts=0,recorded_pid=j['pid']))
# A backend that cannot be introspected must fail before any client/config access.
site2=a.output/'unknown-pool-site';site2.mkdir()
(site2/'sitecustomize.py').write_text("import threadpoolctl\noriginal=threadpoolctl.threadpool_info\nthreadpoolctl.threadpool_info=lambda:original()[:1]\n")
e=env.copy();e['PYTHONPATH']=str(site2);out=a.output/'unknown-pool-run'
r=subprocess.run([str(exe),'capability','--config',str(a.output/'not-read-config.json'),'--binding',str(a.output/'not-read-binding.json'),'--output',str(out),'--allow-network'],env=e,capture_output=True,text=True,timeout=20)
(a.output/'unknown-pool.stderr').write_text(r.stderr)
j=json.loads((out.with_name(out.name+'.startup')/'thread-policy.json').read_text())
assert r.returncode!=0 and not j['verified'] and j['error']=='numeric_backend_not_verifiable_by_candidate' and not out.exists()
receipts.append(dict(scenario='unverifiable_pool',returncode=r.returncode,verified=False,run_created=False,pid=j['pid']))
(a.output/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n');print('PASS installed entries clean/inherited8/shared entry + preloaded rejection with zero network attempts')
