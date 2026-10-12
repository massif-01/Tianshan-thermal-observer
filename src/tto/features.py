"""One finite, causal feature implementation for live and offline replay."""
import bisect
import math
from collections import deque
from .util import finite

LAGS = (5, 15, 30, 60, 120, 180)
WINDOWS = (10, 30, 120)
OPTIONAL = tuple('temp_' + x for x in ('cpu', 'gpu', 'soc0', 'soc1', 'soc2')) + ('cpu_usage', 'cpu_freq', 'cpu_reported_cores', 'gpu_busy', 'vdd_gpu_soc', 'vdd_cpu_cv', 'vin_sys_5v0')
TJ_COLUMNS = ['tj'] + [f'tj_lag_{s}' for s in LAGS] + [f'tj_mean_{s}' for s in WINDOWS] + [f'tj_slope_{s}' for s in WINDOWS]
FULL_REQUIRED = ['duty', 'duty_mean_30', 'duty_mean_120', 'duty_change_30', 'gain']
OPTIONAL_COLUMNS = {field: [field, field + '_mean_30', field + '_mean_120'] for field in OPTIONAL}
ALL_COLUMNS = TJ_COLUMNS + FULL_REQUIRED + [x for cols in OPTIONAL_COLUMNS.values() for x in cols]
assert len(ALL_COLUMNS) <= 64


class Features:
    def __init__(self, period_s, profile=None, independent_gpu=False):
        self.period = period_s
        self.tolerance = min(5, max(2, 2 * period_s)) if period_s else 2
        self.gap = max(5, 3 * period_s) if period_s else 5
        self.history = deque()
        self.profile = profile
        self.independent_gpu = independent_gpu

    def clear(self):
        self.history.clear()

    def push(self, sample):
        t = sample['t']
        if self.history and t <= self.history[-1]['t']:
            raise ValueError('feature times must increase')
        self.history.append(sample)
        # Keep the causal as-of anchor at the 180-second edge, at most tolerance older.
        while self.history and self.history[0]['t'] < t - 180 - self.tolerance:
            self.history.popleft()
        # Excessively fast untrusted sources cannot exhaust memory.
        if len(self.history) > 4096:
            self.clear()
            raise ValueError('history sample budget exceeded')

    def asof(self, target):
        h = list(self.history)
        i = bisect.bisect_right([s['t'] for s in h], target) - 1
        if i < 0 or target - h[i]['t'] > self.tolerance:
            return None
        return h[i]

    def mean(self, field, window):
        h = list(self.history)
        now = h[-1]['t']
        start = now - window
        first = self.asof(start)
        if first is None:
            return None
        rows = [first] + [s for s in h if start < s['t'] <= now]
        acc = 0.0
        for a, b in zip(rows, rows[1:]):
            if b['t'] - a['t'] > self.gap or not finite(a['values'].get(field)):
                return None
            if (self.profile or self.independent_gpu) and field == 'gpu_busy' and (a.get('gpu_valid_until') is None or a['gpu_valid_until'] < b['t']):
                return None
            acc += a['values'][field] * (b['t'] - max(start, a['t']))
        if not finite(h[-1]['values'].get(field)):
            return None
        return acc / window

    def slope(self, window):
        h = [s for s in self.history if s['t'] >= self.history[-1]['t'] - window]
        if len(h) < 2 or h[-1]['t'] - h[0]['t'] < min(10, window - self.tolerance):
            return None
        return (h[-1]['values']['tj'] - h[0]['values']['tj']) / (h[-1]['t'] - h[0]['t'])

    def snapshot(self):
        if not self.history:
            return {}, []
        now = self.history[-1]
        t, v = now['t'], now['values']
        tj = v['tj']
        out = {'tj': tj}
        for sec in LAGS:
            s = self.asof(t - sec)
            out[f'tj_lag_{sec}'] = s['values']['tj'] - tj if s else None
        for sec in WINDOWS:
            m = self.mean('tj', sec)
            out[f'tj_mean_{sec}'] = m - tj if m is not None else None
            out[f'tj_slope_{sec}'] = self.slope(sec)
        out['duty'] = v.get('duty')
        if not self.profile or 'gain' in self.profile['required']:
            out['gain'] = v.get('gain')
        for sec in (30, 120):
            out[f'duty_mean_{sec}'] = self.mean('duty', sec)
        s = self.asof(t - 30)
        out['duty_change_30'] = v['duty'] - s['values']['duty'] if s and finite(v.get('duty')) and finite(s['values'].get('duty')) else None
        for field in self.profile['optional'] if self.profile else OPTIONAL:
            if field.startswith('temp_'):
                # Independently measured chip sensors, expressed relative to TJ.
                out[field] = v[field] - tj if finite(v.get(field)) else None
                for sec in (30, 120):
                    m, mtj = self.mean(field, sec), self.mean('tj', sec)
                    out[f'{field}_mean_{sec}'] = m - mtj if m is not None and mtj is not None else None
            else:
                out[field] = v.get(field)
                for sec in (30, 120):
                    out[f'{field}_mean_{sec}'] = self.mean(field, sec)
        refs = [s['ref'] for s in self.history]
        for s in self.history:
            refs += s.get('aux_refs', [])
        return out, sorted(set(refs))
