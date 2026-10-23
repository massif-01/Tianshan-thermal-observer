"""New local research evidence only; never Git publication or original-data modification."""
from pathlib import Path
import datetime,difflib,hashlib,json,subprocess,tempfile,zipfile
ROOT=Path(__file__).absolute().parent
TITLE='TTO-YET610L同步短问答-冻结模型比较证据包.zip'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def selected():
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(x in rel.parts for x in ['__pycache__','cache','pytest-cache']):continue
        if p.name=='artifact-SHA256.json' or p.suffix=='.so':continue
        if rel.parts[0] in ['vendor','models','tests','inputs','delivery']:files.append(p)
        elif len(rel.parts)==1 and p.suffix in ['.py','.json','.md','.txt','.log'] and p.name not in ['data.json','stage1-registration.json','replay.log','model-generation.log','compare.log','final-run.log','checked-run.log']:files.append(p)
        elif rel.parts[:2]==('runs','deliverable') and len(rel.parts)>2 and rel.parts[2]!='input':files.append(p)
    return files


def build(target=None):
    patch=ROOT/'delivery/research-code.patch';chunks=[];sources=[]
    for p in selected():
        rel=p.relative_to(ROOT)
        if p.suffix in ['.py','.c'] or p.name in ['README.md','spec.json','requirements.txt']:
            sources.append(p);name='experiments/thermal_yet610l_comparison_v1/'+str(rel)
            chunks.append('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n')
            chunks.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))
    patch.write_text(''.join(chunks))
    check=Path(tempfile.mkdtemp(prefix='tto-yet-patch-check-'))
    c=subprocess.run(['git','apply','--check',str(patch.absolute())],cwd=check,capture_output=True,text=True);assert c.returncode==0,c.stderr
    (ROOT/'delivery/patch-check.json').write_text(json.dumps(dict(status='pass',new_paths=len(sources),scope='new independent research directory only',patch_sha256=digest(patch)),ensure_ascii=False,indent=2)+'\n')
    files=selected();manifest={'contract':'TTO-YET-FROZEN-COMPARE-v1.0-evidence','built_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'files':{'thermal_yet610l_comparison_v1/'+str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=digest(p)) for p in files},
       'important':'CSV is real; all three model-state counts and valid model/surface comparison counts are zero under native rules, not a model victory.'}
    target=Path(target) if target else ROOT/'delivery'/TITLE
    # Delivery ZIP is not a member of itself or an earlier build.
    manifest['files']={n:e for n,e in manifest['files'].items() if not n.endswith('.zip') or '/inputs/' in n}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in files:
            name='thermal_yet610l_comparison_v1/'+str(p.relative_to(ROOT))
            if name in manifest['files']:z.write(p,name)
        z.writestr('SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for n,e in manifest['files'].items():
            b=z.read(n);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'],n
    receipt=dict(archive=target.name,bytes=target.stat().st_size,sha256=digest(target),CRC='pass',members=len(manifest['files']),
        report_sha256=digest(ROOT/'delivery/TTO-YET610L同步短问答-冻结模型比较报告.md'),
        input_archive_sha256=digest(ROOT/'inputs/本轮完整原始证据.zip'),
        runtime_source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources})
    (ROOT/'artifact-SHA256.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='runtime_source_sha256'},ensure_ascii=False))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();build(a.output)
