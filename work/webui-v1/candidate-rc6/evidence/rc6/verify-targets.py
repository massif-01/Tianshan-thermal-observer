"""Offline evidence from an installed wheel; mutations touch disposable copies only.

Run: .venv/bin/python evidence/rc6/verify-targets.py /path/to/prefix/current/env/bin/python /path/to/test-only-deps
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PYTHON=Path(sys.argv[1]).absolute()
QA_SITE=Path(sys.argv[2]).absolute()
ENV=dict(os.environ,TTO_WEB_TEST_INSTALLED='1',PYTHONPATH=str(QA_SITE),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')

def run(code,env=ENV):
    return subprocess.check_output([str(PYTHON),'-c',code],env=env,cwd=ROOT,text=True)

identity=json.loads(run('import json,sys,tto_web,tto_web.state,tto,tto_field;'
    'from tto_web.identity import verify;'
    'print(json.dumps(dict(python=sys.executable,module=tto_web.__file__,state=tto_web.state.__file__,tto=tto.__file__,tto_field=tto_field.__file__,identity=verify())))'))
assert identity['identity']['version']=='1.0.0rc6'
site=Path(identity['module']).parents[1]
for name in ('module','state','tto','tto_field'):assert Path(identity[name]).is_relative_to(site)
assert site.resolve().is_relative_to(PYTHON.parent.parent.resolve())
(OUT/'installed-identity.json').write_text(json.dumps(identity,indent=2)+'\n')

mutations=(
    ('barrier',"        if t<=self.model_gap_t:\n            return\n",'',
     'test_disconnect_advances_barrier_beyond_coalesced_expiry_gap','assert list(s.model_history)==before'),
    ('posterior',"(tj['value'],o['Tf_C'],o['Ts_C'],o['E_C'])",
     "(tj['value'],tj['value'],o['Ts_C'],o['E_C'])",
     'test_real_observer_history_is_posterior_of_same_tj','assert tf!=tj'),
)
results=[]
canonical=Path(identity['state']).read_bytes()
for name,old,new,test,assertion in mutations:
    with tempfile.TemporaryDirectory(prefix='tto-rc6-mutant-',dir='/private/tmp') as temp:
        temp=Path(temp)
        shutil.copytree(site/'tto_web',temp/'tto_web',ignore=shutil.ignore_patterns('__pycache__'))
        target=temp/'tto_web/state.py';source=target.read_text();assert source.count(old)==1
        target.write_text(source.replace(old,new))
        env=dict(ENV,PYTHONPATH=os.pathsep.join(map(str,(temp,site,QA_SITE))))
        loaded=run('import tto_web.state; print(tto_web.state.__file__)',env).strip()
        assert Path(loaded)==target
        completed=subprocess.run([str(PYTHON),'-m','pytest','-p','pytest_asyncio.plugin','-q','tests/test_model_history.py::'+test],env=env,cwd=ROOT,capture_output=True,text=True)
        output=completed.stdout+completed.stderr
        (OUT/f'mutation-{name}.log').write_text(output)
        assert completed.returncode==1 and assertion in output and '1 failed' in output,output
        results.append(dict(mutation=name,test=test,returncode=completed.returncode,
            loaded_module=loaded,expected_assertion=assertion,
            original_sha256=hashlib.sha256(canonical).hexdigest(),
            mutant_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            removed=old,replacement=new,isolated_copy=True))
assert Path(identity['state']).read_bytes()==canonical
(OUT/'mutation-results.json').write_text(json.dumps(results,indent=2)+'\n')

# Schema evidence is produced by the installed rc6 schema and actual sealed rc5 fixture.
schema_code="""
import copy,json,sys
from pathlib import Path
import jsonschema,tto_web
root=Path(tto_web.__file__).parent/'contracts'
new=json.loads((root/'series.schema.json').read_text())
old=json.loads(Path('tests/fixtures/series-rc5.schema.json').read_text())
example=json.loads((root/'series-example-tracking.json').read_text())
records=[]
for case in ('joint_tj_kind','joint_tj_stage','numeric_sample_id'):
    invalid=copy.deepcopy(example)
    if case=='joint_tj_kind':invalid['series'][0]['kind']='estimate'
    elif case=='joint_tj_stage':invalid['series'][0]['estimate_stage']='posterior'
    else:invalid['series'][1]['points'][-1]['sample_id']=None
    jsonschema.validate(invalid,old)
    errors=list(jsonschema.Draft202012Validator(new).iter_errors(invalid))
    assert errors
    records.append(dict(case=case,rc5='accepted',rc6='rejected',errors=[dict(path=list(e.absolute_path),message=e.message) for e in errors]))
examples=[]
for p in sorted(root.glob('series-example-*.json')):
    jsonschema.validate(json.loads(p.read_text()),new);examples.append(p.name)
print(json.dumps(dict(counterexamples=records,normal_examples_passed=examples)))
"""
(OUT/'schema-results.json').write_text(json.dumps(json.loads(run(schema_code)),indent=2)+'\n')
print(json.dumps(dict(identity=identity,mutations=results,schemas='three rc5 accepts / rc6 rejects; three normal examples pass')))
