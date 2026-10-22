"""Offline evidence replay. Default reuses candidates; --fit repeats the fixed 6+6 budget."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tool.util import read, write, sha


def equivalent(a, b, path='root'):
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), path
        for k in a:
            equivalent(a[k], b[k], path+'.'+k)
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            equivalent(x, y, path+f'[{i}]')
    elif type(a) in (int, float):
        assert type(b) in (int, float) and math.isclose(a, b, rel_tol=0, abs_tol=1e-8), (path, a, b)
    else:
        assert a == b, (path, a, b)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fit', action='store_true', help='Opt in to the original fixed six-start generate and six-start calibrate jobs')
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('VECLIB_MAXIMUM_THREADS', 'OPENBLAS_NUM_THREADS', 'OPENBLAS_DEFAULT_NUM_THREADS',
                'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env[key] = '1'
    commands = []

    def run(args, name, cwd=ROOT, extra_env=None):
        cmd = [sys.executable]+args
        with (out/(name+'.log')).open('w') as f:
            process = subprocess.run(cmd, cwd=cwd, env=dict(env, **(extra_env or {})),
                                     stdout=f, stderr=subprocess.STDOUT)
        commands.append(dict(argv=cmd, cwd=str(cwd), returncode=process.returncode))
        write(out/'commands.json', commands)
        if process.returncode:
            raise RuntimeError('offline replay failed; see '+str(out/(name+'.log')))

    run(['-m', 'pytest', '-c', 'pytest.ini', 'tests', '--confcutdir=.', '-q', '-p', 'no:cacheprovider'],
        'A1-tests', ROOT/'baseline')
    run(['-m', 'pytest', '-c', 'pytest.ini', 'tests', '--confcutdir=.', '-q', '-p', 'no:cacheprovider'], 'tool-tests')
    run(['-m', 'g2_runtime', '--input', 'golden/request.json', '--output', str(out/'A1-api.json')],
        'A1-api', ROOT/'baseline')
    gen = ROOT/'runs/generate/model-bundle/model-manifest.json'
    cal = ROOT/'runs/calibrate/model-bundle/model-manifest.json'
    if a.fit:
        run(['-m', 'tool', 'generate', '--job', 'config/generate.json', '--parent',
             'baseline/frozen-model-manifest.json', '--output', str(out/'generate')], 'generate')
        gen = out/'generate/model-bundle/model-manifest.json'
        run(['-m', 'tool', 'calibrate', '--job', 'config/calibrate.json', '--parent', str(gen),
             '--output', str(out/'calibrate')], 'calibrate')
        cal = out/'calibrate/model-bundle/model-manifest.json'
    plan = read(ROOT/'config/compare.json')
    plan['dataset'] = str(ROOT/'inputs/dataset.json')
    for item, path in zip(plan['models'], [ROOT/'baseline/frozen-model-manifest.json', gen, cal]):
        item['manifest'] = str(path)
    write(out/'compare-plan.json', plan)
    run(['-m', 'tool', 'compare', '--plan', str(out/'compare-plan.json'), '--output', str(out/'compare')], 'compare')
    checked = []
    for filename in ['predictions.jsonl', 'A-long-points.jsonl', 'B-metrics.json', 'A-roll-metrics.json',
                     'A-long-metrics.json', 'coverage.json', 'decisions.json']:
        expected, actual = ROOT/'runs/compare'/filename, out/'compare'/filename
        if not a.fit:
            if filename.endswith('.jsonl'):
                equivalent([json.loads(x) for x in expected.read_text().splitlines()],
                           [json.loads(x) for x in actual.read_text().splitlines()], filename)
            else:
                equivalent(read(expected), read(actual), filename)
        checked.append(dict(file=filename, original_sha256=sha(expected), replay_sha256=sha(actual),
                            values_compared_to_1e_8_C=not a.fit))
    write(out/'replay-result.json', dict(status='passed', theta_fits=12 if a.fit else 0,
          note='Opt-in refits may select numerically near-tied seeds across runtimes; no exact theta or ranking claim' if a.fit else 'Same retained candidates; all point identities and numerical outputs reproduced',
          checks=checked, control_permission=False, device_access=False, network_clients=0))
    print('Offline replay passed:', out)


if __name__ == '__main__':
    main()
