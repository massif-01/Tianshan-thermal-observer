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
    if type(m.get('schema_version')) is not int or type(m.get('feature_schema')) is not int or m.get('schema_version') not in (1, 2) or m.get('feature_schema') != m['schema_version'] or m.get('time_axis') != 'observer_receive' or m.get('horizons_s') != list(HORIZONS):
        raise ValueError('unsupported model contract')
    required_full, optional, columns = FULL_REQUIRED, OPTIONAL_COLUMNS, ALL_COLUMNS
    if m['schema_version'] == 2:
        from .profiles import validate_profile
        profile = validate_profile(m)
        required_full, optional, columns = profile['required'], profile['optional'], profile['columns']
    expected_scope = 'normal_auto' if m['schema_version'] == 1 else 'control_eligible'
    if m.get('training_scope') != expected_scope or not finite(m.get('source_period_s')) or m['source_period_s'] <= 0:
        raise ValueError('missing training scope/period')
    if m['schema_version'] == 2 and m['source_period_s']*1000 != m['input_contract']['source_period_ms']:
        raise ValueError('model source period differs from input contract')
    if set(m.get('methods', {})) != {'ridge_tj', 'ridge_full'}:
        raise ValueError('two frozen methods required')
    for name, method in m['methods'].items():
        cols = method.get('columns')
        if not isinstance(cols, list) or not all(isinstance(x, str) for x in cols) or len(set(cols)) != len(cols) or len(cols) > 64 or any(x not in columns for x in cols):
            raise ValueError('invalid feature columns')
        required = TJ_COLUMNS if name == 'ridge_tj' else TJ_COLUMNS + required_full
        if cols[:len(required)] != required:
            raise ValueError('feature order/required columns mismatch')
        if name == 'ridge_tj' and cols != TJ_COLUMNS:
            raise ValueError('TJ-only contract mismatch')
        if name == 'ridge_full':
            extra = cols[len(required):]
            expected = [x for group in optional.values() if all(x in extra for x in group) for x in group]
            if extra != expected:
                raise ValueError('optional fields must be complete ordered groups')
            if m['schema_version'] == 2:
                chosen = [field for field, group in optional.items() if all(x in extra for x in group)]
                if m.get('selected_optional_groups') != chosen:
                    raise ValueError('selected optional group identity mismatch')
                if 'gpu_busy' in chosen and m['input_contract']['gpu_period_ms'] is None:
                    raise ValueError('selected GPU group missing cadence evidence')
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


def eligible_scope(row):
    if row.get('feature_schema') == 2:
        return row.get('control_eligible') is True and row.get('feature_profile_id') is not None and row.get('input_contract_eligible') is True
    return row['normal_auto']


def model_dataset_match(model, dataset):
    if model['schema_version'] != dataset['schema_version'] or model['feature_schema'] != dataset['feature_schema']:
        raise ValueError('model/dataset schema mismatch')
    if dataset['schema_version'] == 2:
        from .profiles import compatible_contract
        if model['feature_profile_id'] != dataset['feature_profile_id'] or model['control_scope'] != dataset['control_scope'] or not compatible_contract(model['input_contract'], dataset['input_contract']):
            raise ValueError('model/dataset platform/control contract mismatch')


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
