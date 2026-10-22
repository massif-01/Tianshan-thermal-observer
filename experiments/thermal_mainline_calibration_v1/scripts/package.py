"""Create a new local evidence ZIP and additive patch; never stages, commits or pushes."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REL = Path('experiments')/ROOT.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def members():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and '.pytest_cache' not in p.parts and p.suffix not in ['.so','.pyc','.zip']
                  and p.name not in ['bundle-files.json','source.patch'])


def source_files():
    files=[]
    for p in members():
        parts=p.relative_to(ROOT).parts
        if parts[0] in ['tool','scripts','config','tests','baseline'] or len(parts)==1 and p.suffix in ['.md','.txt','.ini']:
            files.append(p)
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--a1-zip',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    patch=[]
    for file in source_files():
        name=str(REL/file.relative_to(ROOT))
        patch.extend([f'diff --git a/{name} b/{name}\n','new file mode 100644\n'])
        patch.extend(difflib.unified_diff([],file.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))
    (ROOT/'source.patch').write_text(''.join(patch))
    payload={str(f.relative_to(ROOT)):f.read_bytes() for f in members()}
    payload['source.patch']=(ROOT/'source.patch').read_bytes()
    sealed=a.a1_zip.read_bytes()
    if sha(sealed)!='db423023538e8e4b8a6afa0d687b293ea7808b16815d4334f58721afd8dfaa01':
        raise ValueError('early-delivered A1 package changed')
    payload['A1-G2只读基线包.zip']=sealed
    index={name:dict(bytes=len(content),sha256=sha(content)) for name,content in sorted(payload.items())}
    manifest=dict(schema='TTO-MAINLINE-EVIDENCE-FILES-v1',root=str(REL),files=index,
                  notes=['Index excludes its own bytes to avoid self reference','Old raw archive is referenced by SHA; normalized replay data included',
                         'Historical registry entries contain original paths; recreate a new local registry when replaying',
                         'C binaries omitted; original source and build commands included'])
    manifest_bytes=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    (ROOT/'bundle-files.json').write_bytes(manifest_bytes)
    payload['bundle-files.json']=manifest_bytes
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in sorted(payload.items()):
            info=zipfile.ZipInfo(str(REL/name),date_time=(2026,10,21,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,content,compresslevel=9)
    with zipfile.ZipFile(a.output) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for name,meta in index.items():
            if sha(z.read(str(REL/name)))!=meta['sha256']:
                raise ValueError('ZIP member checksum mismatch: '+name)
    receipt=dict(file=str(a.output.resolve()),bytes=a.output.stat().st_size,sha256=sha(a.output.read_bytes()),
                 indexed_files=len(index),zip_crc_and_all_members_verified=True,A1_sha256=sha(sealed),
                 old_files_modified=False,device_access=False,push_or_PR=False)
    Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    main()
