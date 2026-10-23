"""Install offline into a NEW prefix, separate backend/Web venvs, no service or listener."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--active-descriptor', type=Path, required=True)
    parser.add_argument('--service', choices=['none'], default='none')
    parser.add_argument('--access', choices=['local','lan'], default='local')
    parser.add_argument('--bind')
    parser.add_argument('--allowed-origin', action='append', default=[])
    args = parser.parse_args()
    if args.access=='lan' and (not args.bind or not args.allowed_origin):
        parser.error('LAN requires --bind and --allowed-origin')
    root = Path(__file__).resolve().parent
    prefix = args.prefix.expanduser().resolve()
    if prefix.exists():
        parser.error('fresh prefix required; preserve existing installations')
    for name, digest in json.loads((root / 'SHA256.json').read_text()).items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise SystemExit('bundle identity mismatch: ' + name)
    subprocess.run([sys.executable, str(root / 'backend/install_candidate.py'), '--prefix', str(prefix / 'backend'),
                    '--wheelhouse', str(root / 'backend/wheelhouse')], check=True)
    web_command=[sys.executable, str(root / 'web/tools/install.py'), '--prefix', str(prefix / 'web'),
                 '--python', sys.executable, '--service', args.service, '--access', args.access,
                 '--mode', 'follow', '--active-descriptor', str(args.active_descriptor)]
    if args.bind:web_command+=['--bind',args.bind]
    for origin in args.allowed_origin:web_command+=['--allowed-origin',origin]
    subprocess.run(web_command,check=True)
    print('Installed separate backend/Web environments; no source, Web listener or service started: ' + str(prefix))


if __name__ == '__main__':
    main()
