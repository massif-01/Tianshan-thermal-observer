"""Offline package verification only. Does not run experiments or contact devices."""
from pathlib import Path
import hashlib, json, zipfile, sys

def main():
    root=Path(__file__).resolve().parent.parent
    manifest=json.loads((root/'SHA256.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path=root/row['path']
        if not path.is_file():raise RuntimeError(f"Missing file: {row['path']}")
        h=hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        if path.stat().st_size!=row['bytes'] or h.hexdigest()!=row['sha256']:
            raise RuntimeError(f"Identity mismatch: {row['path']}")
    for row in json.loads((root/'inputs/input-index.json').read_text(encoding='utf-8'))['inputs']:
        with zipfile.ZipFile(root/row['path']) as z:
            bad=z.testzip()
            if bad:raise RuntimeError(f"Corrupt ZIP member: {bad}")
    print(f"PASS: {len(manifest['files'])} file hashes and 2 original ZIP CRC checks. No model run or device access.")
if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f"Package check failed: {exc}",file=sys.stderr)
        raise SystemExit(1)
