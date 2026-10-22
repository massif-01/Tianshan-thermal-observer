"""One offline entry for the actual CLI flow, limited tests, plots, and source readback."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import platform
import resource
import subprocess
import sys
import time
from refprep.files import read,write,lines,sha

ROOT=Path(__file__).absolute().parent


def run(output):
    output=Path(output).absolute()
    if output.exists():raise ValueError('Use a new output directory so earlier evidence is preserved')
    output.mkdir(parents=True)
    env=os.environ.copy()
    for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:env[k]='1'
    receipt=[];started=time.perf_counter()
    def call(label,args,extra=None):
        command=[sys.executable,str(ROOT/'ref.py'),*map(str,args)] if extra is None else extra
        t=time.perf_counter()
        result=subprocess.run(command,input=None,capture_output=True,text=True,env=env,cwd=ROOT)
        (output/(label+'.log')).write_text(result.stdout+result.stderr)
        receipt.append(dict(label=label,command=command,exit_code=result.returncode,wall_seconds=time.perf_counter()-t))
        write(output/'commands.json',receipt)
        if result.returncode:raise RuntimeError(label+' failed; '+result.stderr[-1000:])
        return json.loads(result.stdout) if extra is None else None
    store=output/'reference-sidecar'
    fixture=ROOT/'fixtures/synthetic';real=ROOT/'fixtures/real'
    call('01-plan',['plan','--cue-plan',fixture/'cue-plan.json'])
    for name in ['fin','back']:call('02-session-'+name,['init-session','--store',store,'--session',fixture/(name+'-session.json')])
    call('03-fixed-cues',['watch-events','--events',fixture/'events.jsonl','--cue-plan',fixture/'cue-plan.json','--output',output/'synthetic-cues','--replay'])
    call('04-old-M-events',['watch-events','--events',real/'M-runner-events-subset.jsonl','--cue-plan',real/'M-cue-plan.json','--output',output/'M-cue-replay','--replay'])
    call('05-mark-no-exposure',['mark','--store',store,'--session-id','SYNTH-fin','--record-id','fin-bg','--note','合成演示：先打点；不是曝光时间'])
    times=read(fixture/'point-times.json')
    call('06-late-revision',['record','--store',store,'--session-id','SYNTH-fin','--record-id','fin-bg','--revise',
        '--value','41.0','--unit','C','--measured-at',times['background'],'--uncertainty-s','0','--time-source','synthetic_explicit_timestamp_not_real_measurement'])
    call('07-csv',['import','--store',store,'--file',fixture/'external.csv','--mapping',fixture/'csv-mapping.json'])
    call('08-duplicate-import',['import','--store',store,'--file',fixture/'external.csv','--mapping',fixture/'csv-mapping.json'])
    call('09-json',['import','--store',store,'--file',fixture/'external.json','--mapping',fixture/'json-mapping.json'])
    call('10-compare',['compare','--store',store,'--trajectory',real/'M-frozen.jsonl','--output',output/'synthetic-report'])
    call('11-zero-measurements',['compare','--store',output/'zero-sidecar','--trajectory',real/'M-frozen.jsonl','--output',output/'zero-report'])
    contact=ROOT/'fixtures/contact-synthetic';contact_store=output/'contact-sidecar'
    for name in ['fin','back']:call('ADD1-session-'+name,['init-session','--store',contact_store,'--session',contact/(name+'-session.json')])
    call('ADD1-continuous-import',['import','--store',contact_store,'--file',contact/'generic-continuous.csv','--mapping',contact/'mapping.json'])
    call('ADD1-continuous-duplicate',['import','--store',contact_store,'--file',contact/'generic-continuous.csv','--mapping',contact/'mapping.json'])
    call('ADD1-probe-event',['session-event','--store',contact_store,'--session-id','SYNTH-contact-fin','--type','probe_loose',
        '--measured-at','90','--uncertainty-s','.5','--note','合成松脱示例，不是现场事件；之后须新会话'])
    call('ADD1-continuous-compare',['compare','--store',contact_store,'--trajectory',real/'M-frozen.jsonl','--output',output/'contact-report'])
    call('12-tests',[],[sys.executable,'-m','pytest','-q',str(ROOT/'tests'),'-o','cache_dir='+str(output/'pytest-cache')])
    call('13-readback',[],[sys.executable,str(ROOT/'verify_local.py'),'--run-output',str(output)])
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    write(output/'environment-resources.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        wall_seconds=time.perf_counter()-started,children_user_cpu_s=usage.ru_utime,children_system_cpu_s=usage.ru_stime,
        children_peak_rss_native=usage.ru_maxrss,native_rss_units='bytes on macOS; KiB on Linux',
        device_requests=0,external_software_requests=0,model_fits=0,cuda=False,production_modules_imported=False))
    write(output/'offline-complete.json',dict(status='pass',software_implemented=True,offline_checks=True,
        instrument_profile_confirmed=False,surface_measurement_performed=False,physical_mapping_validated=False,
        model_refit=False,control_authorization='none',all_external_demo_values_synthetic=True,
        default_input_path='numeric_export',user_instrument_selection_confirmed=True,
        real_YET_CSV_mapping_accepted=False,actual_contact_installation_verified=False,
        command_count=len(receipt),source_index_sha256=sha(ROOT/'source-index.json')))
    print(json.dumps(dict(status='pass',output=str(output),commands=len(receipt),workload_started=False),ensure_ascii=False))


if __name__=='__main__':
    # A single entry uses an already available local test runtime; never pip/network.
    if importlib.util.find_spec('pytest') is None:
        candidates=[ROOT.parents[1]/'.venv310/bin/python',Path('/Users/massif/Tianshan-thermal-observer/.venv310/bin/python')]
        for candidate in candidates:
            if candidate.is_file() and subprocess.run([str(candidate),'-c','import pytest'],capture_output=True).returncode==0:
                os.execv(str(candidate.absolute()),[str(candidate.absolute()),str(Path(__file__).absolute()),*sys.argv[1:]])
        raise SystemExit('本地未找到pytest运行时；通用CLI仍可用。重跑检查需已有Python+pytest，不自动联网安装。')
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.output)
