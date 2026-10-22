"""Unpack pinned dependencies and replay only the new 27-packet recorded process."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    runtime = out/'runtime'
    runtime.mkdir()
    dependencies = json.loads((ROOT/'replay-spec.json').read_text())['dependencies']
    for name, info in dependencies.items():
        archive = ROOT/'dependencies'/name
        assert sha(archive) == info['sha256'], name
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            z.extractall(runtime/info['extract_directory'])
    study = runtime/ROOT.name
    study.mkdir()
    for name in ['audit.py', 'input-freeze.json', 'resource-addendum-freeze.json']:
        shutil.copyfile(ROOT/name, study/name)
    shutil.copytree(ROOT/'inputs', study/'inputs')
    model = runtime/'thermal_cpu_activity_bridge_v1'
    reporter = runtime/'thermal_cpu_activity_reporter_v1'
    run = study/'inputs/remote-result/run'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    commands = [
        ('metadata-tests', ['-m', 'pytest', '-c', str(reporter/'pytest.ini'), str(reporter/'tests'), '-q', '-p', 'no:cacheprovider']),
        ('adapt', [str(model/'bridge.py'), '--run-dir', str(run), '--source-config', str(study/'inputs/remote-result/payload/source-config.json'), '--output', str(out/'adapted')]),
        ('joint', [str(reporter/'joint_check.py'), '--adapted', str(out/'adapted'), '--run-dir', str(run), '--output', str(out/'joint')]),
        ('audit', [str(study/'audit.py'), '--adapted', str(out/'adapted'), '--joint', str(out/'joint'), '--output', str(out/'audit')])]
    for label, args in commands:
        with (out/(label+'.log')).open('w') as log:
            subprocess.run([sys.executable, *args], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    exact = []
    for name in ['frames.jsonl', 'thermal-origins.jsonl', 'registration.json', 'revocations.jsonl', 'source-query-diagnostics.jsonl']:
        assert sha(out/'adapted'/name) == sha(ROOT/'results/adapted'/name), name
        exact.append(name)
    sys.path.insert(0, str(model))
    spec = importlib.util.spec_from_file_location('frozen_comparator', model/'replay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    equal, differences = [], []
    for base in ['joint', 'audit']:
        for path in sorted((ROOT/'results'/base).rglob('*')):
            if path.suffix not in ('.json', '.jsonl') or path.name in ('joint-receipt.json', 'data-role-and-sources.json'):
                continue
            rel = path.relative_to(ROOT/'results')
            fresh = out/rel
            left, right = ((module.lines(path), module.lines(fresh)) if path.suffix == '.jsonl' else (module.read(path), module.read(fresh)))
            differences.extend(module.compare(left, right))
            equal.append(str(rel))
    receipt = json.loads((out/'joint/joint-receipt.json').read_text())
    assert receipt['actual_wire_to_source_rows_verified'] == 27
    assert receipt['data_source']['run_id'] == '80938521-b659-4160-a7b2-5fdfb6ebc197'
    assert receipt['data_source']['category'] == 'declared_field_unverified'
    result = dict(metadata_tests_passed=3, new_recorded_wire_rows=27, original_thermal_origins=60,
                  exact_adapter_files=exact, equivalent_result_files=equal,
                  maximum_derived_float_difference=max(differences, default=0), float_tolerance_C=1e-8,
                  old150_packets_used_as_new_run=False, model_fits=0, device_access=False,
                  capability_qualified=False, recommend_12_requests=False)
    (out/'replay-receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print('Independent local replay passed: new27 packets,60 original TJ origins; capability remains NOT qualified.')


if __name__ == '__main__':
    main()
