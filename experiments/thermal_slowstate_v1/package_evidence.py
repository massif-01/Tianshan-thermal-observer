"""New research-only patch and evidence archive. No Git mutations or recursive input ZIPs."""
from pathlib import Path
import difflib
import hashlib
import json
import zipfile
from prepare import read,write,digest

ROOT=Path(__file__).absolute().parent
TITLE='TTO-快慢热状态与平稳散热需求-研究证据包.zip'
EXCLUDED_NAMES={TITLE,'SHA256.json','archive-sha256.json','package-check.json','standalone-replay-check.json'}
EXCLUDED_DIRS={'__pycache__','.pytest_cache','build'}


def included(path):
    rel=path.relative_to(ROOT)
    return (path.is_file() and not any(x in EXCLUDED_DIRS for x in rel.parts) and
            path.name not in EXCLUDED_NAMES and path.suffix not in ['.zip','.pyc','.so'] and
            path.name!='.DS_Store')


def main():
    assert read(ROOT/'readback-checks.json')['status']=='pass'
    # A patch only for added executable research files and local documents, never old dirty diffs.
    patch=[]
    code_files=[p for p in ROOT.rglob('*') if included(p) and p.suffix in ['.py','.c','.md'] and
                p.relative_to(ROOT).parts[0] not in ['handoff','sources']]
    for path in sorted(code_files):
        name='experiments/thermal_slowstate_v1/'+str(path.relative_to(ROOT))
        patch+= [f'diff --git a/{name} b/{name}\n','new file mode 100644\n']
        patch+=list(difflib.unified_diff([],path.read_text().splitlines(keepends=True),
                                       fromfile='/dev/null',tofile='b/'+name))
    (ROOT/'code.patch').write_text(''.join(patch))
    paths=sorted(p for p in ROOT.rglob('*') if included(p))
    files={str(p.relative_to(ROOT)):dict(sha256=digest(p.read_bytes()),bytes=p.stat().st_size) for p in paths}
    write(ROOT/'SHA256.json',dict(schema='TTO-SLOWSTATE-ARTIFACT-SHA256-v1',files=files,
        self_excluded='SHA256.json',input_archives='indexed only; not recursively bundled'))
    archive=ROOT/TITLE
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in paths+[ROOT/'SHA256.json']:
            z.write(path,str(path.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        stored=json.loads(z.read('SHA256.json'))['files']
        for member,info in stored.items():
            assert digest(z.read(member))==info['sha256'],member
        assert not any(n.endswith('.zip') for n in z.namelist())
    write(ROOT/'archive-sha256.json',dict(file=TITLE,bytes=archive.stat().st_size,sha256=digest(archive.read_bytes())))
    write(ROOT/'package-check.json',dict(status='pass',CRC='pass',all_member_SHA256='pass',members=len(paths)+1,
        recursive_input_archives=False,code_patch_added_files=len(code_files),old_files_modified=0,
        input_archives_indexed=read(ROOT/'stage1-freeze.json')['original_archive_sha256']))
    print(json.dumps(read(ROOT/'archive-sha256.json'),ensure_ascii=False))


if __name__=='__main__':main()
