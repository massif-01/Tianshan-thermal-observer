"""One offline entry: verify archive, native replay, frozen attempts, time diagnostics, plots/tests."""
from pathlib import Path
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[key]='1'
import argparse,datetime as dt,hashlib,json,platform,resource,shutil,subprocess,sys,time,zipfile
ROOT=Path(__file__).absolute().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'cache/matplotlib')
sys.path.insert(0,str(ROOT/'vendor'))
from common import read,write,sha
from replay_new import replay
from trajectories import generate
from compare_surface import compare
from plots_report import make


def run(archive,out):
    start=time.perf_counter();out=Path(out).absolute()
    if out.exists():raise ValueError('Use a new output directory; earlier evidence stays unchanged')
    out.mkdir(parents=True);archive=Path(archive).absolute()
    assert sha(archive)=='c0c3e1895ca9893d90a27559a491093aa4de1209ab1ae317494adc5ef3c94273'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('SHA256.json'))
        for name,e in manifest['files'].items():
            b=z.read(name);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(out/'input')
    evidence=out/'input'
    protected={n:sha(evidence/n) for n in manifest['files']}
    models={p.name:sha(p) for p in (ROOT/'models').glob('*.json')}
    expected=read(ROOT/'source-identity.json');assert models==expected['frozen_models']
    for n,h in expected['vendor_files'].items():assert sha(ROOT/n)==h,n
    network_attempts=[]
    def audit(event,args):
        if event in ['socket.connect','socket.getaddrinfo','socket.bind','socket.listen']:
            network_attempts.append(event);raise RuntimeError('No network/device access in offline study')
    sys.addaudithook(audit)
    import greybox
    def forbidden(*a,**kw):raise AssertionError('Dynamic parameter training forbidden')
    greybox.fit=greybox.solve=greybox.least_squares=forbidden
    import sklearn.linear_model
    sklearn.linear_model.Ridge.fit=forbidden
    data=replay(evidence,out/'data.json')
    write(out/'stage1-freeze.json',dict(spec_sha256=sha(ROOT/'spec.json'),archive_sha256=sha(archive),models=models,
        data_sha256=sha(out/'data.json'),code_sha256={p.name:sha(p) for p in ROOT.glob('*.py')},frozen_before_model_generation=True))
    result=out/'results';generate(data,result);summary=compare(evidence,data,result);make(data,result)
    test_env=os.environ.copy();test_env['TTO_YET_TEST_DATA_PATH']=str(out/'data.json')
    test=subprocess.run([sys.executable,'-m','pytest','-q','-c','/dev/null',str(ROOT/'tests'),'-o','cache_dir='+str(out/'pytest-cache')],capture_output=True,text=True,env=test_env)
    (out/'tests.log').write_text(test.stdout+test.stderr);assert test.returncode==0,test.stdout+test.stderr
    assert {n:sha(evidence/n) for n in manifest['files']}==protected
    assert {p.name:sha(p) for p in (ROOT/'models').glob('*.json')}==models
    usage=resource.getrusage(resource.RUSAGE_SELF)
    import numpy,scipy,matplotlib
    write(out/'completion.json',dict(status='pass',actual_surface_measurement_received=True,
        actual_file_mapping_verified=summary['actual_CSV_mapping_verified'],legal_model_states=summary['strict_model_states'],
        strictly_time_paired_points=0,valid_model_surface_ranking=False,model_parameter_updates=0,
        surface_state_correction=False,network_attempts=network_attempts,original_255_members_unchanged=True,
        frozen_models_unchanged=True,git_write=False,device_access=False))
    write(out/'environment-resources.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        numpy=numpy.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,
        wall_seconds=time.perf_counter()-start,cpu_user_s=usage.ru_utime,cpu_system_s=usage.ru_stime,
        peak_RSS_native=usage.ru_maxrss,RSS_units='bytes on macOS; KiB on Linux',CPU_BLAS_threads=1,CUDA=False,
        dependency_installation_separate_from_offline_study=True))
    report=result/'TTO-YET610L同步短问答-冻结模型比较报告.md'
    env=read(out/'environment-resources.json')
    rss=env['peak_RSS_native']/(2**20 if sys.platform=='darwin' else 1024)
    report.write_text(report.read_text()+f"\n## 实际离线验收回执\n\n{test.stdout.strip()}\n\n运行环境：{env['platform']}，Python {sys.version.split()[0]}；NumPy {numpy.__version__}、SciPy {scipy.__version__}、Matplotlib {matplotlib.__version__}。CPU单线程，墙钟{env['wall_seconds']:.3f}秒，峰值RSS约{rss:.2f}MiB。运算socket尝试{len(network_attempts)}次，动态参数更新0；未联网设备。此资源是本机离线研究，不是N305现场成绩。\n")
    print(json.dumps(read(out/'completion.json'),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.archive,a.output)
