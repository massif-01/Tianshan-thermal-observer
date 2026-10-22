#!/usr/bin/env python3
"""Verify this handoff only. Does not run models, extract inputs or access a network."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        manifest = json.loads((root / 'SHA256.json').read_text(encoding='utf-8'))
        for rel, expected in manifest['files'].items():
            path = (root / rel).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f'Path outside handoff: {rel}')
            data = path.read_bytes()
            if len(data) != expected['bytes'] or digest(data) != expected['sha256']:
                raise ValueError(f'File mismatch: {rel}')
        inventory = json.loads((root / 'inputs/input-index.json').read_text(encoding='utf-8'))
        for entry in inventory['archives']:
            with zipfile.ZipFile(root / entry['path']) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f'ZIP CRC mismatch: {entry["path"]}/{bad}')
        old = json.loads((root / 'references/frozen-old-model-index.json').read_text(encoding='utf-8'))
        for entry in old['models']:
            with zipfile.ZipFile(root / entry['archive']) as archive:
                data = archive.read(entry['member'])
            if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
                raise ValueError(f'Frozen model mismatch: {entry["member"]}')
        ambient = json.loads((root / 'metadata/M-ambient-user-confirmed.json').read_text(encoding='utf-8'))
        spec = json.loads((root / 'templates/experiment-spec.json').read_text(encoding='utf-8'))
        if ambient['run_id'] != spec['run_ids']['M'] or ambient['ambient_temperature_C'] != 24.0:
            raise ValueError('Ambient/M binding mismatch')
        if len(spec['stage3']['matrices']) * 2 * len(spec['stage3']['initializations']) != 36:
            raise ValueError('Main fitting budget mismatch')
        print(json.dumps({'status':'handoff_verified','files':len(manifest['files']),
                          'input_archives':len(inventory['archives']),
                          'frozen_model_json_files':len(old['models']),
                          'new_model_training':'not_performed','device_access':False},
                         ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
        print(f'交接包校验失败：{exc}',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
