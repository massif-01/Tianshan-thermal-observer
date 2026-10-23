"""Explicit bounded observe, offline status/history/archive, and owned-process STOP."""
import re
import argparse, asyncio, json, os, socket, time, uuid, zipfile, hashlib
from datetime import datetime,timezone
from pathlib import Path
from collections import deque
from . import __version__

def validate_start(config,reg,grant,duration,local_loopback=False):
    from tto.config import public_config
    from tto.util import digest
    from urllib.parse import urlsplit
    import ipaddress
    if not 0<duration<=86400:raise ValueError('observe duration is explicitly bounded by24h')
    for key in ('device_id','thermal_config_id','observer_host_id','session_id'):
        if not isinstance(reg.get(key),str) or not reg[key]:raise ValueError('missing registration '+key)
    uuid.UUID(reg['session_id'])
    if grant.get('action')!='readonly-observe' or grant.get('explicit_user_start') is not True or not grant.get('evidence'):
        raise ValueError('current observation-window permission required')
    for key in ('device_id','thermal_config_id','session_id'):
        if grant.get(key)!=reg[key]:raise ValueError('permission identity mismatch:'+key)
    if reg['observer_host_id']!=socket.gethostname():raise ValueError('observer host identity mismatch')
    if grant.get('candidate_version')!=__version__ or grant.get('config_sha256')!=digest(public_config(config)):
        raise ValueError('permission candidate/config mismatch')
    from .support import digest_file
    package=Path(__file__).parent
    if grant.get('candidate_manifest_sha256')!=digest_file(package/'candidate-files.json') or grant.get('model_manifest_sha256')!=digest_file(package/'g2_model/frozen-model-manifest.json'):
        raise ValueError('permission code/model manifest mismatch')
    if grant.get('max_duration_s',0)<duration:raise ValueError('window does not cover duration')
    begin=datetime.fromisoformat(grant['not_before_utc']);end=datetime.fromisoformat(grant['expires_at_utc'])
    if begin.tzinfo is None or end.tzinfo is None:raise ValueError('window UTC needs timezone')
    now=datetime.now(timezone.utc)
    if not begin<=now or (end-now).total_seconds()<duration+10:raise ValueError('current window cannot contain run and cleanup')
    if not 64*1024**2<=grant.get('session_max_bytes',0)<=8*1024**3:raise ValueError('explicit session byte budget64MiB..8GiB required')
    expected=reg.get('expected_platform')
    if expected is not None and not isinstance(expected,dict):raise ValueError('expected_platform must be object or null')
    events=reg.get('workload_event_source')
    if events is not None:
        if not isinstance(events,dict) or not all(isinstance(events.get(k),str) and events[k] for k in ('path','session_id','clock_domain')):
            raise ValueError('event binding requires path/session/clock strings')
        if not isinstance(events.get('complete_from_session_start',False),bool):raise ValueError('event completeness must be boolean')
    # A no-network dry preview cannot turn into access by changing a formal flag.
    if local_loopback:
        if not grant.get('self_owned_loopback'):raise ValueError('loopback ownership required')
        for section in ('orin','tianshan'):
            if not ipaddress.ip_address(urlsplit(config[section]['base_url']).hostname).is_loopback:
                raise ValueError('local fixture permits numeric loopback origins only')
    return True

def archive(root,destination):
    from tto.util import file_hash
    if not (root/'summary.json').exists():raise ValueError('normal final summary required; preserve a crashed session separately')
    if json.loads((root/'status.json').read_text()).get('running'):raise ValueError('stop own observe before archive')
    index=json.loads((root/'files.json').read_text())
    for name,v in index.items():
        p=root/name
        if p.stat().st_size!=v['bytes'] or file_hash(p)!=v['sha256']:raise ValueError('session file SHA mismatch:'+name)
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(root)))
    return dict(archive=str(destination),sha256=file_hash(destination),bytes=destination.stat().st_size,files_verified=len(index))

def stop_owned(root):
    import psutil,signal
    launch=json.loads((root/'launch.json').read_text());status=json.loads((root/'status.json').read_text())
    if not status.get('running'):return dict(stopped=True,already_ended=True)
    if launch['clock_start']['host']!=socket.gethostname():raise ValueError('cannot stop a process on a different host')
    pid=status['pid'];p=psutil.Process(pid)
    if abs(p.create_time()-launch['process_created'])>.001 or p.uids().real!=os.getuid():raise ValueError('owned process identity no longer matches')
    p.send_signal(signal.SIGTERM)
    try:p.wait(timeout=8);return dict(stopped=True,forced=False)
    except psutil.TimeoutExpired:
        p.kill()
        try:p.wait(timeout=2);ended=True
        except psutil.TimeoutExpired:ended=False
        result=dict(stopped=ended,forced=True,pid=pid,reason='owned_observer_cleanup_timeout',utc=time.time())
        (root.parent/(root.name+'.stop-escalation.json')).write_text(json.dumps(result,indent=2)+'\n')
        return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('verify-install');v.add_argument('--target',action='store_true');v.add_argument('--thread-policy-output',type=Path)
    for name in ('preview','observe'):
        q=sub.add_parser(name);q.add_argument('--config',type=Path,required=True);q.add_argument('--registration',type=Path,required=True);q.add_argument('--duration',type=float,required=True)
        if name=='observe':
            q.add_argument('--grant',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--allow-network',action='store_true');q.add_argument('--local-loopback',action='store_true');q.add_argument('--publication-descriptor',type=Path,help='optional local read-only Web publication descriptor; private directory required')
    for name in ('status','stop','history','archive'):
        q=sub.add_parser(name);q.add_argument('--session',type=Path,required=True)
        if name=='history':q.add_argument('--stream',choices=('observations','states','predictions','scores','events','resources','workload-events'),default='states');q.add_argument('--last',type=int,default=20)
        if name=='archive':q.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    if a.cmd in ('status','history','stop','archive'):
        if a.cmd=='status':result=json.loads((a.session/'status.json').read_text())
        elif a.cmd=='stop':result=stop_owned(a.session)
        elif a.cmd=='archive':result=archive(a.session,a.output)
        else:
            if not 0<a.last<=1000:raise ValueError('history limit1..1000')
            index=json.loads((a.session/'stream-index.json').read_text()) if (a.session/'stream-index.json').exists() else None
            if index:
                files=[a.session/n for n in index['streams'].get('./'+a.stream,[])]
            else:
                pattern=re.compile(re.escape(a.stream)+r'(?:-(\d+))?\.jsonl')
                fragments=[(int(m.group(1) or 1),p) for p in a.session.glob(a.stream+'*.jsonl') if (m:=pattern.fullmatch(p.name))]
                files=[p for _,p in sorted(fragments)]
            if index and not files:files=[a.session/n for k,ns in index['streams'].items() if k in ('./'+a.stream,a.stream) for n in ns]
            records=[]
            for f in reversed(files):
                tail=deque(maxlen=a.last)
                with f.open() as stream:
                    for line in stream:tail.append(json.loads(line))
                records=list(tail)+records
                if len(records)>=a.last:break
            result=records[-a.last:]
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    from .numeric_policy import initialize
    receipt=getattr(a,'thread_policy_output',None)
    if a.cmd=='observe':receipt=a.output.with_name(a.output.name+'.startup')/'thread-policy.json'
    initialize(receipt)
    from .identity import verify
    if a.cmd=='verify-install':print(json.dumps(verify(a.target),indent=2));return 0
    from tto.config import load_config,public_config
    from tto.util import digest
    c=load_config(a.config,environ={});reg=json.loads(a.registration.read_text())
    if a.cmd=='preview':
        if not 0<a.duration<=86400:raise ValueError('duration1..86400s')
        result=dict(candidate_version=__version__,action='readonly-observe',registration=reg,duration_s=a.duration,
            config_sha256=digest(public_config(c)),permission_required=True,network_clients_created=0,Requester_count=0,CPU_sidecar=False,
            prediction_mode='G2-HOLD/B0/B1; real receive-anchor, actual publication',control_permission=False,
            grant_template=dict(action='readonly-observe',candidate_version=__version__,candidate_manifest_sha256=hashlib.sha256((Path(__file__).parent/'candidate-files.json').read_bytes()).hexdigest(),model_manifest_sha256=hashlib.sha256((Path(__file__).parent/'g2_model/frozen-model-manifest.json').read_bytes()).hexdigest(),device_id=reg.get('device_id'),thermal_config_id=reg.get('thermal_config_id'),session_id=reg.get('session_id'),config_sha256=digest(public_config(c)),max_duration_s=a.duration,session_max_bytes=8*1024**3,explicit_user_start=False,evidence=None,not_before_utc=None,expires_at_utc=None))
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if not a.allow_network:p.error('explicit current grant plus --allow-network required')
    grant=json.loads(a.grant.read_text());validate_start(c,reg,grant,a.duration,a.local_loopback)
    verify(target=not a.local_loopback)
    from .observe_runtime import run_observe
    result=asyncio.run(run_observe(c,reg,a.output,a.duration,local_loopback=a.local_loopback,grant=grant,publication_descriptor=a.publication_descriptor,storage_options=dict(budget=grant['session_max_bytes'],segment_bytes=min(2*1024**3,grant['session_max_bytes']))))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['reason'] in ('duration','SIGINT','SIGTERM','external_stop') and not result['error'] else 2
if __name__=='__main__':raise SystemExit(main())
