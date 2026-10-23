#!/usr/bin/env python3
"""Verify actual non-editable package against the supplied source and wheel."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import sys
import zipfile
from pathlib import Path
import tto


def verify(source,wheel,output):
    source=Path(source).resolve();wheel=Path(wheel).resolve();output=Path(output).resolve()
    installed=Path(tto.__file__).resolve().parent
    assert 'site-packages' in installed.parts and source/'src' not in installed.parents
    digest=lambda b:hashlib.sha256(b).hexdigest()
    files={}
    with zipfile.ZipFile(wheel) as z:
        wheel_files={n[len('tto/'):]:z.read(n) for n in z.namelist() if n.startswith('tto/') and not n.endswith('/')}
        source_files={p.name:p.read_bytes() for p in (source/'src/tto').iterdir() if p.is_file()}
        assert source_files.keys()==wheel_files.keys()
        for name,content in source_files.items():
            assert content==wheel_files[name]==(installed/name).read_bytes()
            files['src/tto/'+name]=digest(content)
    dependencies={}
    for line in (source/'requirements-locked.txt').read_text().splitlines():
        if not line or line.startswith('#'):continue
        name,version=line.split('==');dependencies[name]=metadata.version(name)
        assert dependencies[name]==version
    result={'version':tto.__version__,'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'executable':sys.executable,'import_path':str(installed),'non_editable':True,'wheel':wheel.name,'wheel_sha256':digest(wheel.read_bytes()),'source_equals_wheel_equals_installed':True,'source_files_sha256':files,'dependencies':dependencies,'dependency_lock_sha256':digest((source/'requirements-locked.txt').read_bytes())}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--wheel',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();verify(a.source,a.wheel,a.output)
