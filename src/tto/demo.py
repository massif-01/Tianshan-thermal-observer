"""Deterministic synthetic object records. Never a device performance claim."""
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .config import load_config
from .engine import engine_for
from .storage import Journal
from .util import write_json


def packet(seq, tj, stream='demo-stream', fresh=True, age=0, cpu=30):
    return {'timestamp': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seq)).isoformat(), 'telemetry_meta': {'schema_version': 1, 'stream_id': stream, 'sample_seq': seq, 'received_at': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seq)).isoformat(), 'sample_age_ms': age, 'fresh': fresh, 'collector_state': 'running', 'freshness_timeout_ms': 5000, 'time_basis': 'collector_receive'}, 'temperature': {'tj': tj, 'cpu': tj - 3, 'soc0': tj - 5}, 'cpu': {'cores': [{'usage': cpu, 'freq': 1200 + cpu * 4} for _ in range(6)]}, 'gpu': {'gr3d_freq': cpu}, 'power': {'vdd_gpu_soc': {'current': cpu * 120, 'average': cpu * 100, 'unit': 'mW'}, 'vdd_cpu_cv': {'current': cpu * 80, 'average': cpu * 70, 'unit': 'mW'}, 'vin_sys_5v0': {'current': 10000 + cpu * 150, 'average': 10000 + cpu * 140, 'unit': 'mW'}}}


def fan_packet(duty=37):
    return {'code': 0, 'data': {'fans': [{'id': 0, 'mode': 'auto', 'enabled': True, 'fault': False, 'duty_valid': True, 'duty': duty, 'target_duty': 70, 'rpm': 0, 'controller_gain': 1.1, 'guard_active': False, 'temp_stale': False, 'auto_state': 'active', 'predicted_temperature': 47.5}]}}


def temp_packet():
    return {'code': 0, 'data': {'initialized': True, 'manual_mode': False, 'active_source': 'variable', 'preferred_source': 'variable', 'bound_variable': 'agx.tj', 'temperature_c': 42.0, 'temperature_01c': 420, 'valid': True, 'timestamp_ms': 1200}}


def record_demo(root, count=5, seconds=720, record_schema=1, family='jetson_orin', scope='auto'):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    runs = []
    c = load_config(environ={})
    c['orin'].update(source_sample_interval_ms=1000, source_interval_evidence='fixed_simulation_1Hz')
    for ep in range(count):
        journal = Journal(c, root, simulated=True, episode=f'simulation-process-{ep}', record_schema=record_schema)
        engine = engine_for(c, record_schema=record_schema)
        for t in range(seconds):
            cpu = 35 + 25 * math.sin((t + ep * 13) / 83) + 8 * math.sin(t / 17)
            tj = 46 + ep * .35 + 5 * math.sin((t + ep * 13) / 83 - .6) + .2 * math.cos(t / 13)
            for kind, payload in [('fan', fan_packet(35 + cpu * .2)), ('temp', temp_packet())] if t % 5 == 0 else [('fan', fan_packet(35 + cpu * .2))]:
                if kind == 'fan':
                    payload['data']['fans'][0]['mode'] = scope
                r = journal.observation({'kind': kind, 'mono_s': float(t), 'received_at_utc': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=ep, seconds=t)).isoformat(), 'payload': payload, 'sent_mono_s': float(t) - .01, 'round_trip_ms': 10})
                result = engine.process(r)
                journal.processing_output(r, result)
            payload = packet(t + 1, tj, stream=f'demo-{ep}', cpu=cpu)
            if record_schema == 2:
                from .profiles import FAMILIES, RAILS
                soc, backend = FAMILIES[family]
                payload['telemetry_meta']['source_sample_interval_ms'] = 1000
                payload['platform'] = {'schema_version': 1, 'family': family, 'soc': soc, 'gpu_backend': backend, 'compatible': ['nvidia,'+soc], 'identification_source': 'device_tree_compatible'}
                payload['gpu'].update(schema_version=1, utilization_pct=cpu, source=backend, status='valid', sampled_at_utc=payload['telemetry_meta']['received_at'], age_at_telemetry_receive_ms=0, sample_interval_ms=1000, freshness_timeout_ms=5000, device_uuid='GPU-SIMULATION' if backend == 'nvml' else None)
                if family == 'jetson_thor':
                    payload['gpu'].pop('gr3d_freq')
                    payload['temperature'] = dict(tj=tj, cpu=tj-3, soc012=tj-5, soc345=tj-6)
                    payload['power'] = {name: dict(current=cpu*(100+i*20), unit='mW') for i, name in enumerate(RAILS[family])}
            r = journal.observation({'kind': 'orin', 'mono_s': float(t), 'received_at_utc': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=ep, seconds=t)).isoformat(), 'connection_epoch': 1, 'payload': payload})
            result = engine.process(r)
            journal.processing_output(r, result)
        for score in engine.invalidate('run_end'):
            journal.append('scores', score)
        journal.close({'simulated': True, 'quality': dict(engine.q.counts), 'stop_reason': 'simulation_end', 'elapsed_s': seconds})
        runs.append(journal.path)
    return runs


def demo(output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    runs = record_demo(out / 'synthetic-runs', record_schema=2)
    from .dataset import freeze_split
    from .training import train
    from .evaluation import evaluate
    from .report import run_report
    split_dir = freeze_split(runs, out / 'frozen')
    train(split_dir / 'dataset.json', split_dir / 'split.json', out / 'model-simulation.json')
    evaluate(split_dir / 'dataset.json', split_dir / 'split.json', out / 'model-simulation.json', out / 'evaluation')
    run_report(runs[0], out / 'collection-report')
    write_json(out / 'SIMULATION-ONLY.json', {'simulated': True, 'statement': '固定模拟数据仅验证软件；模型不允许作为真实旁路候选。', 'run_count': len(runs), 'command': 'tto demo --output NEW_DIRECTORY'})
    return out
