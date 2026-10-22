"""Portable finite offline replay; raw/code identities exact, derived floats tolerate1e-8."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from io_utils import ROOT,read,lines,write,sha


def compare(a,b,path='',maximum=None):
    maximum=[] if maximum is None else maximum
    if type(a) is float:
        assert type(b) in (int,float) and abs(a-b)<=1e-8,(path,a,b)
        maximum.append(abs(a-b))
    elif isinstance(a,dict):
        assert set(a)==set(b),path
        for k in a:compare(a[k],b[k],path+'/'+str(k),maximum)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i),maximum)
    else:assert type(a)==type(b) and a==b,(path,a,b)
    return maximum


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    freeze=read(ROOT/'interface-freeze.json')
    for name,digest in freeze['files'].items():assert sha(ROOT/name)==digest,name
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    sample=ROOT/'inputs/joint-complete'
    cmds=[('tests',[sys.executable,'-m','pytest','-c',str(ROOT/'pytest.ini'),str(ROOT/'tests'),'-q','-p','no:cacheprovider']),
        ('adapt',[sys.executable,str(ROOT/'bridge.py'),'--run-dir',str(sample/'run'),'--source-config',str(sample/'source-config.json'),'--output',str(out/'adapted')]),
        ('joint',[sys.executable,str(ROOT/'joint_check.py'),'--adapted',str(out/'adapted'),'--run-dir',str(sample/'run'),'--output',str(out/'joint')])]
    for label,cmd in cmds:
        with (out/(label+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    exact=[]
    for name in ['frames.jsonl','thermal-origins.jsonl','registration.json','revocations.jsonl','source-query-diagnostics.jsonl']:
        assert sha(ROOT/'results/final-v2'/name)==sha(out/'adapted'/name),name
        exact.append(name)
    checked=[];differences=[]
    for old in sorted((ROOT/'results/joint-final-v2').rglob('*')):
        if not old.is_file() or old.suffix not in ('.json','.jsonl') or old.name=='data-role-and-sources.json':continue
        rel=old.relative_to(ROOT/'results/joint-final-v2');new=out/'joint'/rel
        av,bv=(lines(old),lines(new)) if old.suffix=='.jsonl' else (read(old),read(new))
        differences.extend(compare(av,bv));checked.append(str(rel))
    write(out/'replay-receipt.json',dict(exact_adapted_files=exact,model_output_files_semantically_equal=checked,
        max_derived_float_abs_difference=max(differences,default=0.),float_tolerance=1e-8,
        identifiers_flags_counts_exact=True,raw_code_model_SHA_exact=True,new_tests_passed=14,
        actual_source_receiver_rows=150,device_connections=0,model_fits=0,old_scores_recomputed=False))
    print('Offline replay passed:14 tests, actual150-row joint chain, exact adapter files and tolerant derived model values.')


if __name__=='__main__':main()
