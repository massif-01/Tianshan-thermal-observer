#!/usr/bin/env python3
"""Real installer regression in NEW temp prefixes, offline dependency wheels only.
Never installs in the user's default directory or contacts devices.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output,wheelhouse,bundle=None):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    bundle=Path(bundle).resolve() if bundle else Path(__file__).resolve().parent.parent
    wheelhouse=Path(wheelhouse).resolve()
    env=dict(os.environ,TTO_INSTALL_PYTHON=sys.executable,PIP_DISABLE_PIP_VERSION_CHECK='1')
    cases={}
    def run(name,args,expected=0):
        result=subprocess.run(['sh',str(bundle/'install.sh'),*args],env=env,capture_output=True,text=True,timeout=600)
        (output/(name+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode==expected,(name,result.returncode,result.stdout[-300:],result.stderr[-500:])
        return result
    prefix=output/'installed with spaces'
    arguments=['--prefix',str(prefix),'--offline-wheelhouse',str(wheelhouse)]
    run('success',arguments)
    identity=json.loads((prefix/'installation.json').read_text())
    assert identity['version']=='0.1.2' and identity['non_editable'] and identity['offline_doctor_passed']
    assert identity['wheel_sha256']==sha(bundle/'wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl')
    assert str(prefix/'.venv') in identity['import_path']
    config=prefix/'config/local.json';settings=json.loads(config.read_text())
    assert settings['orin']['base_url'] is None and settings['tianshan']['base_url'] is None
    assert settings['storage']['data_root']==str(prefix/'runs')
    version=subprocess.run([str(prefix/'tto'),'--version'],capture_output=True,text=True,check=True)
    assert version.stdout.strip()=='0.1.2'
    (output/'launcher-version.log').write_text(version.stdout)
    cases['success']={'passed':True,'version':'0.1.2','prefix_has_spaces':True,'non_editable':True,'wheel_files_equal_installed':True,'offline_dependencies':True,'config_endpoints_unset':True}
    settings['run']['default_duration_s']=60
    config.write_text(json.dumps(settings,indent=2)+'\n')
    sentinel=prefix/'runs/user-record.txt';sentinel.parent.mkdir();sentinel.write_text('synthetic user-owned record\n')
    model=prefix/'user-model.json';model.write_text('{"synthetic_user_owned":true}\n')
    preserved={str(p.relative_to(prefix)):sha(p) for p in (config,sentinel,model)}
    run('repeat-preserves-data',arguments)
    assert preserved=={name:sha(prefix/name) for name in preserved}
    cases['repeat']={'passed':True,'config_records_model_unchanged':preserved}
    # A failed venv bootstrap can leave python present but pip absent.
    # Move ONLY this test environment's pip files to reproduce that partial state.
    site=Path(identity['import_path']).parent
    disabled=output/'disabled-pip';disabled.mkdir()
    for path in [site/'pip',*site.glob('pip-*.dist-info')]:shutil.move(str(path),str(disabled/path.name))
    run('partial-bootstrap-retry',arguments)
    assert preserved=={name:sha(prefix/name) for name in preserved}
    cases['partial_bootstrap_retry']={'passed':True,'missing_pip_recovered':True,'config_records_model_unchanged':True}
    occupied=output/'unrelated-directory';occupied.mkdir();(occupied/'do-not-touch.txt').write_text('existing file')
    original=sha(occupied/'do-not-touch.txt')
    run('occupied-directory',['--prefix',str(occupied),'--offline-wheelhouse',str(wheelhouse)],1)
    assert sha(occupied/'do-not-touch.txt')==original and len(list(occupied.iterdir()))==1
    cases['occupied']={'passed':True,'preexisting_file_unchanged':True}
    missing=output/'missing-wheelhouse-prefix'
    run('missing-wheelhouse',['--prefix',str(missing),'--offline-wheelhouse',str(output/'no-wheelhouse')],1)
    assert not missing.exists()
    cases['missing_wheelhouse']={'passed':True,'target_not_created':True}
    tampered=output/'tampered-bundle';tampered.mkdir()
    for name in ('install.sh','install-manifest.json','requirements-locked.txt'):
        shutil.copy2(bundle/name,tampered/name)
    for directory in ('scripts','wheels','config'):
        (tampered/directory).mkdir()
    shutil.copy2(bundle/'scripts/install_tto.py',tampered/'scripts/install_tto.py')
    shutil.copy2(bundle/'config/tto.example.json',tampered/'config/tto.example.json')
    wheel=tampered/'wheels/tianshan_thermal_observer-0.1.2-py3-none-any.whl'
    wheel.write_bytes((bundle/'wheels'/wheel.name).read_bytes()+b'tampered')
    rejected=output/'tampered-prefix'
    result=subprocess.run(['sh',str(tampered/'install.sh'),'--prefix',str(rejected),'--offline-wheelhouse',str(wheelhouse)],env=env,capture_output=True,text=True,timeout=30)
    (output/'tampered-wheel.log').write_text(result.stdout+result.stderr)
    assert result.returncode==1 and 'SHA' in result.stderr and not rejected.exists()
    cases['tampered_wheel']={'passed':True,'rejected_before_install':True}
    # Doctor does not call collect/shadow, and installation creates no run.
    assert list((prefix/'runs').iterdir())==[sentinel]
    cases['no_collect']={'passed':True,'no_observation_run_created':True,'no_device_endpoints_configured':True}
    (output/'findings.json').write_text(json.dumps({'passed':True,'cases':cases,'python':sys.version,'real_devices':False,'target_linux_executed':sys.platform=='linux'},ensure_ascii=False,indent=2))
    print(json.dumps({'passed':True,'cases':len(cases),'output':str(output),'real_devices':False},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--wheelhouse',required=True);p.add_argument('--bundle')
    a=p.parse_args();verify(a.output,a.wheelhouse,a.bundle)
