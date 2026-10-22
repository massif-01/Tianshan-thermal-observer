#!/usr/bin/env python3
"""Actual offline Conda 0.1.2 -> 0.2.0 upgrade in one NEW temporary prefix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(a):
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    old=Path(a.old_bundle).resolve();new=Path(a.new_bundle).resolve();prefix=out/'installed with spaces'
    bundle_sha=sha(new) if new.is_file() else None
    if new.is_file():
        if not zipfile.is_zipfile(new):raise ValueError('new bundle is not a zip archive')
        extracted=out/'candidate-bundle';extracted.mkdir()
        with zipfile.ZipFile(new) as archive:
            for name in archive.namelist():
                item=Path(name)
                if item.is_absolute() or '..' in item.parts:raise ValueError('unsafe bundle entry')
            archive.extractall(extracted)
        roots=[p for p in extracted.iterdir() if p.is_dir()]
        if len(roots)!=1:raise ValueError('candidate bundle must contain one root directory')
        new=roots[0]
    conda=Path(a.conda).resolve()
    env=dict(os.environ,CONDA_EXE=str(conda),CONDA_PKGS_DIRS=str(Path(a.conda_cache).resolve()),CONDA_REGISTER_ENVS='false',CONDA_PIP_INTEROP_ENABLED='false',CONDA_CHANNELS='conda-forge',PIP_DISABLE_PIP_VERSION_CHECK='1')
    env.pop('PYTHONPATH',None)
    base=Path(subprocess.check_output([str(conda),'info','--base'],env=env,text=True).strip())
    def base_snapshot():
        files=[*base.glob('conda-meta/*.json'),base/'conda-meta/history',base/'bin/python',base/'bin/conda']
        return {str(p.relative_to(base)):sha(p) for p in files if p.is_file()}
    def run(name,cmd):
        r=subprocess.run(cmd,env=env,cwd=out,capture_output=True,text=True,timeout=600)
        (out/(name+'.log')).write_text(r.stdout+r.stderr)
        assert r.returncode==0,(name,r.returncode,r.stdout[-300:],r.stderr[-500:])
        return r
    before_base=base_snapshot()
    args=['--prefix',str(prefix),'--offline','--offline-wheelhouse',str(Path(a.wheelhouse).resolve())]
    run('old-install',['sh',str(old/'install.sh'),*args])
    python=str(prefix/'conda-env/bin/python')
    old_identity=json.loads((prefix/'installation.json').read_text());assert old_identity['version']=='0.1.2'
    config=prefix/'config/local.json';c=json.loads(config.read_text())
    c['run']['default_duration_s']=60
    # Preserve the old closed-merge feature key and deliberately unchanged cadence.
    assert c['features']['power_current_rails']==['vdd_gpu_soc','vdd_cpu_cv','vin_sys_5v0']
    config.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    code='''from pathlib import Path
from tto.demo import record_demo
from tto.dataset import freeze_split
from tto.training import train
from tto.report import run_report
import sys
import json
root=Path(sys.argv[1]);runs=record_demo(root/'runs',count=3,seconds=400)
f=freeze_split(runs,root/'frozen');train(f/'dataset.json',f/'split.json',root/'old-model.json')
run_report(runs[0],root/'old-report')
(root/'report-source.json').write_text(json.dumps({'run_name':runs[0].name}))
'''
    run('old-software-records',[python,'-c',code,str(prefix/'retained-user-artifacts')])
    retained=[config,*[p for p in (prefix/'retained-user-artifacts').rglob('*') if p.is_file()]]
    before={str(p.relative_to(prefix)):sha(p) for p in retained}
    identity_sha=sha(prefix/'installation.json')
    run('new-upgrade',['sh',str(new/'install.sh'),*args])
    assert before=={name:sha(prefix/name) for name in before}
    assert sha(prefix/'installation-history'/(identity_sha+'.json'))==identity_sha
    identity=json.loads((prefix/'installation.json').read_text());assert identity['version']=='0.2.0' and identity['non_editable'] and identity['offline_doctor_passed']
    assert before_base==base_snapshot()
    assert run('launcher-version',[str(prefix/'tto'),'--version']).stdout.strip()=='0.2.0'
    first_run=prefix/'retained-user-artifacts/runs'/json.loads((prefix/'retained-user-artifacts/report-source.json').read_text())['run_name']
    run('historical-report',[str(prefix/'tto'),'report','--run',str(first_run),'--output',str(out/'historical-report-after')])
    old_report=json.loads((prefix/'retained-user-artifacts/old-report/report.json').read_text())
    report=json.loads((out/'historical-report-after/report.json').read_text())
    for key in ('origin_count','normal_auto_origins','label_counts','availability'):
        assert old_report[key]==report[key],key
    assert old_report['recorded_results']['scored_records']==report['recorded_results']['scored_records']
    assert old_report['recorded_results']['quality_isolations']==report['recorded_results']['quality_isolations']
    # Existing frozen schema1 dataset/model remain evaluable after the upgrade.
    artifacts=prefix/'retained-user-artifacts'
    run('old-frozen-evaluate',[str(prefix/'tto'),'evaluate','--dataset',str(artifacts/'frozen/dataset.json'),'--split',str(artifacts/'frozen/split.json'),'--models',str(artifacts/'old-model.json'),'--output',str(out/'old-model-evaluation-after')])
    assert before=={name:sha(prefix/name) for name in before}
    result={'passed':True,'real_devices':False,'target_linux_executed':sys.platform=='linux','old_version':'0.1.2','new_version':'0.2.0',
            'source_wheel_import_verified_by_installer':True,'retained_artifacts_sha256':before,'conda_base_unchanged':True,
            'conda_base_files_checked':len(before_base),'conda_base_identity_sha256':hashlib.sha256(json.dumps(before_base,sort_keys=True).encode()).hexdigest(),
            'old_installation_identity_preserved_sha256':identity_sha,'old_record_contract_report_unchanged':True,'old_frozen_model_offline_evaluation_passed':True,
            'configuration_feature_key_preserved':True,'environment_python':identity['python'],'new_wheel_sha256':identity['wheel_sha256'],'new_bundle_sha256':bundle_sha}
    (out/'findings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='retained_artifacts_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--old-bundle',required=True);p.add_argument('--new-bundle',required=True);p.add_argument('--conda',required=True);p.add_argument('--conda-cache',required=True);p.add_argument('--wheelhouse',required=True)
    verify(p.parse_args())
