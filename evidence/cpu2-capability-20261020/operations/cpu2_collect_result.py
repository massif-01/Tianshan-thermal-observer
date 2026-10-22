from pathlib import Path
import subprocess,json,shlex,tarfile,datetime
E=Path('/Users/massif/Tianshan-thermal-observer/evidence/cpu2-capability-20261020');F=E/'field';p=json.loads((F/'plan.json').read_text());root=p['remote_root'];prefix=p['prefix']
a=['ssh','-S',p['n305_socket'],'-o','BatchMode=yes','-o','ProxyCommand=false','rm01@10.10.99.99']
cmd=shlex.join([prefix+'/bin/python',root+'/payload/inspect_capability.py','--run',root+'/run','--output',root+'/capability-receipt.json'])
r=subprocess.run(a+[cmd],capture_output=True,text=True,timeout=20);(F/'inspect-capability.stdout').write_text(r.stdout);(F/'inspect-capability.stderr').write_text(r.stderr);(F/'inspect-capability-exit.json').write_text(json.dumps({'returncode':r.returncode},indent=2));print('inspector_exit',r.returncode,r.stdout,r.stderr)
# Preserve a missing/failed capability receipt; no implicit retry or run restart.
remote='''import pathlib,json,hashlib,datetime,time,socket
root=pathlib.Path(ROOT)
a=time.monotonic();u=datetime.datetime.now(datetime.timezone.utc).isoformat();b=time.monotonic()
(root/'post-clock.json').write_text(json.dumps({'host':socket.gethostname(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'clock':'CLOCK_MONOTONIC','mono_before_s':a,'utc':u,'mono_after_s':b},indent=2))
index={str(f.relative_to(root)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in root.rglob('*') if f.is_file() and 'wheelhouse' not in f.parts and f.name!='transfer-index.json'}
(root/'transfer-index.json').write_text(json.dumps(index,indent=2))
print((root/'run/summary.json').read_text())
'''.replace('ROOT',repr(root))
r=subprocess.run(a+['python3 -c '+shlex.quote(remote)],capture_output=True,text=True,timeout=20);r.check_returncode();(F/'summary-readback.json').write_text(r.stdout);print(r.stdout[:2500])
with (F/'remote-result.tar').open('wb') as out:
 r=subprocess.run(a+['tar --exclude=payload/wheelhouse -cf - -C '+shlex.quote(root)+' .'],stdout=out,stderr=subprocess.PIPE,timeout=60)
r.check_returncode();dest=E/'remote-result';dest.mkdir()
with tarfile.open(F/'remote-result.tar') as t:
 for m in t.getmembers():
  target=(dest/m.name).resolve();target.relative_to(dest.resolve());assert not m.issym() and not m.islnk()
 t.extractall(dest)
print('downloaded',dest)
