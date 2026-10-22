"""Populate the standalone research cache from the supplied original handoff; offline only."""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--handoff',type=Path,required=True);args=parser.parse_args()
source=args.handoff.resolve();target=root/'handoff'
subprocess.run([sys.executable,str(source/'scripts/verify_handoff.py')],check=True)
if source!=target.resolve():
    if target.exists():
        # Evidence contains lightweight handoff references; fill only the absent original inputs.
        for p in source.rglob('*'):
            if p.is_file() and not (target/p.relative_to(source)).exists():
                (target/p.relative_to(source)).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target/p.relative_to(source))
    else:shutil.copytree(source,target)
cache=root/'cache';cache.mkdir(exist_ok=True)
for name in ('L-seven-conditions-original','S-shortqa-original-complete','previous-exploration-evidence','greybox-v1-evidence','M-midload-original','M-independent-review'):
    dest=cache/name
    if dest.exists():continue
    with zipfile.ZipFile(target/'inputs'/f'{name}.zip') as z:
        assert z.testzip() is None
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(dest)
if not (cache/'M-trial').exists():
    with zipfile.ZipFile(cache/'M-midload-original/trial-result.zip') as z:
        assert z.testzip() is None
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(cache/'M-trial')
print('Offline cache ready; original archive identities verified. Use research.py all --out a-new-directory.')
