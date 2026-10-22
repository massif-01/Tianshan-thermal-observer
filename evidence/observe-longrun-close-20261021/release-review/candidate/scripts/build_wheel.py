"""Deterministic pure-Python wheel from sealed source, stdlib only, no downloads."""
from pathlib import Path
import base64,csv,hashlib,io,zipfile,tomllib
root=Path(__file__).resolve().parents[1];meta=tomllib.loads((root/'pyproject.toml').read_text())['project']
version=meta['version'];dist='tto_field_candidate';info=f'{dist}-{version}.dist-info'
items={str(p.relative_to(root/'src')):p.read_bytes() for p in sorted((root/'src').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json')}
items[info+'/METADATA']=('\n'.join(['Metadata-Version: 2.1','Name: '+meta['name'],'Version: '+version,'Summary: '+meta['description'],'Requires-Python: '+meta['requires-python']]+['Requires-Dist: '+x for x in meta['dependencies']])+'\n\n').encode()
items[info+'/WHEEL']=b'Wheel-Version: 1.0\nGenerator: tto-offline-sealed-wheel-v1\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
items[info+'/entry_points.txt']=('[console_scripts]\n'+''.join(k+' = '+v+'\n' for k,v in meta['scripts'].items())).encode()
rows=[]
for name,data in items.items():rows.append([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='),str(len(data))])
rows.append([info+'/RECORD','','']);stream=io.StringIO(newline='');csv.writer(stream).writerows(rows);items[info+'/RECORD']=stream.getvalue().encode()
(root/'dist').mkdir(exist_ok=True);out=root/'dist'/f'{dist}-{version}-py3-none-any.whl'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in sorted(items.items()):
  zi=zipfile.ZipInfo(name,(2026,10,21,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o600<<16;z.writestr(zi,data)
print(str(out),out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
