"""Index and package this private review handoff; no recursive historical ZIPs."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--zip',type=Path,required=True);args=ap.parse_args()
    dest=args.zip.resolve()
    if ROOT in dest.parents:raise ValueError('Write archive outside payload directory')
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=ROOT/'SHA256.json'
           and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
    index={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files}
    (ROOT/'SHA256.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)))
        z.write(ROOT/'SHA256.json','SHA256.json')
    print(json.dumps(dict(archive=str(dest),bytes=dest.stat().st_size,sha256=sha(dest),indexed_files=len(index))))
