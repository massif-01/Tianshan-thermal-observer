"""Local user evidence, not a remote installation verifier."""
from pathlib import Path
from .util import digest, read_json


def deployment_record(path=None):
    if not path:
        return {'deployment_status': 'deployment_unverified', 'record_sha256': None, 'evidence_source': 'not_provided'}
    if Path(path).stat().st_size > 65536:
        raise ValueError('deployment record exceeds 64KiB')
    r = read_json(path)
    if r.get('record_schema') != 1:
        raise ValueError('unsupported deployment record')
    w = r.get('ws_candidate', {})
    checks = r.get('checks', {})
    config = r.get('effective_service_config', {})
    def sha(v):
        return isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v.lower())
    complete = (w.get('final_after_f1_f2') is True and all(sha(w.get(k)) for k in ('wheel_sha256', 'parser_sha256', 'cli_sha256', 'config_sha256', 'server_sha256')) and bool(w.get('installed_import_path')) and bool(w.get('final_closeout_evidence_ref')) and bool(config.get('evidence_ref')) and all(checks.get(k) is True for k in ('tj_reaches_tianshan', 'socketio_event_received', 'new_sequence_progresses', 'repeated_cache_not_new_sample', 'power_fields_valid', 'source_period_confirmed', 'fan_status_usable')))
    return {'deployment_status': 'user_recorded_not_independently_verified' if complete else 'deployment_unverified', 'record_sha256': digest(r), 'evidence_source': 'local_user_record', 'ws_final_package_sha256': w.get('wheel_sha256') if sha(w.get('wheel_sha256')) else None, 'final_after_f1_f2': w.get('final_after_f1_f2') is True, 'record_complete': bool(complete), 'statement': '本机记录由用户填写，不代表TTO远程核对了导入路径、配置或安装包。'}
