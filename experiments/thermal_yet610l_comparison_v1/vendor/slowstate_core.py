"""Causal state substitutions and dimensionless offline signal; no hardware IO."""
import math
import numpy as np

BRANCHES = ['STATE-G2', 'STATE-QS', 'STATE-LP30', 'STATE-LP120']


def qs(TJ, E, duty_fraction, p):
    _, c, d0, d1, _, _ = p
    d = d0 + d1 * duty_fraction
    return (c * TJ + d * E) / (c + d)


def lp_step(previous, previous_input, dt, tau):
    assert dt >= 0 and tau > 0
    return previous_input + (previous - previous_input) * math.exp(-dt / tau)


def filters_at_origins(segment, E, p):
    """Only prefix operations. E must already be known before publishing an origin."""
    rows = segment['rows']
    by_time = {r['mono_s']: r for r in rows}
    timeline = segment['timeline']
    current_TJ = rows[0]['values']['tj']
    previous_t = timeline[0]['t']
    previous_q = qs(current_TJ, E, timeline[0]['inputs'][2], p)
    lp30 = lp120 = previous_q
    out = {}
    for node in timeline:
        t = node['t']
        dt = t - previous_t
        lp30 = lp_step(lp30, previous_q, dt, 30)
        lp120 = lp_step(lp120, previous_q, dt, 120)
        if t in by_time:
            row = by_time[t]
            current_TJ = row['values']['tj']
        current_q = qs(current_TJ, E, node['inputs'][2], p)
        if t in by_time:
            out[by_time[t]['ref']] = {'STATE-QS': current_q, 'STATE-LP30': lp30, 'STATE-LP120': lp120}
        previous_t, previous_q = t, current_q
    assert len(out) == len(rows)
    return out


def shape(state, reference, previous, dt):
    """Fixed demonstration scale, NOT a physical cooling or actuator command."""
    raw = (state - reference) / 10.0
    target = float(np.clip(raw, 0, 1))
    deadband = abs(target - previous) <= .02
    change = 0.0 if deadband else float(np.clip(target - previous, -dt / 120, dt / 30))
    output = previous + change
    return dict(state=state, reference=reference, z_raw=raw, z_target=target, z_output=output,
                deadband=deadband, change=change, dt_s=dt,
                lower_clipped=raw < 0, upper_clipped=raw > 1,
                rise_limited=not deadband and target - previous > dt / 30,
                fall_limited=not deadband and previous - target > dt / 120)


def reversal_count(values, threshold=.02):
    if len(values) < 2:
        return 0
    low = high = float(values[0])
    direction = count = 0
    for v in values[1:]:
        if direction == 0:
            if v >= low + threshold:
                direction, high = 1, v
            elif v <= high - threshold:
                direction, low = -1, v
            else:
                low, high = min(low, v), max(high, v)
        elif direction == 1:
            if v <= high - threshold:
                count += 1
                direction, low = -1, v
            else:
                high = max(high, v)
        else:
            if v >= low + threshold:
                count += 1
                direction, high = 1, v
            else:
                low = min(low, v)
    return count


def error_metrics(errors):
    e = np.array(errors, dtype=float)
    if len(e) == 0:
        return dict(n=0, MAE=None, bias=None, P95_abs=None, max_under=None, max_over=None)
    return dict(n=len(e), MAE=float(np.mean(abs(e))), bias=float(np.mean(e)),
                P95_abs=float(np.percentile(abs(e), 95)), max_under=float(max(0, -e.min())),
                max_over=float(max(0, e.max())))
