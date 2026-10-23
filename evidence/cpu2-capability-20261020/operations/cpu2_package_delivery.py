from pathlib import Path
import json,hashlib,zipfile,shutil,datetime
ROOT=Path('/Users/massif/Tianshan-thermal-observer');E=ROOT/'evidence/cpu2-capability-20261020';D=ROOT/'deliverables';stage=E/'delivery';stage.mkdir(exist_ok=True)
report=D/'TTO-cpu.2-首次60秒能力核对报告.md';card=D/'TTO-cpu.2-能力核对后操作卡.md'
entries={}
def add(f,n):
 f=Path(f);assert f.is_file();assert n not in entries,n;entries[n]=f
for f in [report,card]:add(f,f.name)
# Raw same-run evidence and preparations; no duplicate wheelhouses, transport tars or historical synthetic trees.
for part in ['field','remote-result','operations']:
 for f in sorted((E/part).rglob('*')):
  if f.is_file() and f.suffix!='.tar':add(f,'evidence/'+str(f.relative_to(E)))
for n in ['authorization.json','authorization-supplement.json','offline-identity-check.json','connection-blocker.json']:
 add(E/'preparation'/n,'preparation/'+n)
for n in ['README.md','01-独立复审报告.md','02-给实际安装与测试的指令.md','03-给模型线的并行说明.md','SHA256.json']:
 add(E/'preparation/review-input'/n,'review-input/'+n)
add(E/'preparation/wheelhouse/SHA256.json','candidate/wheelhouse-SHA256.json')
for n in ['tto_field_candidate-0.2.4+cpu.2-py3-none-any.whl','install_candidate.py','dependency-reference.json']:
 add(ROOT/'evidence/cpu-pilot-closeout-20261020/candidate'/n,'candidate/'+n)
# The owner hands off only this round's focused modeling delivery, not recursive old history.
model=D/'TTO-cpu.2首次60秒能力记录-模型线判读'
if not model.exists():raise SystemExit('model handoff not yet available; do not finalize')
for f in sorted(model.iterdir()):
 if f.is_file():add(f,'model-line/'+f.name)
rep=D/'TTO-CPU联合回执来源标签-报告器修订'
for f in sorted(rep.iterdir()):
 if f.is_file() and f.suffix in ('.md','.json','.zip','.log','.txt'):add(f,'reporter-revision/'+f.name)
index={name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for name,f in entries.items()}
manifest=stage/'SHA256.json';manifest.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
zipout=D/'TTO-cpu.2-首次60秒能力核对证据包.zip'
with zipfile.ZipFile(zipout,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,f in entries.items():z.write(f,name)
 z.write(manifest,'SHA256.json')
with zipfile.ZipFile(zipout) as z:
 assert z.testzip() is None
 for n,v in index.items():
  b=z.read(n);assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
receipt={'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'zip':str(zipout),'bytes':zipout.stat().st_size,'sha256':hashlib.sha256(zipout.read_bytes()).hexdigest(),'indexed_files':len(index),'crc_and_all_sha_passed':True,'native_uuid':'80938521-b659-4160-a7b2-5fdfb6ebc197','capability_qualified':False,'inference_requests':0,'repeat_runs':0,'large_archives_reference_only':True}
(D/'TTO-cpu.2-首次60秒能力核对-交付核验.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))
