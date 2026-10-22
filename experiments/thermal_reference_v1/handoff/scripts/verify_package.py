#!/usr/bin/env python3
"""Check this handoff only; no network, installation or device access."""
from pathlib import Path
import hashlib
import json
import sys

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = root / 'SHA256.json'
    try:
        entries = json.loads(manifest.read_text(encoding='utf-8'))['files']
        for name, info in entries.items():
            path = (root / name).resolve()
            if root not in path.parents:
                raise ValueError('Unsafe manifest path: ' + name)
            data = path.read_bytes()
            if len(data) != info['bytes'] or hashlib.sha256(data).hexdigest() != info['sha256']:
                raise ValueError('Mismatch: ' + name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Package verification failed:', exc, file=sys.stderr)
        return 1
    print(f'Package verified: {len(entries)} files; no device action performed.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
