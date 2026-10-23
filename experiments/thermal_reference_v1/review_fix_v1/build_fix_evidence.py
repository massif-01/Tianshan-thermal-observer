"""Build a fresh full minimal replay bundle; never overwrite the accepted evidence ZIP."""
from pathlib import Path
import datetime,hashlib,json,zipfile
ROOT=Path(__file__).absolute().parent.parent
FIX=ROOT/'review_fix_v1'
TITLE='TTO-连续测温工具-审查修正证据包.zip'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    target=FIX/TITLE
    groups={'refprep','tests','templates','schemas','frozen','fixtures','maintenance','handoff','freeze-history'}
    chosen=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        if any(p in rel.parts for p in ['__pycache__','.pytest_cache','pytest-cache','plot-cache']):continue
        if path.suffix=='.zip' or path.name=='repair-artifact-SHA256.json':continue
        include=False
        if len(rel.parts)==1 and path.suffix in ['.py','.json','.md']:include=True
        if rel.parts[0] in groups:include=True
        if rel.parts[0]=='review_fix_v1':include=True
        if rel.parts[:2]==('results','release-check') and path.name in ['comparison.json','paired-points.jsonl']:include=True
        if include:chosen.append(path)
    entries={'thermal_reference_v1/'+str(p.relative_to(ROOT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in chosen}
    manifest=dict(contract='TTO-REF-PREP-v1.0+ADD1-review-fix',files=entries,built_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        base_accepted_archive_sha256='f32ccb4c3a70d9005a74c66c2f0b736f5362c9e6ebe85d64f9e912feaef48b1c',
        real_new_measurement=False,no_model_refit=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in chosen:z.write(p,'thermal_reference_v1/'+str(p.relative_to(ROOT)))
        z.writestr('thermal_reference_v1/SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for name,e in entries.items():
            data=z.read(name);assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
    receipt=dict(archive=target.name,sha256=digest(target),bytes=target.stat().st_size,members=len(entries),CRC='pass',
        report_sha256=digest(FIX/'TTO-连续测温工具-审查修正报告.md'),manifest_all_members='pass',
        old_accepted_archive_unchanged=digest(ROOT/'TTO-测温记录准备与路线图同步-证据包.zip')=='f32ccb4c3a70d9005a74c66c2f0b736f5362c9e6ebe85d64f9e912feaef48b1c')
    (FIX/'repair-artifact-SHA256.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':build()
