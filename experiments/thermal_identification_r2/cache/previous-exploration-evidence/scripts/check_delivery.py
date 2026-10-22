"""Portable read-only ZIP/CRC/member-SHA check; no extraction, network or private run needed."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def check(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, f'CRC failed: {path}'
        indexes=[n for n in ['SHA256.json','archive-file-hashes.json','complement-SHA256.json'] if n in z.namelist()]
        # A complement also has the full original index, whose other 39 files are intentionally external.
        if 'complement-SHA256.json' in indexes:indexes=['complement-SHA256.json']
        assert indexes, f'No supported member index: {path}'
        checks=0
        for name in indexes:
            index=json.loads(z.read(name))
            for member,expected in index.items():
                data=z.read(member)
                if isinstance(expected,dict):
                    assert len(data)==expected['bytes'],member
                    expected=expected['sha256']
                assert hashlib.sha256(data).hexdigest()==expected,member
                checks+=1
        return dict(file=Path(path).name,bytes=Path(path).stat().st_size,
                    sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    member_checks=checks,crc='passed',sha='passed')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zips',type=Path,nargs='+')
    for path in p.parse_args().zips:print(json.dumps(check(path),ensure_ascii=False))
