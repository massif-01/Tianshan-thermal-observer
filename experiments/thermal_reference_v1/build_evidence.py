"""Local delivery only: selected research files, code patch, member SHA, CRC. No publishing."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import subprocess
import tempfile
import zipfile
from refprep.files import read,write,sha,now_utc

ROOT=Path(__file__).absolute().parent
TITLE='TTO-测温记录准备与路线图同步-证据包.zip'


def selected():
    result=[]
    root_suffix={'.py','.json','.md','.log','.txt'}
    trees={'refprep','tests','templates','schemas','frozen','fixtures','maintenance','handoff','freeze-history','publication','delivery'}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        if any(x in rel.parts for x in ['__pycache__','.pytest_cache','pytest-cache','plot-cache']):continue
        if len(rel.parts)==1:
            if path.suffix in root_suffix and path.name not in ['delivery-SHA256.json'] and not path.name.startswith(('offline-attempt','offline-final','offline-v2','offline-add1','tests-attempt','prepare-sources')):result.append(path)
        elif rel.parts[0] in trees:result.append(path)
        elif rel.parts[:2]==('results','release-check'):result.append(path)
    return result


def code_patch():
    candidates=[]
    for path in selected():
        rel=path.relative_to(ROOT)
        if rel.parts[0] in ['refprep','tests','templates','schemas','maintenance'] or (
            len(rel.parts)==1 and (path.suffix=='.py' or path.name in ['README.md','一页操作卡.md','连续测温版操作卡.md','prep-spec.json','prep-add1-spec.json','stage1-freeze.json','stage-add1-freeze.json'])):
            candidates.append(path)
    chunks=[]
    for path in candidates:
        name='experiments/thermal_reference_v1/'+str(path.relative_to(ROOT))
        chunks.append('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n')
        chunks.extend(difflib.unified_diff([],path.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))
    dest=ROOT/'delivery/research-code.patch';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(''.join(chunks))
    check=Path(tempfile.mkdtemp(prefix='tto-reference-patch-check-'))
    result=subprocess.run(['git','apply','--check',str(dest)],cwd=check,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    write(ROOT/'delivery/patch-check.json',dict(status='pass',method='git apply --check in an empty temporary directory',
        files=len(candidates),patch_sha256=sha(dest),temporary_directory=str(check),publication_patch='publication/docs-only.patch separate'))


def build(output):
    code_patch()
    paths=selected();payload={}
    for path in paths:
        name='thermal_reference_v1/'+str(path.relative_to(ROOT));payload[name]=dict(sha256=sha(path),bytes=path.stat().st_size)
    manifest=dict(contract='TTO-REF-PREP-v1.0+ADD1-evidence',built_at_utc=now_utc(),files=payload,
        note='Manifest excludes itself; outer ZIP SHA is delivered separately. No new external real temperature; no model refit.')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for path in paths:archive.write(path,'thermal_reference_v1/'+str(path.relative_to(ROOT)))
        archive.writestr('thermal_reference_v1/SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    from verify_archive import verify
    result=verify(output)
    write(ROOT/'delivery-SHA256.json',dict(archive=Path(output).name,sha256=sha(output),bytes=Path(output).stat().st_size,
        report_sha256=sha(ROOT/'TTO-测温记录准备与路线图同步-实施报告.md'),CRC=result['CRC'],members=result['members'],written_at_utc=now_utc()))
    print(json.dumps(read(ROOT/'delivery-SHA256.json'),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/TITLE)
    a=p.parse_args();build(a.output)
