"""Offline preview or explicitly authorized capability/pilot. No implicit upgrade or device defaults."""
import argparse,asyncio,json
from pathlib import Path
from . import __version__
from .support import digest_file

def preview(c,mode):
    from .cli import preview as original
    from .cpu_pilot import PLAN,pilot_profile
    b=original(c,'diagnose' if mode=='capability' else 'execute')
    b.update(profile_sha256=digest_file(PLAN),profile=pilot_profile(),candidate_version=__version__,capability_receipt=None,
             capability_user_decision_evidence=None,instrument={'used':False},sidecar=None)
    b['authorization']['action']='readonly-diagnostic' if mode=='capability' else 'cpu-activity-pilot'
    return b

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify-install').add_argument('--target',action='store_true')
    for name in ('preview','capability','execute'):
        q=sub.add_parser(name);q.add_argument('--config',type=Path,required=True)
        if name=='preview':q.add_argument('--mode',choices=('capability','execute'),default='capability')
        else:
            q.add_argument('--binding',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--allow-network',action='store_true')
    a=p.parse_args(argv)
    from .identity import verify
    if a.cmd=='verify-install':print(json.dumps(verify(a.target),indent=2));return 0
    verify()
    from tto.config import load_config
    c=load_config(a.config,environ={})
    if a.cmd=='preview':print(json.dumps(preview(c,a.mode),ensure_ascii=False,indent=2));return 0
    if not a.allow_network:p.error('current explicit permission and --allow-network required')
    b=json.loads(a.binding.read_text())
    if not b.get('synthetic_loopback_only'):verify(target=True)
    from .runtime import run
    result=asyncio.run(run(c,b,'diagnose' if a.cmd=='capability' else 'execute',a.output,duration=60,cpu_pilot=True))
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
