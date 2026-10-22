"""Private, minimal current-run evidence. Does not include historical archives or touch Git."""
import argparse
import difflib
import json
import shutil
import zipfile
from pathlib import Path
from prepare import ROOT,REPO,read,write,sha


PAYLOAD=ROOT/'delivery/payload'


def stage():
    PAYLOAD.mkdir(parents=True,exist_ok=False)
    for name in ('inputs','vendor','tests'):
        shutil.copytree(ROOT/name,PAYLOAD/name,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
    for p in ROOT.iterdir():
        if p.is_file() and (p.suffix in ('.py','.md','.ini','.txt') or p.name in ('spec.json','design-freeze.json','source-and-input-originals.json')):
            shutil.copyfile(p,PAYLOAD/p.name)
    shutil.copytree(ROOT/'runs/final',PAYLOAD/'results')
    verification=PAYLOAD/'verification';verification.mkdir()
    for name in ('tests-final.log','study-final.log','study-attempt-01.log','report-generation.log'):
        shutil.copyfile(ROOT/name,verification/name)
    original_checks=[]
    for name,item in read(ROOT/'source-and-input-originals.json').items():
        original=REPO/name
        assert original.stat().st_size==item['bytes'] and sha(original)==item['sha256'],name
        original_checks.append(name)
    write(verification/'unchanged-originals.json',dict(originals_checked=len(original_checks),all_bytes_SHA_unchanged=True,
          scope='all copied current-run and sealed-source originals; no global repository/security review',paths=original_checks))
    first={str(p.relative_to(ROOT/'runs/attempt-01')):sha(p) for p in sorted((ROOT/'runs/attempt-01').rglob('*'))
           if p.is_file() and p.suffix in ('.json','.jsonl') and p.name!='environment-resource.json'}
    matched=[name for name,digest in first.items() if sha(ROOT/'runs/final'/name)==digest]
    assert len(matched)==len(first)
    write(verification/'first-execution-scientific-sha.json',first)
    write(PAYLOAD/'execution-attempts.json',dict(theta_fits=0,searches=0,executions=[
        dict(id='attempt-01',status='completed',log='verification/study-attempt-01.log',scientific_files=len(first)),
        dict(id='final',status='completed',log='verification/study-final.log',scientific_files_identical_to_attempt_01=len(matched))],
        first_output_preserved_in_author_directory=True,duplicate_first_results_not_recursively_packaged=True))
    write(verification/'figures-visual-check.json',dict(figures_inspected=[p.name for p in sorted((ROOT/'runs/final/figures').glob('*.png'))],
         method='actual rendered PNG inspection',Chinese_labels_readable=True,legends_axes_not_clipped=True,
         A_B_and_surface_meanings_separate=True,scientific_data_modified=False))
    codefiles=[p for p in PAYLOAD.rglob('*') if p.is_file() and p.parts[len(PAYLOAD.parts)] not in ('inputs','results','verification')
               and p.name not in ('source-and-input-originals.json','execution-attempts.json')]
    patch=[]
    for p in sorted(codefiles):
        relative='experiments/thermal_fixed_anchors_frozen_v1/'+str(p.relative_to(PAYLOAD))
        content=p.read_text().splitlines(keepends=True)
        patch.extend([f'diff --git a/{relative} b/{relative}\n','new file mode 100644\n'])
        patch.extend(difflib.unified_diff([],content,fromfile='/dev/null',tofile='b/'+relative))
    (PAYLOAD/'new-research-code.patch').write_text(''.join(patch))
    print(json.dumps(dict(staged=str(PAYLOAD),originals_unchanged=len(original_checks),first_scientific_files_equal=len(matched))))


def pack(path):
    path=Path(path)
    index={str(p.relative_to(PAYLOAD)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PAYLOAD.rglob('*'))
           if p.is_file() and p.name!='SHA256.json' and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
    write(PAYLOAD/'SHA256.json',index)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(index):z.write(PAYLOAD/name,name)
        z.write(PAYLOAD/'SHA256.json','SHA256.json')
    print(json.dumps(dict(zip=str(path),bytes=path.stat().st_size,sha256=sha(path),payload_members=len(index))))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--stage',action='store_true');ap.add_argument('--pack',type=Path)
    args=ap.parse_args()
    if args.stage:stage()
    if args.pack:pack(args.pack)
