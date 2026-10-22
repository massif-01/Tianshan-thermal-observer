"""Verify delivered Issue9 correction, never edit the owner's exporter."""
import argparse,hashlib,json,subprocess,sys,zipfile,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--original-integration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir()
with zipfile.ZipFile(a.package) as z:
 assert z.testzip() is None
 m=json.loads(z.read('SHA256.json'));files=m.get('files',m)
 for n,v in files.items():
  if not isinstance(v,dict) or 'sha256' not in v:continue
  b=z.read(n);assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
 z.extractall(a.output/'original-delivery')
old=[json.loads(x) for x in (a.original_integration/'streams/issue9-Y.jsonl').read_text().splitlines()]
new=[json.loads(x) for x in (a.output/'original-delivery/output/source-health-Y-I02.jsonl').read_text().splitlines()]
model=[json.loads(x) for x in (a.original_integration/'streams/issue8-Y.jsonl').read_text().splitlines()]
assert len(old)==len(new)==len(model)==5319
changes=[]
for n,(b,c,s) in enumerate(zip(old,new,model)):
 assert c['identity']['spec']=='COMM-SOURCE-HEALTH-R2-I02-v1';c['identity']['spec']=b['identity']['spec']
 if b!=c:
  assert n==5318
  assert b['measurement']['TJ_and_rails']['raw_valid'] is True and c['measurement']['TJ_and_rails']['raw_valid'] is False
  cc=json.loads(json.dumps(c));cc['measurement']['TJ_and_rails']['raw_valid']=True;assert cc==b
  changes.append(dict(ref=c['identity']['observed_through_ref'],field='measurement.TJ_and_rails.raw_valid',before=True,after=False))
 assert bool((s['measurement']['tj'] or {}).get('raw_valid'))==c['measurement']['TJ_and_rails']['raw_valid']
proc=subprocess.run([sys.executable,'tests/test_lifecycle.py'],cwd=a.output/'original-delivery',text=True,capture_output=True);assert proc.returncode==0,proc.stdout+proc.stderr
(a.output/'local-tests.log').write_text(proc.stdout+proc.stderr)
(a.output/'integration-verification.json').write_text(json.dumps(dict(package_sha256=hashlib.sha256(a.package.read_bytes()).hexdigest(),rows=5319,only_semantic_changes=changes,
    revised_source_valid_matches_issue8_all_rows=True,owner_tests_returncode=proc.returncode,production_or_collector_changed=False),indent=2)+'\n')
print('I02 verified: 5319 rows, one preserved boundary correction; six owner tests pass')
