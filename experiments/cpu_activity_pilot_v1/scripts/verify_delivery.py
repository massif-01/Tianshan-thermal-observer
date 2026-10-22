"""Offline ZIP CRC and member SHA/size verification; never installs or connects."""
import argparse,hashlib,json,zipfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('zip');a=p.parse_args()
with zipfile.ZipFile(a.zip) as z:
 bad=z.testzip()
 if bad:raise SystemExit('CRC failed: '+bad)
 manifest=json.loads(z.read('SHA256.json'))
 actual={x.filename for x in z.infolist() if not x.is_dir() and x.filename!='SHA256.json'}
 if actual!=set(manifest):raise SystemExit('member set differs from manifest')
 for name,meta in manifest.items():
  b=z.read(name)
  if len(b)!=meta['bytes'] or hashlib.sha256(b).hexdigest()!=meta['sha256']:raise SystemExit('identity mismatch: '+name)
 print(json.dumps(dict(crc_pass=True,sha_pass=True,checked_members=len(manifest)),indent=2))
