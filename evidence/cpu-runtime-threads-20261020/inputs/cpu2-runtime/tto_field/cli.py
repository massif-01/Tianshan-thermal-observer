"""Explicit commands: offline preview, authorized read-only diagnose, or authorized fixed-anchors execute."""
import argparse,asyncio,json
from pathlib import Path
from . import __version__

def preview(config,mode):
    from tto.config import public_config
    from tto.util import digest
    from tto.storage import source_identity
    from .runtime import ROOT,profile
    from .support import digest_file
    return dict(candidate_version=__version__,mode=mode,config_sha256=digest(public_config(config)),
                collector_source_sha256=source_identity()['sha256'],observer_model_sha256=digest_file(ROOT/'research/models/primary.json'),
                observer_spec_sha256=digest_file(ROOT/'research/observer-spec.json'),old_overrides=False,command_id=None,
                expected_binding='agx_info.temperature.tj',firmware_identity=None,
                authorization=dict(action='readonly-diagnostic' if mode=='diagnose' else 'fixed-anchors',command_id=None,explicit_user_start=False,evidence=None),
                note='Preview creates no network clients and never opens credential headers. No device authorization is implied.',
                request_actor_thread='01a1331a-f937-7d91-aef0-ac4f5e50bd8a' if mode=='execute' else None,
                profile=profile() if mode=='execute' else None)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('verify-install');q.add_argument('--target',action='store_true')
    for name in ['preview','diagnose','execute']:
        q=sub.add_parser(name);q.add_argument('--config',required=True,type=Path)
        if name=='preview':q.add_argument('--mode',choices=['diagnose','execute'],default='diagnose')
        else:
            q.add_argument('--binding',required=True,type=Path);q.add_argument('--output',required=True,type=Path)
            q.add_argument('--allow-network',action='store_true')
            if name=='diagnose':q.add_argument('--duration',type=float,default=300)
    a=p.parse_args(argv)
    from .identity import verify
    if a.command=='verify-install':
        print(json.dumps(verify(a.target),ensure_ascii=False,indent=2));return 0
    verify()
    from tto.config import load_config
    c=load_config(a.config,environ={})
    if a.command=='preview':
        print(json.dumps(preview(c,a.mode),ensure_ascii=False,indent=2));return 0
    if not a.allow_network:p.error('Run commands require --allow-network and a current bound authorization; preview is offline.')
    from .runtime import run
    b=json.loads(a.binding.read_text())
    if not b.get('synthetic_loopback_only'):verify(target=True)
    result=asyncio.run(run(c,b,a.command,a.output,duration=getattr(a,'duration',300)))
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
