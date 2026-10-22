"""Package only this new research tree; preserve original sources/worktree."""
import argparse
import difflib
from pathlib import Path
import shutil
import zipfile
from common import ROOT, read, write, sha


def patch():
    paths=[p for p in ROOT.glob('*') if p.is_file() and p.suffix=='.py']
    paths += [ROOT/n for n in ['analysis-spec.json','candidate.json','freeze.json','interface-contract.json','interface-freeze.json','requirements.txt','pytest.ini','README.md','变更与尝试记录.md']]
    paths += [p for d in ['tests','fixtures-v2'] for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    parts=[]
    for p in sorted(paths):
        name='experiments/thermal_cpu_increment_v1/'+str(p.relative_to(ROOT))
        parts.append(f'diff --git a/{name} b/{name}\nnew file mode 100644\n')
        parts.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))
    (ROOT/'research.patch').write_text(''.join(parts))


def stage(destination):
    destination.mkdir(parents=True,exist_ok=False)
    names=[p.name for p in ROOT.iterdir() if p.is_file() and p.name not in ['SHA256.json']]
    names += ['inputs','handoff','fixtures-v2','tests','verification','figures-v2']
    for name in names:
        src,dst=ROOT/name,destination/name
        if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
        else:shutil.copyfile(src,dst)
    dst=destination/'runs/final-v2';dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'runs/final-v2',dst)
    # Retain exact inventories for previous mechanical executions without nesting
    # several copies of identical raw/derived tables in the handoff.
    history={}
    for name in ('attempt-01','final'):
        history[name]=[dict(path=str(p.relative_to(ROOT/'runs'/name)),bytes=p.stat().st_size,sha256=sha(p))
            for p in sorted((ROOT/'runs'/name).rglob('*')) if p.is_file()]
    write(destination/'verification/intermediate-result-inventories.json',history)
    entries=[dict(path=str(p.relative_to(destination)),bytes=p.stat().st_size,sha256=sha(p))
             for p in sorted(destination.rglob('*')) if p.is_file()]
    write(destination/'SHA256.json',dict(schema='TTO-CPU-INCREMENT-EVIDENCE-v1',files=entries,
        theta_fits=0,new_field_runs=0,deployable=False))


def archive(stage_root,destination):
    if destination.exists():raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted(stage_root.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(stage_root)))
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
        manifest=read(stage_root/'SHA256.json')
        import hashlib
        for e in manifest['files']:
            b=z.read(e['path'])
            assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
    return dict(path=str(destination),bytes=destination.stat().st_size,sha256=sha(destination),
        indexed_payload_files=len(manifest['files']),CRC_and_all_member_SHA_passed=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',type=Path,required=True)
    ap.add_argument('--zip',type=Path)
    a=ap.parse_args();patch();stage(a.stage.resolve())
    if a.zip:print(archive(a.stage.resolve(),a.zip.resolve()))
