"""Offline hash/binding verification only. No install, network, device or historical-script execution."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


if __name__=='__main__':
    top=json.loads((ROOT/'SHA256.json').read_text())
    for name,item in top.items():
        p=ROOT/name
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],name
    nested={}
    for label in ('field','modeling'):
        base=ROOT/'evidence'/label
        index=json.loads((base/'SHA256.json').read_text())
        for name,item in index.items():
            p=base/name
            assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],(label,name)
        nested[label]=len(index)
    spec=json.loads((ROOT/'evidence/modeling/spec.json').read_text())
    field=json.loads((ROOT/'evidence/field/remote-result/run/summary.json').read_text())
    assert spec['run_id']==field['native_run_id']=='5d5e5a4a-6081-49d8-a9be-5156d9ca2ab3'
    assert sha(ROOT/'evidence/modeling/vendor/src/tto_field/research/models/primary.json')==spec['model_sha256']
    assert sha(ROOT/'evidence/modeling/vendor/src/tto_field/research/observer-spec.json')==spec['observer_spec_sha256']
    summary=json.loads((ROOT/'analysis/cpu-memory-time-summary.json').read_text())
    assert summary['new_field_runs']==summary['theta_fits']==summary['lag_or_threshold_searches']==0
    assert summary['groups'][0]['n']==2706
    print(json.dumps(dict(payload_files_verified=len(top),nested_original_indexes=nested,
                         same_run_and_frozen_identity=True,supplement_is_offline_only=True)))
