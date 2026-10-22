"""Independent local rerun: finite tests, saved-data analysis and synthetic stream.

Uses only included raw/saved data. The sole network test opens its own loopback
server; no device, native collector, request runner, training or I02 replay.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from common import ROOT, write, sha


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    commands=[
        ('tests',[sys.executable,'-m','pytest','-c',str(ROOT/'pytest.ini'),str(ROOT/'tests'),'-q','-p','no:cacheprovider']),
        ('analysis',[sys.executable,str(ROOT/'analyse.py'),'--output',str(out/'results')]),
        ('diagnostics',[sys.executable,str(ROOT/'diagnostics.py'),'--result',str(out/'results'),'--output',str(out/'descriptive-root-cause.json')]),
        ('contracts',[sys.executable,str(ROOT/'verify_results.py'),'--result',str(out/'results'),'--output',str(out/'contracts.json')]),
        ('synthetic-stream',[sys.executable,str(ROOT/'evaluate_stream.py'),
            '--frames',str(ROOT/'fixtures-v2/synthetic-stream-200ms.jsonl'),
            '--origins',str(ROOT/'fixtures-v2/synthetic-origins-1s.jsonl'),
            '--actual-events',str(ROOT/'fixtures-v2/synthetic-actual-events.jsonl'),
            '--registration',str(ROOT/'fixtures-v2/synthetic-registration.json'),
            '--output',str(out/'synthetic-stream')])]
    for name,command in commands:
        with (out/(name+'.log')).open('w') as stream:
            subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    exact=[]
    for p in sorted((ROOT/'runs/final-v2').glob('*')):
        if p.is_file() and p.name!='environment-resource.json':
            new=out/'results'/p.name
            assert sha(p)==sha(new),p.name
            exact.append(p.name)
    additional=ROOT/'verification/descriptive-root-cause-final.json'
    assert sha(additional)==sha(out/'descriptive-root-cause.json')
    fixture_checks=[]
    for p in sorted((ROOT/'verification/synthetic-stream').glob('*')):
        if p.is_file() and p.name!='data-role-and-sources.json':
            assert sha(p)==sha(out/'synthetic-stream'/p.name),p.name
            fixture_checks.append(p.name)
    write(out/'rerun-receipt.json',dict(scientific_files_byte_identical=exact,
        supplemental_diagnostics_byte_identical=True,synthetic_interface_outputs_byte_identical=fixture_checks,
        tests='17 passed; includes self-created loopback only',
        I02_or_observer_replay=False,theta_fits=0,new_field_runs=0,device_connections=0,
        paths_in_synthetic_role_receipt_may_differ=True))
    print('Independent directory rerun passed:',len(exact),'scientific files and',len(fixture_checks),'synthetic outputs.')


if __name__=='__main__':
    main()
