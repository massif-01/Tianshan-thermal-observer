#!/usr/bin/env python3
"""Synthetic CPU inference on current host only; no device/benefit claim."""
import argparse
import json
import time
import platform
from pathlib import Path
import psutil
from tto.dataset import load_dataset
from tto.model import load_model, infer
from tto.evaluation import percentile
from tto.util import write_json

p = argparse.ArgumentParser()
p.add_argument('--model', required=True); p.add_argument('--dataset', required=True); p.add_argument('--output', required=True)
a = p.parse_args()
model = load_model(a.model); dataset = load_dataset(a.dataset)
row = next(r for r in dataset['rows'] if r['history_ready'] and all(r['features'].get(c) is not None for c in model['methods']['ridge_full']['columns']))
process = psutil.Process()
latencies = []
start = time.perf_counter(); c0 = process.cpu_times()
for _ in range(10000):
    t = time.perf_counter()
    assert infer(model, 'ridge_tj', row['features'])[0]
    assert infer(model, 'ridge_full', row['features'])[0]
    latencies.append((time.perf_counter() - t) * 1000)
c1 = process.cpu_times(); wall = time.perf_counter() - start
result = {'scope': 'synthetic_inference_current_host_only', 'simulated': True, 'host': platform.platform(), 'python': platform.python_version(), 'N305_measured': False, 'model_sha256': model['sha256'], 'iterations': len(latencies), 'two_methods_three_horizons_p99_ms': percentile(latencies, .99), 'p95_ms': percentile(latencies, .95), 'max_ms': max(latencies), 'wall_s': wall, 'CPU_seconds': c1.user+c1.system-c0.user-c0.system, 'cpu_pct_single_core': 100*(c1.user+c1.system-c0.user-c0.system)/wall, 'RSS_mib_including_loaded_offline_dataset': process.memory_info().rss/1024**2, 'steady_collection_CPU_measured': False, 'statement': '此循环故意满速执行，CPU百分比不代表1Hz稳态采集。'}
write_json(a.output, result)
print(json.dumps(result, ensure_ascii=False, indent=2))
