#!/usr/bin/env python3
"""Independent, versioned prefix. Default installation enables systemd after successful checks.
Use --service none only for local candidate verification; no service is activated by that mode.
"""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import socket
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlsplit
import uuid

ROOT=Path(__file__).resolve().parents[1]
# Local readiness checks must not inherit an HTTP proxy from the install shell.
urlopen=build_opener(ProxyHandler({})).open


def run(*args):subprocess.run([str(a) for a in args],check=True)

def hash_password(password):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),200000).hex()


def wait_ready(config, systemctl, timeout_s=15):
    """Type=simple active is not readiness. Never accept another listener's health."""
    w=json.loads(Path(config).read_text())['web'];bind=w['bind']
    family=socket.AF_INET6 if ':' in bind else socket.AF_INET
    # Verify the configured address belongs to this host before any HTTP check.
    with socket.socket(family,socket.SOCK_STREAM) as probe:probe.bind((bind,0))
    address='127.0.0.1' if bind=='0.0.0.0' else '::1' if bind=='::' else bind
    address='['+address+']' if ':' in address else address
    host=urlsplit(w['allowed_origins'][0]).netloc if w['access_mode']=='lan' else address+':59009'
    request=Request('http://'+address+':59009/healthz',headers={'Host':host})
    deadline=time.monotonic()+timeout_s
    while time.monotonic()<deadline:
        try:
            pid=int(subprocess.check_output([*systemctl,'show','tto-web.service','--property=MainPID','--value'],text=True).strip())
            with urlopen(request,timeout=1) as response:value=json.load(response)
            if pid>0 and value.get('pid')==pid and value.get('web')=='running':return
        except (OSError,ValueError,subprocess.CalledProcessError):pass
        time.sleep(.2)
    raise SystemExit('Web服务未在期限内就绪；未将其他59009监听者视为安装成功，请检查tto-web.service日志。')


def main():
    p=argparse.ArgumentParser(description='TTO Web独立安装；默认启用systemd服务，需已批准主机安装')
    p.add_argument('--prefix',type=Path,default=Path.home()/'TTO-Web')
    p.add_argument('--python',default=sys.executable,help='目标建议独立Conda Python3.10，不升级base')
    p.add_argument('--service',choices=['system','user','none'],default='system')
    p.add_argument('--access',choices=['local','lan'],default='local')
    p.add_argument('--bind',default=None);p.add_argument('--allowed-origin',action='append',default=[])
    p.add_argument('--mode',choices=['follow','observe'],default='follow')
    p.add_argument('--active-descriptor',type=Path);p.add_argument('--observation-config',type=Path)
    p.add_argument('--observed-device',default=None);p.add_argument('--rollback',action='store_true')
    p.add_argument('--uninstall-service',action='store_true')
    args=p.parse_args();prefix=args.prefix.expanduser().resolve()
    if any(c in str(prefix) for c in ('\n','\r','%','"','\\')):p.error('prefix contains unsupported systemd characters')
    systemctl=['systemctl'] if args.service=='system' else ['systemctl','--user']
    privileged=['sudo'] if args.service=='system' and os.getuid()!=0 else []
    if args.uninstall_service:
        if args.service=='none':p.error('select installed service type')
        run(*privileged,*systemctl,'disable','--now','tto-web.service')
        unit=Path('/etc/systemd/system/tto-web.service') if args.service=='system' else Path.home()/'.config/systemd/user/tto-web.service'
        run(*privileged,'rm','--',unit);run(*privileged,*systemctl,'daemon-reload')
        print('已移除Web服务；独立prefix和原TTO数据保留。');return
    if args.rollback:
        previous=prefix/'previous';current=prefix/'current'
        if not previous.is_symlink():p.error('no previous Web release')
        old=current.resolve();target=previous.resolve();tmp=prefix/'current.next'
        tmp.symlink_to(target);os.replace(tmp,current);previous.unlink();previous.symlink_to(old)
        if args.service!='none':
            run(*privileged,*systemctl,'restart','tto-web.service');wait_ready(prefix/'web.json',systemctl)
        print('已切换到上一Web版本；未修改原TTO环境。');return
    if args.access=='local' and args.bind not in (None,'127.0.0.1','::1'):p.error('local access requires loopback')
    if args.access=='lan' and (not args.bind or not args.allowed_origin):p.error('LAN requires --bind and --allowed-origin')
    if args.service=='system' and os.getuid()==0:p.error('run as the same non-root user as existing TTO; sudo is used only for the service unit')
    if args.service=='system' and sys.platform!='linux':p.error('system service requires Linux; use --service none for local tests')
    prefix.mkdir(parents=True,exist_ok=True,mode=0o700)
    wheels=list((ROOT/'wheelhouse').glob('tto_web_ui-*.whl'))
    if len(wheels)!=1:raise SystemExit('expected one Web wheel')
    version=wheels[0].name.split('-')[1]
    release=prefix/'releases'/(version+'-'+uuid.uuid4().hex[:8]);release.mkdir(parents=True,mode=0o700)
    # Every candidate file is hashed; verify before installing. No base-environment mutation.
    identities=json.loads((ROOT/'candidate-identities.json').read_text())
    for name,digest in identities.items():
        f=ROOT/name
        if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise SystemExit('candidate identity mismatch: '+name)
    run(args.python,'-m','venv',release/'env')
    python=release/'env/bin/python';wheelhouse=ROOT/'wheelhouse'
    run(python,'-m','pip','install','--no-index','--find-links',wheelhouse,'-r',ROOT/'requirements.runtime.lock')
    wheels=list(wheelhouse.glob('tto_web_ui-*.whl'))
    if len(wheels)!=1:raise SystemExit('expected one Web wheel')
    run(python,'-m','pip','install','--no-deps',wheels[0])
    config=prefix/'web.json'
    if not config.exists():
        config_data=json.loads((ROOT/'config/web.json').read_text())
        config_data['web'].update(access_mode=args.access,bind=args.bind or '127.0.0.1',allowed_origins=args.allowed_origin)
        config_data['source'].update(mode=args.mode,active_descriptor=str(args.active_descriptor.resolve()) if args.active_descriptor else None,observation_config=str(args.observation_config.resolve()) if args.observation_config else None,observed_device=args.observed_device)
        if args.access=='lan':
            password=secrets.token_urlsafe(24);config_data['web']['password_hash']=hash_password(password)
            credential=prefix/'readonly-password.txt';credential.write_text(password+'\n');credential.chmod(0o600)
            print('只读口令保存在prefix/readonly-password.txt（600），不进入URL或日志。')
        config.write_text(json.dumps(config_data,ensure_ascii=False,indent=2)+'\n');config.chmod(0o600)
    run(python,'-c','from tto_web.server import configuration; import sys; configuration(sys.argv[1]); from tto_web.server import STATIC; assert (STATIC/"index.html").is_file(); from tto_web.identity import verify; print(verify())',config)
    current=prefix/'current';previous=prefix/'previous'
    if current.is_symlink():
        if previous.is_symlink():previous.unlink()
        previous.symlink_to(current.resolve())
    temp=prefix/'current.next';temp.symlink_to(release);os.replace(temp,current)
    launcher=prefix/'tto-web';launcher.write_text('#!/bin/sh\nexec "'+str(prefix/'current/env/bin/tto-web')+'" "$@"\n');launcher.chmod(0o700)
    unit_text='''[Unit]
Description=TTO read-only thermal Web UI 59009
After=network.target
[Service]
Type=simple
ExecStart="{exe}" serve --config "{config}"
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
UMask=0077
NoNewPrivileges=true
StandardOutput=null
StandardError=journal
LogRateLimitIntervalSec=60
LogRateLimitBurst=10
{user}[Install]
WantedBy={target}
'''.format(exe=launcher,config=config,user=('User='+getpass.getuser()+'\n') if args.service=='system' else '',target='multi-user.target' if args.service=='system' else 'default.target')
    unit_candidate=prefix/'tto-web.service';unit_candidate.write_text(unit_text)
    if args.service!='none':
        unit=Path('/etc/systemd/system/tto-web.service') if args.service=='system' else Path.home()/'.config/systemd/user/tto-web.service'
        if args.service=='user':unit.parent.mkdir(parents=True,exist_ok=True)
        run(*privileged,'install','-m','644',unit_candidate,unit)
        run(*privileged,*systemctl,'daemon-reload');run(*privileged,*systemctl,'enable','tto-web.service')
        run(*privileged,*systemctl,'restart','tto-web.service')
        run(*privileged,*systemctl,'is-active','tto-web.service')
        wait_ready(config,systemctl)
    print('Web候选安装完成：'+str(launcher)+' serve --config '+str(config))
    print('访问 http://127.0.0.1:59009/；LAN使用安装主机地址。无源时等待，不启用合成数据。')


if __name__=='__main__':main()
