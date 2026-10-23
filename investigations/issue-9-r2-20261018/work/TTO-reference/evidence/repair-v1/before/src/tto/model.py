"""Safe JSON inference; no numpy/sklearn import on the observer path."""
import math
from pathlib import Path
from .features import ALL_COLUMNS, FULL_REQUIRED, TJ_COLUMNS, OPTIONAL_COLUMNS
from .util import finite, read_json, verify_seal

HORIZONS = (15, 45, 90)


def load_model(path):
    if Path(path).stat().st_size > 5 * 1024 * 1024:
        raise ValueError('model exceeds 5MiB')
    m = verify_seal(read_json(path))
    if type(m.get('schema_version')) is not int or type(m.get('feature_schema')) is not int or m.get('schema_version') != 1 or m.get('feature_schema') != 1 or m.get('time_axis') != 'observer_receive' or m.get('horizons_s') != list(HORIZONS):
        raise ValueError('unsupported model contract')
    if m.get('training_scope') != 'normal_auto' or not finite(m.get('source_period_s')) or m['source_period_s'] <= 0:
        raise ValueError('missing training scope/period')
    if set(m.get('methods', {})) != {'ridge_tj', 'ridge_full'}:
        raise ValueError('two frozen methods required')
    for name, method in m['methods'].items():
        cols = method.get('columns')
        if not isinstance(cols, list) or not all(isinstance(x, str) for x in cols) or len(set(cols)) != len(cols) or len(cols) > 64 or any(x not in ALL_COLUMNS for x in cols):
            raise ValueError('invalid feature columns')
        required = TJ_COLUMNS if name == 'ridge_tj' else TJ_COLUMNS + FULL_REQUIRED
        if cols[:len(required)] != required:
            raise ValueError('feature order/required columns mismatch')
        if name == 'ridge_tj' and cols != TJ_COLUMNS:
            raise ValueError('TJ-only contract mismatch')
        if name == 'ridge_full':
            extra = cols[len(required):]
            expected = [x for group in OPTIONAL_COLUMNS.values() if all(x in extra for x in group) for x in group]
            if extra != expected:
                raise ValueError('optional fields must be complete ordered groups')
        n = len(cols)
        for key in ('mean', 'scale', 'minimum', 'maximum'):
            a = method.get(key)
            if not isinstance(a, list) or len(a) != n or not all(finite(v) for v in a):
                raise ValueError('invalid numeric preprocessing')
        if any(x <= 0 for x in method['scale']) or any(a > b for a, b in zip(method['minimum'], method['maximum'])):
            raise ValueError('invalid preprocessing ranges')
        if set(method.get('heads', {})) != {str(x) for x in HORIZONS}:
            raise ValueError('invalid horizons')
        for head in method['heads'].values():
            if not finite(head.get('intercept')) or len(head.get('coefficients', [])) != n or not all(finite(v) for v in head['coefficients']):
                raise ValueError('invalid coefficients')
    return m


def infer(model, name, features):
    method = model['methods'][name]
    x = [features.get(c) for c in method['columns']]
    if not all(finite(v) for v in x):
        return None, 'missing_selected_features', False
    z = [(v - mu) / scale for v, mu, scale in zip(x, method['mean'], method['scale'])]
    pred = {str(h): features['tj'] + head['intercept'] + math.fsum(a * b for a, b in zip(z, head['coefficients'])) for h, head in ((h, method['heads'][str(h)]) for h in HORIZONS)}
    if not all(finite(v) for v in pred.values()):
        return None, 'nonfinite_prediction', False
    outside = any(v < a or v > b for v, a, b in zip(x, method['minimum'], method['maximum']))
    return pred, None, outside
