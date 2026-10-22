"""New private runs, bounded append-only logs, crash-safe single-instance lock."""
import fcntl
import json
import os
import shutil
import uuid
from pathlib import Path
from . import __version__
from .config import public_config
from .util import canonical, digest, file_hash, utc_now, write_json


class LimitReached(Exception):
    pass


class InstanceLock:
    def __init__(self, path=None):
        self.path = Path(path or f'/tmp/tto-observer-{os.getuid()}.lock')
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd)
            self.fd = None
            raise ValueError('另一个TTO观察进程正在运行。') from None
        return self

    def __exit__(self, *args):
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None
        # Never unlink a lock inode while another process could already hold it.


class Journal:
    def __init__(self, config, root=None, simulated=False, episode=None, deployment=None):
        self.c = config
        base = Path(root or config['storage']['data_root'] or Path.home() / '.local/share/tianshan-thermal-observer').expanduser()
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.run_id = str(uuid.uuid4())
        self.path = base / ('run-' + utc_now().replace(':', '').replace('+', '_') + '-' + self.run_id[:8])
        self.path.mkdir(mode=0o700)
        self.total = 0
        self.reserve = min(8 * 1024 ** 2, config['storage']['run_max_bytes'] // 10)
        self.chunk_index = 1
        self.chunk_size = 0
        self.handles = {}
        self.observation_count = 0
        self.episode = episode or self.run_id
        self.manifest = {'record_schema': 1, 'version': __version__, 'source_identity': source_identity(), 'config': public_config(config), 'config_sha256': digest(public_config(config)), 'observer_run_id': self.run_id, 'episode': self.episode, 'episode_evidence': 'operator_named_process' if episode else None, 'simulated': simulated, 'started_at_utc': utc_now(), 'time_axis': 'observer_receive', 'feature_schema': 1, 'model_schema': 1, 'input_schema': 1, 'units': {'temperature': 'C', 'raw_power': 'mW', 'features_power': 'W', 'duty': 'logical_percent', 'cpu_freq': 'MHz', 'gpu_gr3d_freq': 'busy_percent'}, 'fan_id': 0, 'deployment_status': 'deployment_unverified', 'ws_final_package_sha256': None, 'firmware_identity': None, 'source_period_ms': config['orin']['source_sample_interval_ms'], 'source_period_evidence': config['orin']['source_interval_evidence'], 'network_authorization': {'kind': 'offline_simulation' if simulated else 'explicit_bounded_cli', 'endpoints': [] if simulated else [config[s]['base_url'] for s in ('orin', 'tianshan')], 'business_writes': False}, 'operator_environment': 'unknown', 'control_elapsed_time_available': False}
        if deployment:
            self.manifest.update(deployment)
        manifest_bytes = len((json.dumps(self.manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
        if manifest_bytes > config['storage']['run_max_bytes'] - self.reserve:
            raise LimitReached('manifest_exceeds_run_budget')
        write_json(self.path / 'manifest.json', self.manifest)
        self.total = self.initial_metadata_bytes = manifest_bytes

    def append(self, name, row):
        raw = canonical(row) + b'\n'
        s = self.c['storage']
        if self.total + len(raw) > s['run_max_bytes'] - self.reserve:
            raise LimitReached('run_max_bytes')
        if shutil.disk_usage(self.path).free < s['min_free_bytes'] + len(raw):
            raise LimitReached('min_free_bytes')
        if name == 'observations':
            if len(raw) > s['chunk_bytes']:
                raise LimitReached('record_exceeds_chunk')
            if self.chunk_size + len(raw) > s['chunk_bytes']:
                self.chunk_index += 1
                self.chunk_size = 0
            filename = f'observations-{self.chunk_index:04d}.jsonl'
        else:
            filename = name + '.jsonl'
        if filename not in self.handles:
            fd = os.open(self.path / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            self.handles[filename] = os.fdopen(fd, 'wb')
        self.handles[filename].write(raw)
        self.handles[filename].flush()
        self.total += len(raw)
        if name == 'observations':
            self.chunk_size += len(raw)
            self.observation_count += 1
        return f'{self.run_id}/{filename}:{self.observation_count}'

    def observation(self, row):
        # References use a global observation ordinal; replay verifies it, even after rotation.
        row = dict(row, observer_run_id=self.run_id, episode=self.episode)
        row['ref'] = f'{self.run_id}/observation:{self.observation_count + 1}'
        self.append('observations', row)
        return row

    def close(self, summary):
        for f in self.handles.values():
            f.flush()
            os.fsync(f.fileno())
            f.close()
        self.handles.clear()
        summary = dict(summary, ended_at_utc=utc_now(), raw_bytes=self.total - self.initial_metadata_bytes, observations=self.observation_count)
        try:
            remaining = self.c['storage']['run_max_bytes'] - self.total
            summary_size = len((json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
            # Index is bounded by the number of chunk files and fixed output files.
            index_budget = 256 * (len(list(self.path.iterdir())) + 2)
            if summary_size + index_budget > remaining:
                raise LimitReached('final_metadata_exceeds_run_budget')
            write_json(self.path / 'summary.json', summary)
            write_json(self.path / 'files.json', {p.name: file_hash(p) for p in sorted(self.path.iterdir()) if p.is_file() and p.name != 'files.json'})
        except OSError:
            # Full-disk failure stays visible in the CLI's nonzero exit and stderr.
            raise


def source_identity():
    files = {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    return {'kind': 'package_source_hashes', 'sha256': digest(files), 'files': files, 'git_head': None, 'dirty': None, 'git_state': 'not_checked_in_installed_runtime'}
