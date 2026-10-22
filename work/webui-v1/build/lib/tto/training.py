"""Train/validation-only field selection, weighted scaling and direct Ridge heads."""
import time
from .dataset import check_split, load_dataset
from .features import TJ_COLUMNS, FULL_REQUIRED, OPTIONAL_COLUMNS
from .model import HORIZONS, eligible_scope
from .util import digest, finite, read_json, seal, write_json


def eligible(row, cols, labels=True):
    return eligible_scope(row) and row['history_ready'] and all(finite(row['features'].get(c)) for c in cols) and (not labels or all(str(h) in row['labels'] for h in HORIZONS))


def row_weights(rows):
    """Each episode sums to one; irregular origins receive causal elapsed-time weights."""
    import numpy as np
    weights = np.zeros(len(rows))
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(r['episode'], []).append((i, r))
    for pairs in groups.values():
        pairs.sort(key=lambda p: (p[1]['run_id'], p[1]['t']))
        for j, (i, r) in enumerate(pairs):
            dt = 5.0
            if j and pairs[j - 1][1]['run_id'] == r['run_id'] and pairs[j - 1][1]['segment'] == r['segment']:
                dt = min(5.0, r['t'] - pairs[j - 1][1]['t'])
            weights[i] = max(dt, 1e-6)
        indexes = [i for i, _ in pairs]
        weights[indexes] /= sum(weights[indexes])
    return weights


def macro_mae(rows, errors):
    import numpy as np
    groups = {}
    for r, e in zip(rows, errors):
        groups.setdefault(r['episode'], []).append(abs(float(e)))
    return float(np.mean([np.mean(v) for v in groups.values()]))


def train(dataset_path, split_path, output):
    # Imported only inside an explicitly launched training command.
    import numpy as np
    from sklearn.linear_model import Ridge
    from threadpoolctl import threadpool_limits
    started = time.monotonic()
    d, s = load_dataset(dataset_path), read_json(split_path)
    byid = check_split(d, s)
    required_full, optional = FULL_REQUIRED, OPTIONAL_COLUMNS
    if d['schema_version'] == 2:
        from .profiles import validate_profile
        p = validate_profile(d)
        required_full, optional = p['required'], p['optional']
    train_rows = [byid[i] for i in s['partitions']['train']]
    validation_rows = [byid[i] for i in s['partitions']['validation']]
    base = [r for r in train_rows if eligible(r, TJ_COLUMNS)]
    if len(base) < 10:
        raise ValueError('训练区缺少合格控制范围、完整历史和三个未来标签；软件可用，效果待数据。')
    selected = []
    for field, cols in optional.items():
        valid = [r for r in base if all(finite(r['features'].get(c)) for c in cols)]
        values = [r['features'][field] for r in valid]
        if len(valid) / len(base) >= 0.95 and values and max(values) - min(values) > 1e-9:
            selected.extend(cols)
    full_cols = TJ_COLUMNS + required_full + selected
    common_train = [r for r in base if eligible(r, full_cols)]
    common_val = [r for r in validation_rows if eligible(r, full_cols)]
    if len(common_train) < 10 or len(common_val) < 5:
        raise ValueError('M0/M1公平比较缺少共同可用的训练/验证起点；先保留基线。')
    methods = {}
    comparisons = {}
    with threadpool_limits(limits=1):
        for name, cols in (('ridge_tj', TJ_COLUMNS), ('ridge_full', full_cols)):
            x = np.array([[r['features'][c] for c in cols] for r in common_train], dtype=float)
            xv = np.array([[r['features'][c] for c in cols] for r in common_val], dtype=float)
            w = row_weights(common_train)
            mean = np.average(x, axis=0, weights=w)
            variance = np.average((x - mean) ** 2, axis=0, weights=w)
            scale = np.sqrt(variance)
            scale[scale < 1e-12] = 1
            z, zv = (x - mean) / scale, (xv - mean) / scale
            fitted, scores = {}, {}
            for lam in (0.001, 0.01, 0.1, 1.0):
                if time.monotonic() - started > 590:
                    raise ValueError('training candidate time budget exceeded')
                heads = {}
                for h in HORIZONS:
                    y = np.array([r['labels'][str(h)]['value'] - r['features']['tj'] for r in common_train])
                    reg = Ridge(alpha=lam * float(w.sum()), fit_intercept=True, solver='svd')
                    reg.fit(z, y, sample_weight=w)
                    heads[str(h)] = {'coefficients': reg.coef_.tolist(), 'intercept': float(reg.intercept_)}
                    if h == 45:
                        truth = np.array([r['labels']['45']['value'] - r['features']['tj'] for r in common_val])
                        scores[str(lam)] = macro_mae(common_val, reg.predict(zv) - truth)
                fitted[lam] = heads
            minimum = min(scores.values())
            chosen = max(lam for lam in fitted if scores[str(lam)] <= minimum + 0.01)
            methods[name] = {'columns': cols, 'mean': mean.tolist(), 'scale': scale.tolist(), 'minimum': x.min(axis=0).tolist(), 'maximum': x.max(axis=0).tolist(), 'lambda': chosen, 'alpha': chosen * float(w.sum()), 'heads': fitted[chosen]}
            comparisons[name] = scores
    body = {'schema_version': d['schema_version'], 'feature_schema': d['feature_schema'], 'time_axis': 'observer_receive', 'horizons_s': list(HORIZONS), 'source_period_s': d['source_period_s'], 'training_scope': 'normal_auto' if d['schema_version'] == 1 else 'control_eligible', 'deployment_provenance': d['runs'], 'simulated': d['simulated'], 'not_a_control_model': True, 'objective': 'weighted_mean_squared_delta_error + lambda * squared_standardized_coefficients', 'scaling_weights': 'equal_episode_total_causal_elapsed_time_capped_at_origin_stride', 'optional_selection': 'training_only_95pct_available_nonconstant', 'selected_optional_groups': [f for f, cols in optional.items() if all(c in selected for c in cols)], 'dataset_sha256': d['sha256'], 'split_sha256': s['sha256'], 'train_sha256': digest(common_train), 'validation_sha256': digest(common_val), 'train_origin_ids': [r['id'] for r in common_train], 'validation_origin_ids': [r['id'] for r in common_val], 'train_count': len(common_train), 'm0_more_available_train_count': len(base), 'validation_count': len(common_val), 'validation_45s_episode_macro_mae': comparisons, 'methods': methods}
    if d['schema_version'] == 2:
        body.update({k: d[k] for k in ('feature_profile_id', 'control_scope', 'input_contract', 'input_contract_sha256')})
    model = seal(body)
    write_json(output, model)
    return model
