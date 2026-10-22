#!/usr/bin/env python3
"""Install a reviewed wheel locally, without configuring/connecting devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

VERIFY = '''
import hashlib,importlib.metadata as metadata,json,sys,zipfile
from pathlib import Path
import tto
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
install_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$install_dir"
exec "$install_dir/.venv/bin/tto" "$@"
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(args):
    if sys.version_info < (3,10):
        raise ValueError('需要Python 3.10或更高；Ubuntu 22.04默认Python 3.10。本轮验证使用3.10.18。')
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
    prefix=Path(args.prefix).expanduser().resolve()
    marker=prefix/'.tto-install.json'
    if prefix.exists() and any(prefix.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text()).get('version')!=version:
            raise ValueError('目录已有其他内容，未改动：'+str(prefix)+'；请用--prefix指定新的独立目录。')
    prefix.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps({'installer_version':1,'version':version})+'\n')
    env=dict(os.environ)
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    env.update(PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_INPUT='1',PIP_CACHE_DIR=str(prefix/'.cache/pip'))
    python=prefix/'.venv/bin/python'
    print('安装TTO '+version+' → '+str(prefix),flush=True)
    pip_ready = python.is_file() and subprocess.run([str(python),'-m','pip','--version'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0
    if not pip_ready:
        print('1/5 创建独立Python环境',flush=True)
        result=subprocess.run([sys.executable,'-m','venv',str(prefix/'.venv')],env=env)
        if result.returncode:
            raise ValueError('虚拟环境创建失败。Ubuntu 22.04可先执行 sudo apt install python3-venv，再运行本脚本。')
    print('2/5 安装锁定依赖'+('（离线）' if wheelhouse else '（需要下载时会联网）'),flush=True)
    command=[str(python),'-m','pip','install']
    if wheelhouse:command+=['--no-index','--find-links',str(wheelhouse)]
    subprocess.run(command+['-r',str(bundle/'requirements-locked.txt')],env=env,check=True)
    print('3/5 安装已核对的wheel',flush=True)
    subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps','--force-reinstall',str(wheel)],env=env,check=True)
    subprocess.run([str(python),'-m','pip','check'],env=env,check=True)
    print('4/5 核对实际导入文件、版本及依赖',flush=True)
    result=subprocess.run([str(python),'-I','-c',VERIFY,str(wheel),str(bundle/'requirements-locked.txt'),version],env=env,check=True,capture_output=True,text=True)
    identity=json.loads(result.stdout)
    config=prefix/'config/local.json';config.parent.mkdir(exist_ok=True)
    if not config.exists():
        settings=json.loads((bundle/'config/tto.example.json').read_text())
        settings['storage']['data_root']=str(prefix/'runs')
        with config.open('x') as f:json.dump(settings,f,ensure_ascii=False,indent=2);f.write('\n')
    launcher=prefix/'tto';launcher.write_text(LAUNCHER);launcher.chmod(0o755)
    print('5/5 离线配置检查（不连接设备）',flush=True)
    subprocess.run([str(python),'-m','tto','doctor','--config',str(config)],env=env,cwd=prefix,check=True)
    identity.update(wheel_sha256=digest(wheel),dependency_lock_sha256=digest(bundle/'requirements-locked.txt'),config_path=str(config),checked_at_utc=datetime.now(timezone.utc).isoformat(),offline_doctor_passed=True)
    (prefix/'installation.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n')
    print('\n安装完成：TTO '+version+'\n运行入口：'+str(launcher)+'\n本机配置：'+str(config)+'\n安装身份：'+str(prefix/'installation.json')+'\n未启动采集、设备连接或后台服务。',flush=True)


def main():
    parser=argparse.ArgumentParser(description='TTO本地安装：创建独立环境、安装锁定包、核对身份、离线doctor。')
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
