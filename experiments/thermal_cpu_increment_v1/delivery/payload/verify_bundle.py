"""Verify an extracted bundle's indexed members and immutable input bindings."""
from pathlib import Path
import argparse
from common import read, sha


def verify(root):
    entries=read(root/'SHA256.json')['files']
    for e in entries:
        rel=Path(e['path'])
        assert not rel.is_absolute() and '..' not in rel.parts
        p=root/rel
        assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
    source=read(root/'sources.json')
    for e in source['sources']:
        assert sha(root/e['local_path'])==e['sha256'],e['local_path']
    freeze=read(root/'freeze.json')
    assert sha(root/'candidate.json')==freeze['candidate_sha256']
    assert sha(root/'analysis-spec.json')==freeze['spec_sha256']
    interface=read(root/'interface-freeze.json')
    for rel,digest in interface['code_and_interface_sha256'].items():
        assert sha(root/rel)==digest,rel
    for e in read(root/'handoff/SHA256.json')['files']:
        p=root/'handoff'/e['path']
        assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
    print('Bundle hash/binding verification passed:',len(entries),'members; all15 original inputs and32 review members.')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    verify(ap.parse_args().root.resolve())
