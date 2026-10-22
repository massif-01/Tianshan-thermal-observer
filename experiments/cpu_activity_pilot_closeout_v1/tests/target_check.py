"""Installed wheel check on disposable Linux x86 CPython3.10, never on RM-01."""
import asyncio,json,os,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);sys.path.insert(0,str(Path(__file__).resolve().parent))
from tto_field import __version__
from tto_field.identity import verify
from tto_field.cpu_source import __file__ as installed_source
from tto.config import load_config
assert __version__=='0.2.4+cpu.2';identity=verify(target=True);assert identity['checked_files']==48
c=load_config(environ={});config=out/'synthetic-default-config.json';config.write_text(json.dumps(c))
r=subprocess.run([sys.executable,'-m','tto_field.cpu_cli','preview','--config',str(config)],capture_output=True,text=True,check=True)
preview=json.loads(r.stdout);assert preview['authorization']['explicit_user_start'] is False
r=subprocess.run([sys.executable,'-m','tto_field.cpu_cli','execute','--config',str(config),'--binding','DOES-NOT-EXIST','--output','DOES-NOT-EXIST'],capture_output=True,text=True)
assert r.returncode!=0 and 'current explicit permission' in r.stderr
source_config=out/'source.json';source_config.write_text(json.dumps(dict(query_target_s=.2,nvml=False,rails=[])))
permission=out/'permission.json';permission.write_text(json.dumps(dict(action='cpu-sidecar-readonly',explicit_user_start=True,evidence='OWN DISPOSABLE CONTAINER ONLY',command_id='SYNTHETIC-LINUX-PROC')))
r=subprocess.run([sys.executable,installed_source,'--config',str(source_config),'--permission',str(permission),'--duration','2'],capture_output=True,text=True,check=True)
(out/'linux-proc-source.jsonl').write_text(r.stdout)
rows=[json.loads(x) for x in r.stdout.splitlines()];assert len(rows)>=5 and rows[1]['cpu']['complete_online_set']
assert all(x['identity']['boot_id'] and x['raw_cpu']['SC_CLK_TCK']>0 for x in rows)
assert all(x['gpu']['source_window'] is None and x['gpu']['new_independent_sample'] is None for x in rows)
# Full pipeline attempt1 retained a resource-budget stop under x86 emulation.
# This final installation check covers identity, CLI permissions and Linux source reads only.
(out/'verification.json').write_text(json.dumps(dict(installed_version=__version__,checked_files=48,python=sys.version,cli_preview_offline=True,execute_without_permission_rejected=True,linux_proc_read_rows=len(rows),full_target_request_run_proven=False,field_connections=0),indent=2))
print('INSTALLED TARGET CHECK PASS',flush=True)
