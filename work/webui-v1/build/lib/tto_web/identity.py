"""New Web candidate identity, distinct from the historical field manifest."""
import hashlib
import json
from pathlib import Path


def verify():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'web-candidate-files.json').read_text())
    for name,expected in manifest['files'].items():
        actual=hashlib.sha256((root.parent/name).read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Web candidate source identity mismatch')
    return dict(version=manifest['version'],checked_files=len(manifest['files']),baseline=manifest['baseline'],frozen_model_sha256=manifest['frozen_model_sha256'])
