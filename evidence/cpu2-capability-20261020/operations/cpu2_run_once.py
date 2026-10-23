from pathlib import Path
import subprocess,json,shlex,datetime
E=Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu2-capability-20261020');F=E/'field';p=json.loads((F/'plan.json').read_text());root=p['remote_root'];prefix=p['prefix']
remote='''import subprocess,pathlib,json,datetime,time
root=pathlib.Path(ROOT);prefix=PREFIX
receipt={'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command_id':COMMAND,'one_attempt_only':True}
argv=[prefix+'/bin/tto-cpu-pilot','capability','--config',str(root/'payload/configuration.json'),'--binding',str(root/'binding.json'),'--output',str(root/'run'),'--allow-network']
with (root/'capability.stdout').open('x') as out,(root/'capability.stderr').open('x') as err:
 p=subprocess.run(argv,stdout=out,stderr=err)
receipt.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=p.returncode)
(root/'exit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\\n');print(json.dumps(receipt));raise SystemExit(p.returncode)
'''.replace('ROOT',repr(root)).replace('PREFIX',repr(prefix)).replace('COMMAND',repr(p['command_id']))
(F/'run-once-remote.py').write_text(remote)
a=['ssh','-S',p['n305_socket'],'-o','BatchMode=yes','-o','ProxyCommand=false','rm01@10.10.99.99','python3 -c '+shlex.quote(remote)]
r=subprocess.run(a,capture_output=True,text=True,timeout=100);(F/'execute-invocation.stdout').write_text(r.stdout);(F/'execute-invocation.stderr').write_text(r.stderr);print(r.stdout);print(r.stderr);print('invocation_exit',r.returncode)
