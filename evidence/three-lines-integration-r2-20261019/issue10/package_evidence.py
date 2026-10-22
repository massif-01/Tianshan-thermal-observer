"""Create a private offline review archive. No GitHub upload, install or device access."""
import argparse,datetime,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def selected():
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or '__pycache__' in f.parts:continue
        rel=f.relative_to(ROOT)
        if rel.parts[0]=='results' and (len(rel.parts)<2 or rel.parts[1]!='delivery-r2'):continue
        if rel.name in ('SHA256.json','delivery-receipt.json') and len(rel.parts)==1:continue
        yield f

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);args=p.parse_args()
    files=list(selected());manifest={'contract':'TTO-REVIEW-R2-20261018-Issue10','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'private offline preparation; not field authorization','files':{str(f.relative_to(ROOT)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files}}
    m=ROOT/'SHA256.json';m.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(args.archive,'x',zipfile.ZIP_DEFLATED) as z:
        for f in files+[m]:z.write(f,str(f.relative_to(ROOT)))
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        for name,v in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==v['sha256'],name
    receipt={'archive':str(args.archive.resolve()),'bytes':args.archive.stat().st_size,'sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),
             'indexed_files_verified':len(files),'zip_crc':'passed','role':'private review; no software commit/push/PR or deployment'}
    (ROOT/'delivery-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
