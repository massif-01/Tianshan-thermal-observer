"""Offline JSON invocation of the same pure Predictor, not a collector."""
import argparse
import json
from pathlib import Path
from .predict import Predictor

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--input', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--manifest', type=Path)
a = p.parse_args()
result = Predictor(a.manifest).predict(**json.loads(a.input.read_text()))
with a.output.open('x') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    f.write('\n')
