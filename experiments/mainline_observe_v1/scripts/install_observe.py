"""Original target installer plus optional OFFLINE user-unit rendering. Never enables a service."""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,required=True);p.add_argument('--wheelhouse',type=Path,required=True);p.add_argument('--unit-output',type=Path);p.add_argument('--config',type=Path);p.add_argument('--registration',type=Path);p.add_argument('--grant',type=Path);p.add_argument('--session-output',type=Path);p.add_argument('--duration',type=int);a=p.parse_args()
if a.unit_output and not all((a.config,a.registration,a.grant,a.session_output,a.duration)):p.error('unit rendering needs explicit window paths/duration')
subprocess.run([sys.executable,str(Path(__file__).with_name('install_candidate.py')),'--prefix',str(a.prefix),'--wheelhouse',str(a.wheelhouse)],check=True)
subprocess.run([str(a.prefix/'bin/tto-observe'),'verify-install','--target','--thread-policy-output',str(a.prefix/'observe-install-thread-policy.json')],check=True)
if a.unit_output:
 args=[str(a.prefix/'bin/tto-observe'),'observe','--config',str(a.config),'--registration',str(a.registration),'--grant',str(a.grant),'--output',str(a.session_output),'--duration',str(a.duration),'--allow-network']
 if not 0<a.duration<=86400:raise ValueError('window bounded24h')
 if any('\n' in x for x in args):raise ValueError('unit arguments must be single line')
 text='[Unit]\nDescription=TTO bounded read-only observe\n\n[Service]\nType=simple\nExecStart='+ ' '.join(json.dumps(x.replace('%','%%')) for x in args)+'\nRestart=no\nTimeoutStopSec=10\nKillMode=control-group\nRuntimeMaxSec='+str(a.duration+10)+'\nNoNewPrivileges=true\n\n[Install]\nWantedBy=default.target\n'
 with a.unit_output.open('x') as f:f.write(text)
 print('Unit rendered only; no systemd daemon reload/enable/start performed')
