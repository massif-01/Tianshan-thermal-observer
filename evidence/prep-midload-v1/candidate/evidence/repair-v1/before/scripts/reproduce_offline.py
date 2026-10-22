#!/usr/bin/env python3
"""One installed-wheel verification entry; never installs or contacts devices."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tto.util import write_json


def run(cmd, cwd, out, env):
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    out.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('offline command failed; see ' + str(out))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True)
    a = p.parse_args()
    output = Path(a.output).resolve(); output.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parent.parent
    import tto
    # Installed entry must not resolve to the package's authoring source checkout.
    location = Path(tto.__file__).resolve()
    if package / 'src' in location.parents:
        raise RuntimeError('independent verification requires a non-editable installed wheel')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    for key in list(env):
        if key.startswith('TTO_'):
            env.pop(key)
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        env[key] = '1'
    # Pytest automatically denies external sockets/subprocesses. Signal verification uses
    # an explicit loopback server and its own guarded child process.
    run([sys.executable, '-m', 'pytest', '-q', str(package / 'tests'), '--junitxml=' + str(output / 'junit.xml')], output, output / 'tests.txt', env)
    guard = output / 'guard'; guard.mkdir()
    guard_source = (package / 'scripts/verify_signals.py').read_text()
    import ast
    module = ast.parse(guard_source)
    code = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'GUARD' for t in n.targets))
    (guard / 'sitecustomize.py').write_text(code)
    guarded = dict(env, PYTHONPATH=str(guard))
    run([sys.executable, '-m', 'tto', 'doctor', '--config', str(package / 'config/tto.example.json')], output, output / 'doctor.txt', guarded)
    run([sys.executable, '-m', 'tto', 'demo', '--output', str(output / 'demo')], output, output / 'demo.txt', guarded)
    run([sys.executable, str(package / 'scripts/verify_signals.py'), '--output', str(output / 'signals')], output, output / 'signals.txt', env)
    run([sys.executable, str(package / 'scripts/benchmark_offline.py'), '--model', str(output / 'demo/model-simulation.json'), '--dataset', str(output / 'demo/frozen/dataset.json'), '--output', str(output / 'benchmark.json')], output, output / 'benchmark.txt', guarded)
    run([sys.executable, '-m', 'tto', 'train', '--dataset', str(output / 'demo/frozen/dataset.json'), '--split', str(output / 'demo/frozen/split.json'), '--output', str(output / 'model-via-cli.json')], output, output / 'train.txt', guarded)
    write_json(output / 'verification.json', {'passed': True, 'package_import_path': str(location), 'offline': True, 'network_scope': 'loopback_fixture_only', 'real_devices': False, 'prediction_effectiveness_verified': False})
    print(json.dumps({'passed': True, 'output': str(output), 'prediction_effectiveness': '待真实数据'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
