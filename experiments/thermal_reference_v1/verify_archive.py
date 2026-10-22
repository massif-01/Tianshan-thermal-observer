"""Verify the evidence ZIP CRC and every member SHA; optional extraction into a new directory."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile


def verify(path,extract=None):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None,'CRC mismatch'
        manifest=json.loads(archive.read('thermal_reference_v1/SHA256.json'))
        expected=manifest['files']
        actual=set(archive.namelist())-{'thermal_reference_v1/SHA256.json'}
        assert actual==set(expected),'Unlisted or missing member'
        for name,entry in expected.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==entry['sha256'],name
            assert len(archive.read(name))==entry['bytes'],name
        if extract:
            target=Path(extract)
            assert not target.exists(),'Use a fresh extraction directory'
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
            target.mkdir(parents=True);archive.extractall(target)
    return dict(status='pass',CRC='pass',members=len(expected),extracted_to=str(extract) if extract else None,
                note='Package integrity only; not a device, instrument, model, or control validation')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip',type=Path);p.add_argument('--extract',type=Path)
    a=p.parse_args();print(json.dumps(verify(a.zip,a.extract),ensure_ascii=False))
