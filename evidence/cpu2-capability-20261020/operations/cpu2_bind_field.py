from pathlib import Path
import subprocess,json,hashlib,shlex,datetime,time
E=Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu2-capability-20261020');F=E/'field';p=json.loads((F/'plan.json').read_text());root=p['remote_root'];prefix=p['prefix'];payload=root+'/payload'
def remote(cmd,name):
 before=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(['ssh','-S',p['n305_socket'],'-o','BatchMode=yes','-o','ProxyCommand=false','rm01@10.10.99.99',cmd],capture_output=True,text=True,timeout=30);after=datetime.datetime.now(datetime.timezone.utc).isoformat();(F/(name+'.stdout')).write_text(r.stdout);(F/(name+'.stderr')).write_text(r.stderr);(F/(name+'.receipt.json')).write_text(json.dumps({'mac_before_utc':before,'mac_after_utc':after,'returncode':r.returncode},indent=2));r.check_returncode();return r.stdout
ident=json.loads(remote(prefix+'/bin/tto-cpu-pilot verify-install --target','verify-install'));assert ident['checked_files']==48 and ident['target_environment_checked'];(F/'installation-identity.json').write_text(json.dumps(ident,indent=2)+'\n')
preview=json.loads(remote(prefix+'/bin/tto-cpu-pilot preview --mode capability --config '+payload+'/configuration.json','preview'))
side=json.loads(Path('experiments/cpu_activity_pilot_closeout_v1/config/sidecar-transport.example.json').read_text());side.update(existing_control_socket=p['n305_thor_socket'],command_id=p['command_id'],remote_python=p['remote_python'],remote_source_script=p['thor_root']+'/cpu_source.py',source_script_sha256=hashlib.sha256((E/'preparation/field-payload/cpu_source.py').read_bytes()).hexdigest(),remote_source_config=p['thor_root']+'/source-config.json',source_config_sha256=hashlib.sha256((E/'preparation/field-payload/source-config.json').read_bytes()).hexdigest(),remote_source_permission=p['thor_root']+'/source-permission.json')
b=dict(preview);b['command_id']=p['command_id'];b['sidecar']=side;b['authorization'].update(command_id=p['command_id'],explicit_user_start=True,evidence='User current permission: 允许本次独立安装、只读文件放置和一次60秒能力核对; subsequent password reconnection and N305 host key explicitly confirmed. Scope one capability only, no inference/model queries/jtop.');b['synthetic_loopback_only']=False;b['provenance']={'kind':'declared_field','source':'known N305 and Thor, independent SSH clock and hash receipts retained; not zero-latency proof'}
(F/'binding.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
remote('cat > '+shlex.quote(root+'/binding.json')+' <<\'TTO_BINDING\'\n'+json.dumps(b,ensure_ascii=False,indent=2)+'\nTTO_BINDING','binding-upload')
script='''import os,json,time,socket,datetime,pathlib,subprocess,hashlib
p=json.loads(PLAN)
clock=lambda:dict(host=socket.gethostname(),boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),mono_before_s=time.monotonic(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mono_after_s=time.monotonic(),clock='CLOCK_MONOTONIC')
print(json.dumps({'clock':clock(),'python':os.path.realpath('/home/rm01/TTO-field-cpu2-capability-20261020/bin/python')}))
for lock in ['/tmp/tto-field-entry-1000.lock','/tmp/tto-observer-1000.lock']:
 import fcntl
 fd=os.open(lock,os.O_RDWR|os.O_CREAT,0o600)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);print('lock_available',lock)
 finally:os.close(fd)
print('mux',subprocess.run(['ssh','-S',p['n305_thor_socket'],'-O','check','rm01@10.10.99.98'],capture_output=True,text=True).stderr.strip())
print('original_configuration_equal',json.loads(pathlib.Path('/home/rm01/TTO-fixed-anchors-closeout2-20261019/payload/configuration.json').read_text())=={} if pathlib.Path('/home/rm01/TTO-fixed-anchors-closeout2-20261019/payload/configuration.json').exists() else 'old canonical copy preserved')
'''.replace('PLAN',repr(json.dumps(p)))
print(remote('python3 -c '+shlex.quote(script),'preflight-clock-locks'))
# Verify exact source file bytes and clock through existing N305 -> Thor connection. Do not execute source.
thor='''import pathlib,hashlib,json,time,socket,datetime
root=pathlib.Path(ROOT)
a=time.monotonic();u=datetime.datetime.now(datetime.timezone.utc).isoformat();b=time.monotonic()
print(json.dumps({'host':socket.gethostname(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'clock':'CLOCK_MONOTONIC','mono_before_s':a,'utc':u,'mono_after_s':b,'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file()}}))
'''.replace('ROOT',repr(p['thor_root']))
thor_cmd=shlex.join([p['remote_python'],'-c',thor]);cmd=shlex.join(['ssh','-S',p['n305_thor_socket'],'-o','BatchMode=yes','-o','ProxyCommand=false','rm01@10.10.99.98',thor_cmd]);receipt=json.loads(remote(cmd,'thor-clock-source-hashes'));assert receipt['files']['cpu_source.py']==side['source_script_sha256'];assert receipt['files']['source-config.json']==side['source_config_sha256'];print('binding + source identity + clocks ready; no run yet')
