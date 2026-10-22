"""Offline independent replay entry. Write only a NEW output directory."""
import argparse
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent


def forbidden(*args,**kwargs):
    raise AssertionError('Network calls are forbidden during this frozen offline replay')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--figures',action='store_true',help='Also render Chinese figures/report; a CJK font is needed')
    args=ap.parse_args()
    out=args.output.resolve()
    if out.exists():
        raise FileExistsError('Output must not exist')
    tests=subprocess.run([sys.executable,'-m','pytest','-q','-c',str(ROOT/'pytest.ini'),'-p','no:cacheprovider',str(ROOT/'tests')],
                         cwd=ROOT,capture_output=True,text=True)
    print(tests.stdout,end='')
    if tests.returncode:
        print(tests.stderr,file=sys.stderr);raise SystemExit(tests.returncode)
    import run_study
    sys.argv=['run_study.py','--output',str(out)]
    # Guard a forbidden side effect independently of pure processing identities.
    with patch.object(socket.socket,'connect',forbidden),patch.object(socket.socket,'connect_ex',forbidden),patch.object(socket,'create_connection',forbidden):
        run_study.main()
    (out/'rerun-tests.log').write_text(tests.stdout+tests.stderr)
    from diagnostics import run
    run(out)
    if args.figures:
        from report import figures,report
        figures(out);report(out)
