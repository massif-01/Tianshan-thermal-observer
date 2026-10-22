"""Verify a finished candidate trial ZIP; read-only with respect to the run."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import zipfile


archive = Path(sys.argv[1])
with zipfile.ZipFile(archive) as z:
    names = z.namelist()
    crc_failure = z.testzip()
    hashes = json.loads(z.read('SHA256.json'))
    checks = {}
    for name, expected in hashes.items():
        data = z.read(name)
        checks[name] = {
            'bytes_match': len(data) == expected['bytes'],
            'sha256_match': hashlib.sha256(data).hexdigest() == expected['sha256'],
        }
    unindexed = sorted(set(names) - set(hashes) - {'SHA256.json'})
    summary = json.loads(z.read('summary.json'))
    events = [json.loads(line) for line in z.read('events.jsonl').splitlines()]
    requests = [json.loads(line) for line in z.read('requests.jsonl').splitlines()]
    manifest_name = next(n for n in names if n.endswith('/manifest.json'))
    manifest = json.loads(z.read(manifest_name))
    collection_prefix = manifest_name.removesuffix('manifest.json')
    collection_index = json.loads(z.read(collection_prefix + 'files.json'))
    collection_checks = {
        name: hashlib.sha256(z.read(collection_prefix + name)).hexdigest() == expected
        for name, expected in collection_index.items()
    }
    phase_starts = {e['phase']: e for e in events if e['event'] == 'phase_start'}
    phase_ends = {e['phase']: e for e in events if e['event'] == 'phase_end'}
    phases = []
    for name, start in phase_starts.items():
        end = phase_ends.get(name)
        phases.append({
            'phase': name, 'start_utc': start['occurred_at_utc'],
            'end_utc': end['occurred_at_utc'] if end else None,
            'actual_duration_s': end.get('actual_duration_s') if end else None,
            'nominal_window_s': start['duration_s'],
        })
    request_rows = [{k: r.get(k) for k in (
        'request_id', 'submitted_at_utc', 'client_end_at_utc',
        'duration_s', 'first_content_mono_s', 'submit_mono_s',
        'finish_reason', 'done', 'usage', 'status', 'server_status',
        'request_end_semantics',
    )} for r in requests]
    overlap = [b['request_id'] for a, b in zip(requests, requests[1:])
               if b['submit_mono_s'] < a['client_end_mono_s']]
    unknown = [r['request_id'] for r in requests
               if r.get('server_status') != 'protocol_completion_observed']
    verification = {
        'archive': str(archive.resolve()), 'archive_bytes': archive.stat().st_size,
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'zip_crc_failure': crc_failure, 'duplicate_members': len(names) != len(set(names)),
        'indexed_files': len(checks), 'file_checks': checks, 'unindexed_files': unindexed,
        'all_indexed_file_checks_pass': all(all(v.values()) for v in checks.values()),
        'collector_file_checks': collection_checks,
        'all_collector_file_checks_pass': all(collection_checks.values()),
        'collector_run_id': manifest['observer_run_id'],
        'collector_version': manifest['version'], 'collector_record_schema': manifest['record_schema'],
        'summary': summary, 'phases': phases, 'requests': request_rows,
        'request_count': len(requests),
        'request_status_counts': dict(Counter(r['status'] for r in requests)),
        'finish_reason_counts': dict(Counter(r.get('finish_reason') for r in requests)),
        'overlapping_request_ids': overlap, 'unknown_server_completion_ids': unknown,
        'event_counts': dict(Counter(e['event'] for e in events)),
        'scope': 'Archive integrity and recorded execution; not firmware safety certification or independent acceptance',
    }
print(json.dumps(verification, ensure_ascii=False, indent=2, allow_nan=False))
