from pathlib import Path
import hashlib,json,zipfile
S=Path('/private/tmp/tto-cpu2-closeout-delivery-20261020');R=Path('/Users/massif/Tianshan-thermal-observer');out=R/'deliverables/TTO-CPU旁录与分析衔接-收尾证据包.zip'
files={str(p.relative_to(S)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(S.rglob('*')) if p.is_file() and p!=S/'SHA256.json'}
(S/'SHA256.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(S.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(S)))
receipt=dict(zip=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),members=len(files),candidate_version='0.2.4+cpu.2',adapter_version='cpu-arrival-bridge-1.0.0',field_actions=False,new_12_requests=False,target310_install_pass=None)
(R/'evidence/cpu-pilot-closeout-20261020/archive-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))
