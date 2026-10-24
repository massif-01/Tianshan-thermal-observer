"""Install the candidate and optionally render a user unit; never enables a service."""
import argparse,json,subprocess,sys
from pathlib import Path


def render_unit(a):
    args=[str(a.prefix/'bin/tto-observe'),'observe','--config',str(a.config),'--registration',str(a.registration),'--grant',str(a.grant),'--output',str(a.session_output),'--allow-network']
    timed=a.duration is not None
    if timed:
        if not 0<a.duration<=86400:raise ValueError('timed test bounded24h')
        args+=['--duration',str(a.duration)]
    if a.publication_descriptor:args+=['--publication-descriptor',str(a.publication_descriptor)]
    if any('\n' in x for x in args):raise ValueError('unit arguments must be single line')
    text='[Unit]\nDescription=TTO read-only observe\nStartLimitIntervalSec=60\nStartLimitBurst=3\n\n[Service]\nType=simple\nExecStart='+ ' '.join(json.dumps(x.replace('%','%%')) for x in args)+'\n'
    text+='Restart=no\n' if timed else 'Restart=on-failure\nRestartSec=5\n'
    text+='TimeoutStopSec=10\nKillMode=control-group\n'
    if timed:text+='RuntimeMaxSec='+str(a.duration+10)+'\n'
    return text+'NoNewPrivileges=true\nUMask=0077\n\n[Install]\nWantedBy=default.target\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--wheelhouse',type=Path,required=True)
    for name in ('unit-output','config','registration','grant','session-output','publication-descriptor'):p.add_argument('--'+name,type=Path)
    p.add_argument('--duration',type=int,help='optional timed test; omitted means continuous')
    a=p.parse_args()
    if a.unit_output and not all((a.config,a.registration,a.grant,a.session_output)):p.error('unit rendering needs explicit configuration paths')
    text=render_unit(a) if a.unit_output else None
    subprocess.run([sys.executable,str(Path(__file__).with_name('install_candidate.py')),'--prefix',str(a.prefix),'--wheelhouse',str(a.wheelhouse)],check=True)
    subprocess.run([str(a.prefix/'bin/tto-observe'),'verify-install','--target','--thread-policy-output',str(a.prefix/'observe-install-thread-policy.json')],check=True)
    if a.unit_output:
        with a.unit_output.open('x') as f:f.write(text)
        print('Unit rendered only; no systemd daemon reload/enable/start performed')


if __name__=='__main__':main()
