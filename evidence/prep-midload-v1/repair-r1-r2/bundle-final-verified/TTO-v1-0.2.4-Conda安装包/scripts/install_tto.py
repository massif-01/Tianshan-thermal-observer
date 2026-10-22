#!/usr/bin/env python3
"""Install a reviewed wheel locally, without configuring/connecting devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shlex
import shutil
import sys
from datetime import datetime, timezone

VERIFY = '''
import hashlib,importlib.metadata as metadata,json,sys,zipfile
from pathlib import Path
import tto
assert sys.version_info[:2]==(3,10)
installed=Path(tto.__file__).resolve().parent
assert Path(sys.prefix) in installed.parents and 'site-packages' in installed.parts
files={}
with zipfile.ZipFile(sys.argv[1]) as z:
 for name in z.namelist():
  if name.startswith('tto/') and not name.endswith('/'):
   relative=name[4:];content=z.read(name)
   assert content==(installed/relative).read_bytes(),relative
   files[relative]=hashlib.sha256(content).hexdigest()
versions={}
for line in Path(sys.argv[2]).read_text().splitlines():
 if line and not line.startswith('#'):
  name,version=line.split('==');versions[name]=metadata.version(name)
  assert versions[name]==version,name
assert tto.__version__==sys.argv[3]
assert metadata.version('tianshan-thermal-observer')==sys.argv[3]
print(json.dumps({'version':tto.__version__,'python':sys.version,'import_path':str(installed),'non_editable':True,'installed_files_sha256':files,'dependencies':versions}))
'''

LAUNCHER = '''#!/bin/sh
set -eu
export CONDA_PIP_INTEROP_ENABLED=false
install_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$install_dir"
exec {conda_exe} run --no-capture-output --prefix "$install_dir/conda-env" python -I -m tto "$@"
'''

MIDLOAD_LAUNCHER = '''#!/bin/sh
set -eu
export CONDA_PIP_INTEROP_ENABLED=false
install_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$install_dir"
exec {conda_exe} run --no-capture-output --prefix "$install_dir/conda-env" python -I "$install_dir/thermal_trials/run_midload.py" "$@"
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(args):
    if sys.version_info < (3,8):
        raise ValueError('预装Conda的base Python需3.8或更高；TTO会单独使用Python 3.10。')
    bundle=Path(__file__).resolve().parent.parent
    manifest=json.loads((bundle/'install-manifest.json').read_text())
    version=manifest['version']
    wheel=bundle/'wheels'/('tianshan_thermal_observer-'+version+'-py3-none-any.whl')
    for name,expected in manifest['files'].items():
        path=bundle/name
        if not path.is_file() or digest(path)!=expected:
            raise ValueError('安装包文件缺失或SHA不匹配：'+name+'；请重新取得完整安装包。')
    wheelhouse=Path(args.offline_wheelhouse).expanduser().resolve() if args.offline_wheelhouse else None
    if wheelhouse is not None and not wheelhouse.is_dir():
        raise ValueError('离线依赖目录不存在：'+str(wheelhouse))
    if args.offline and wheelhouse is None:
        raise ValueError('--offline需要同时指定--offline-wheelhouse，Conda的Python/pip也需已有本机缓存。')
    conda=Path(args.conda_exe).expanduser().resolve()
    prefix=Path(args.prefix).expanduser().resolve()
    marker=prefix/'.tto-install.json'
    previous=None
    if prefix.exists() and any(prefix.iterdir()):
        previous=json.loads(marker.read_text()) if marker.is_file() else None
        supported={'0.1.2','0.2.0','0.2.1','0.2.2','0.2.3','0.2.4'}
        if not previous or previous.get('version') not in supported or previous.get('installer_version') not in (1,2,3) or previous.get('environment_manager') not in (None,'venv','conda'):
            raise ValueError('目录已有其他内容，未改动：'+str(prefix)+'；请用--prefix指定新的独立目录。')
    prefix.mkdir(parents=True,exist_ok=True)
    # Ownership is recorded before environment creation so interrupted installs
    # can resume. installation.json remains the last verified installed identity.
    marker.write_text(json.dumps({'installer_version':3,'version':previous['version'] if previous else version,'candidate_version':version,'environment_manager':previous.get('environment_manager') if previous else 'conda','status':'installing'})+'\n')
    installed_identity=prefix/'installation.json'
    if installed_identity.is_file():
        history=prefix/'installation-history';history.mkdir(exist_ok=True)
        saved=history/(digest(installed_identity)+'.json')
        if not saved.exists():saved.write_bytes(installed_identity.read_bytes())
    env=dict(os.environ)
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    env.update(PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_INPUT='1',PIP_CACHE_DIR=str(prefix/'.cache/pip'))
    env.setdefault('CONDA_PKGS_DIRS',str(prefix/'.cache/conda'))
    env['CONDA_PIP_INTEROP_ENABLED']='false'
    environment=prefix/'conda-env'
    python=environment/'bin/python'
    runner=[str(conda),'run','--no-capture-output','--prefix',str(environment)]
    conda_offline=['--offline'] if args.offline else []
    print('安装TTO '+version+' → '+str(prefix),flush=True)
    if previous and previous.get('environment_manager')!='conda':
        print('保留已有配置、模型、数据和旧环境；切换TTO入口到独立Conda环境。',flush=True)
    if not python.is_file():
        operation='install' if (environment/'conda-meta/history').is_file() else 'create'
        print('1/5 使用预装Conda创建独立Python 3.10环境',flush=True)
        subprocess.run([str(conda),operation,'--yes','--prefix',str(environment),*(['--no-default-packages'] if operation=='create' else []),*conda_offline,'python=3.10','pip'],env=env,check=True)
    pip_ready=subprocess.run(runner+['python','-m','pip','--version'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not pip_ready:
        print('恢复本TTO环境的pip',flush=True)
        subprocess.run([str(conda),'install','--yes','--prefix',str(environment),'--force-reinstall',*conda_offline,'pip'],env=env,check=True)
    print('2/5 安装锁定依赖'+('（离线）' if wheelhouse else '（需要下载时会联网）'),flush=True)
    command=runner+['python','-m','pip','install']
    if wheelhouse:command+=['--no-index','--find-links',str(wheelhouse)]
    subprocess.run(command+['-r',str(bundle/'requirements-locked.txt')],env=env,check=True)
    print('3/5 安装已核对的wheel',flush=True)
    subprocess.run(runner+['python','-m','pip','install','--no-index','--no-deps','--force-reinstall',str(wheel)],env=env,check=True)
    subprocess.run(runner+['python','-m','pip','check'],env=env,check=True)
    print('4/5 核对实际导入文件、版本及依赖',flush=True)
    result=subprocess.run(runner+['python','-I','-c',VERIFY,str(wheel),str(bundle/'requirements-locked.txt'),version],env=env,check=True,capture_output=True,text=True)
    identity=json.loads(result.stdout)
    config=prefix/'config/local.json';config.parent.mkdir(exist_ok=True)
    if not config.exists():
        settings=json.loads((bundle/'config/tto.example.json').read_text())
        settings['storage']['data_root']=str(prefix/'runs')
        with config.open('x') as f:json.dump(settings,f,ensure_ascii=False,indent=2);f.write('\n')
    print('5/5 离线配置检查（不连接设备）',flush=True)
    subprocess.run(runner+['python','-m','tto','doctor','--config',str(config)],env=env,cwd=prefix,check=True)
    launcher=prefix/'tto';launcher.write_text(LAUNCHER.format(conda_exe=shlex.quote(str(conda))));launcher.chmod(0o755)
    trial_source=bundle/'scripts/thermal_trials'
    if trial_source.is_dir():
        trial_dir=prefix/'thermal_trials';trial_dir.mkdir(exist_ok=True)
        for path in sorted(trial_source.iterdir()):
            if path.is_file() and path.suffix in ('.py','.json','.md'):shutil.copy2(path,trial_dir/path.name)
        trial_launcher=prefix/'tto-midload'
        trial_launcher.write_text(MIDLOAD_LAUNCHER.format(conda_exe=shlex.quote(str(conda))));trial_launcher.chmod(0o755)
        # The same isolated script used by the installed launcher; no target/credentials.
        trial_check=subprocess.run(runner+['python','-I',str(trial_dir/'run_midload.py'),'--plan'],env=env,cwd=prefix,check=True,capture_output=True,text=True)
        trial_identity=json.loads(trial_check.stdout)['runtime']
        identity['midload_runner']=dict(entry=str(trial_launcher),runtime=trial_identity,
            files_sha256={p.name:digest(p) for p in sorted(trial_dir.iterdir()) if p.is_file()})
    identity.update(environment_manager='conda',environment_prefix=str(environment),conda_executable=str(conda),conda_version=subprocess.check_output([str(conda),'--version'],env=env,text=True).strip(),wheel_sha256=digest(wheel),dependency_lock_sha256=digest(bundle/'requirements-locked.txt'),config_path=str(config),checked_at_utc=datetime.now(timezone.utc).isoformat(),offline_doctor_passed=True)
    (prefix/'installation.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n')
    marker.write_text(json.dumps({'installer_version':3,'version':version,'environment_manager':'conda','previous_version':previous.get('version') if previous else None,'status':'verified'})+'\n')
    print('\n安装完成：TTO '+version+'\n运行入口：'+str(launcher)+'\n中等负载入口：'+str(prefix/'tto-midload')+'\n本机配置：'+str(config)+'\n安装身份：'+str(prefix/'installation.json')+'\n未启动采集、设备连接或后台服务。',flush=True)


def main():
    parser=argparse.ArgumentParser(description='TTO本地安装：创建独立环境、安装锁定包、核对身份、离线doctor。')
    parser.add_argument('--conda-exe',required=True,help=argparse.SUPPRESS)
    parser.add_argument('--offline',action='store_true',help='Conda和pip均离线；需要Conda本机缓存及--offline-wheelhouse')
    parser.add_argument('--prefix',default=str(Path.home()/'TTO'),help='独立安装目录，默认~/TTO')
    parser.add_argument('--offline-wheelhouse',help='匹配目标系统/CPU/Python的离线依赖wheel目录；指定后pip禁止访问索引')
    args=parser.parse_args()
    try:install(args)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        detail=str(error) if isinstance(error,ValueError) else ('本地命令失败，退出码 '+str(error.returncode) if isinstance(error,subprocess.CalledProcessError) else type(error).__name__)
        print('\n安装未完成：'+detail+'\n配置和数据不会被覆盖；处理上述问题后可重跑。',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
