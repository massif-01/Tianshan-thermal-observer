"""Verify the delivered payload index, frozen sources and current-run binding, offline."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


if __name__=='__main__':
    index=json.loads((ROOT/'SHA256.json').read_text())
    for name,item in index.items():
        p=ROOT/name
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],name
    spec=json.loads((ROOT/'spec.json').read_text())
    freeze=json.loads((ROOT/'design-freeze.json').read_text())
    assert sha(ROOT/'spec.json')==freeze['spec_sha256']
    for name,key in [('models/primary.json','model_sha256'),('observer-spec.json','observer_spec_sha256')]:
        assert sha(ROOT/'vendor/src/tto_field/research'/name)==spec[key]
    manifest=json.loads((ROOT/'inputs/native/manifest.json').read_text())
    for name,digest in manifest['source_identity']['files'].items():
        assert sha(ROOT/'vendor/src/tto'/name)==digest
    assert manifest['observer_run_id']==spec['run_id']
    link=json.loads((ROOT/'inputs/instrument/run-link.json').read_text())
    assert link['native_run_id']==link['imported_run_id']==spec['run_id']
    assert link['original_csv_sha256']==spec['surface']['csv_sha256']
    print(json.dumps(dict(payload_members_verified=len(index),frozen_identity_and_same_run_link=True)))
