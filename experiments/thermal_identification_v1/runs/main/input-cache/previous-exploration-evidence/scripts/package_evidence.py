"""Package new analysis with exact hashes; do not modify original archives or source projects."""
import hashlib
import json
import zipfile
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]


def main():
    omitted={
        'model-exploration/short-qa/all-origins-dataset.json':'model-exploration/short-qa/exploratory-split/dataset.json',
        'model-exploration/seven-conditions/exploratory-split/dataset.json':'model-exploration/seven-conditions/all-origins-dataset.json'}
    receipt=[]
    for old,kept in omitted.items():
        a,b=(OUT/old).read_bytes(),(OUT/kept).read_bytes()
        assert a==b,(old,kept)
        receipt.append(dict(omitted=old,kept=kept,bytes=len(a),sha256=hashlib.sha256(a).hexdigest(),byte_identical=True))
    (OUT/'results/packaging-deduplication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    skip=set(omitted)|{'SHA256.json'}
    # Full status snapshots may mention unrelated files; their SHA summaries are included instead.
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and str(p.relative_to(OUT)) not in skip
           and p.suffix!='.bin' and '__pycache__' not in p.parts]
    hashes={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
    (OUT/'SHA256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    archive=ROOT/'deliverables/TTO-短问答后续核对证据包.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files+[OUT/'SHA256.json']:z.write(p,str(p.relative_to(OUT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,h in hashes.items():
            b=z.read(name)
            assert len(b)==h['bytes'] and hashlib.sha256(b).hexdigest()==h['sha256']
    r=dict(name=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
           member_checks=len(hashes),crc='passed',sha='passed',report=str((OUT/'TTO-短问答后续核对与有限优化方案.md').relative_to(ROOT)),
           original_archives=json.loads((OUT/'results/original-archive-verification.json').read_text()),
           complement=json.loads((OUT/'results/complement-verification.json').read_text()))
    (ROOT/'deliverables/TTO-短问答后续核对交付清单.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['name','bytes','sha256','member_checks','crc','sha']},ensure_ascii=False))


if __name__=='__main__':main()
