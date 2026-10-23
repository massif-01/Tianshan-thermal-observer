import subprocess,pathlib,json,datetime,time
root=pathlib.Path('/home/rm01/TTO-cpu2-capability-20261020');prefix='/home/rm01/TTO-field-cpu2-capability-20261020'
receipt={'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command_id':'cpu2-capability-20261020-1ca3a249-8ea9-4608-aa05-105f9aff5614','one_attempt_only':True}
argv=[prefix+'/bin/tto-cpu-pilot','capability','--config',str(root/'payload/configuration.json'),'--binding',str(root/'binding.json'),'--output',str(root/'run'),'--allow-network']
with (root/'capability.stdout').open('x') as out,(root/'capability.stderr').open('x') as err:
 p=subprocess.run(argv,stdout=out,stderr=err)
receipt.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=p.returncode)
(root/'exit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(p.returncode)
