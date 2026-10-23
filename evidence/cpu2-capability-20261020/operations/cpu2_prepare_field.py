from pathlib import Path
import subprocess,json,hashlib,tarfile,uuid,datetime,base64
E=Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu2-capability-20261020');P=E/'preparation';F=E/'field';F.mkdir(exist_ok=True)
command='cpu2-capability-20261020-'+str(uuid.uuid4())
plan={'command_id':command,'remote_root':'/home/rm01/TTO-cpu2-capability-20261020','prefix':'/home/rm01/TTO-field-cpu2-capability-20261020','thor_root':'/home/rm01/TTO-cpu2-source-20261020','n305_socket':'/private/tmp/tto-cpu2-n305-ssh','mac_thor_socket':'/private/tmp/tto-cpu2-thor-ssh','n305_thor_socket':'/tmp/tto-cpu2-thor-ssh','remote_python':'/home/rm01/.venvs/tegrastats-api-1.1.1-2c356a1-20261013/bin/python','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
payload=P/'field-payload';payload.mkdir()
import shutil
shutil.copytree(P/'wheelhouse',payload/'wheelhouse')
shutil.copy2('evidence/cpu-pilot-closeout-20261020/candidate/install_candidate.py',payload/'install_candidate.py')
shutil.copy2('experiments/cpu_activity_pilot_closeout_v1/src/tto_field/cpu_source.py',payload/'cpu_source.py')
shutil.copy2('experiments/cpu_activity_pilot_closeout_v1/scripts/inspect_capability.py',payload/'inspect_capability.py')
config=json.loads(Path('evidence/fixed-anchors-closeout2-20261019/configuration/configuration.json').read_text());config['storage']['data_root']=plan['remote_root']+'/native-unused-default'
(payload/'configuration.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
source=json.loads(Path('experiments/cpu_activity_pilot_closeout_v1/config/sidecar-source.example.json').read_text());(payload/'source-config.json').write_text(json.dumps(source,indent=2)+'\n')
permission={'action':'cpu-sidecar-readonly','command_id':command,'explicit_user_start':True,'evidence':'User current permission: 允许本次独立安装、只读文件放置和一次60秒能力核对; password reconnection explicitly allowed; no inference/model query/jtop; one record only','recorded_at_utc':plan['recorded_at_utc'],'message_timestamp':'unknown'}
(payload/'source-permission.json').write_text(json.dumps(permission,ensure_ascii=False,indent=2)+'\n')
scan=subprocess.run(['ssh-keyscan','-T','5','-t','ed25519','10.10.99.98'],capture_output=True,text=True,check=True)
line=next(l for l in scan.stdout.splitlines() if l.startswith('10.10.99.98 '));finger='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(line.split()[2])).digest()).decode().rstrip('=');assert finger=='SHA256:94X9gAwwKSZMQTs6KCaCwlvWSEKXL4W9mC1OtGdOY40';(payload/'thor-known-hosts').write_text(line+'\n')
with tarfile.open(P/'field-payload.tar','w') as t:t.add(payload,arcname='payload')
print(json.dumps(plan,indent=2));print('payload ready')
