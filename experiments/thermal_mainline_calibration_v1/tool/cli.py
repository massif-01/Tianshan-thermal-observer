"""Offline generate/calibrate/compare and explicit local version selection."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from .util import ROOT, read, write, sha, load_job


def train(operation, job_path, parent, output):
    job, _, spec = load_job(job_path, operation, parent)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    core = ['worker.py', 'util.py', 'offline_runtime.py', '__init__.py']
    job['fit_execution_code_sha256'] = {n:sha(ROOT/'tool'/n) for n in core}
    write(out/'job-frozen.json', job)
    write(out/'experiment-spec.json', spec)
    write(out/'freeze-before-fit.json', dict(job_sha256=sha(out/'job-frozen.json'),
                 experiment_spec_sha256=sha(out/'experiment-spec.json'), validation_not_used_for_initialization_or_selection=True,
                 max_starts=6, resources=spec['limits'], baseline_not_modified=True))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ['OPENBLAS_NUM_THREADS','OPENBLAS_DEFAULT_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        env[key] = '1'
    began = time.monotonic()
    peak = 0.
    stopped = None
    with (out/'worker.log').open('w') as log:
        process = subprocess.Popen([sys.executable, '-m', 'tool.worker', '--out', str(out)], cwd=ROOT,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            heartbeat = out/'resource-heartbeat.json'
            if heartbeat.exists():
                peak = max(peak, read(heartbeat)['peak_RSS_MiB'])
            if time.monotonic()-began > spec['limits']['wall_seconds']:
                stopped = 'pre_registered_wall_budget_exceeded'
            if peak > spec['limits']['rss_MiB']:
                stopped = 'pre_registered_RSS_budget_exceeded'
            if stopped:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)
                break
            time.sleep(.1)
        code = process.wait()
    resource = dict(worker_pid=process.pid, returncode=code, elapsed_s=time.monotonic()-began,
                    sampled_peak_RSS_MiB=peak, RSS_sample_interval_s=.1, stopped_reason=stopped, training_in_observer_callback=False,
                    device_access=False, CUDA_used=False)
    if (out/'resource-heartbeat.json').exists():
        resource['last_worker_self_usage'] = read(out/'resource-heartbeat.json')
    write(out/'resources.json', resource)
    if code or stopped or not (out/'result.json').exists():
        write(out/'result.json', dict(status='numerical_or_runtime_failure', reason=stopped or 'see preserved worker.log',
                                     returncode=code, model_activated=False, baseline_unchanged=True))
    for name, digest in job['fit_execution_code_sha256'].items():
        if sha(ROOT/'tool'/name) != digest:
            raise ValueError('fit execution code changed during job: '+name)
    print(json.dumps(read(out/'result.json'), ensure_ascii=False, default=str))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['generate', 'calibrate']:
        s = sub.add_parser(name)
        s.add_argument('--job', type=Path, required=True)
        s.add_argument('--parent', type=Path, required=True)
        s.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('compare');s.add_argument('--plan', type=Path, required=True);s.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('register');s.add_argument('--registry', type=Path, required=True);s.add_argument('--manifest', type=Path, required=True)
    s.add_argument('--device-id');s.add_argument('--thermal-config-id')
    for name in ['activate', 'rollback']:
        s = sub.add_parser(name);s.add_argument('--registry', type=Path, required=True);s.add_argument('--model-id', required=True)
        s.add_argument('--confirm', action='store_true');s.add_argument('--reason', required=True)
    s = sub.add_parser('session-open');s.add_argument('--registry', type=Path, required=True);s.add_argument('--session-id', required=True)
    a = p.parse_args()
    if a.command in ('generate', 'calibrate'):
        train(a.command, a.job, a.parent, a.output)
    elif a.command == 'compare':
        from .comparison import compare
        compare(a.plan, a.output)
    else:
        from . import registry
        if a.command == 'register': result = registry.register(a.registry, a.manifest, device_id=a.device_id, thermal_config_id=a.thermal_config_id)
        elif a.command == 'session-open': result = registry.open_session(a.registry, a.session_id)
        else: result = registry.select(a.registry, a.model_id, confirm=a.confirm, reason=a.reason, action=a.command)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
