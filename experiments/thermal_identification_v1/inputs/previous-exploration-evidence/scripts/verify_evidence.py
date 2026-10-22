"""Offline integrity/identity checks. Never runs the archived workload script."""
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
SOURCE = OUT / 'sources/tto-reference/src/tto'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def verify_zip(path, index):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        hashes = json.loads(z.read(index))
        checks = [dict(path=n, bytes=len(z.read(n)), expected=h,
                       actual=sha(z.read(n)), match=sha(z.read(n)) == h)
                  for n, h in hashes.items()]
        core = []
        for n in z.namelist():
            if n.endswith('/files.json'):
                parent = n.rsplit('/', 1)[0]
                for f, h in json.loads(z.read(n)).items():
                    data = z.read(parent + '/' + f)
                    core.append(dict(path=parent + '/' + f, bytes=len(data),
                                     sha256=sha(data), match=sha(data) == h))
    return dict(name=path.name, bytes=path.stat().st_size,
                sha256=sha(path.read_bytes()), crc_first_bad=bad,
                indexed_count=len(checks), checks=checks, core_checks=core,
                passed=bad is None and all(c['match'] for c in checks + core))


def stamp(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    paths = [ROOT / 'deliverables/TTO-第二轮七工况数据与分析-20261013-929742d7.zip',
             ROOT / 'deliverables/TTO-短问答实测证据包-20261013-d2a7593a.zip']
    indexes = ['archive-file-hashes.json', 'SHA256.json']
    archives = [verify_zip(p, i) for p, i in zip(paths, indexes)]
    write('results/original-archive-verification.json', archives)
    private_checks, source_checks = [], []
    for name in ['formal-collection-20261013-round2', 'short-qa-20261013']:
        run = next((ROOT / 'evidence' / name).glob('run-*'))
        manifest = json.loads((run / 'manifest.json').read_text())
        core = [dict(path=f, sha256=sha((run / f).read_bytes()),
                     match=sha((run / f).read_bytes()) == h)
                for f, h in json.loads((run / 'files.json').read_text()).items()]
        private_checks.append(dict(run=manifest['observer_run_id'], directory=str(run.relative_to(ROOT)),
                                   checks=core, passed=all(c['match'] for c in core)))
        files = manifest['source_identity']['files']
        checks = [dict(path=f, expected=h, actual=sha((SOURCE / f).read_bytes()),
                       match=sha((SOURCE / f).read_bytes()) == h) for f, h in files.items()]
        source_checks.append(dict(run=manifest['observer_run_id'], version=manifest['version'],
                                 manifest_source_identity=manifest['source_identity']['sha256'],
                                 reference_commit='52f571acb128af44f4b06bbba049148e00fd97fb',
                                 module_count=len(checks), checks=checks,
                                 passed=all(c['match'] for c in checks),
                                 limit='Matches recorded package hashes; no current remote reinstall or flash-hash proof.'))
    write('results/private-original-run-index-verification.json', private_checks)
    write('identity/tto-recorded-source-comparison.json', source_checks)

    # Complement is assembled from the complete original ZIP, never the recovered copy.
    external = json.loads((OUT / 'sources/external-reference/integrity-results.json').read_text())
    missing = external['missing']
    missing = [x if isinstance(x, str) else x['path'] for x in missing]
    complement = ROOT / 'deliverables/TTO-短问答缺失60项补交-20261013.zip'
    with zipfile.ZipFile(paths[1]) as orig:
        hashes = json.loads(orig.read('SHA256.json'))
        assert len(missing) == 60 and all(n in hashes for n in missing)
        if complement.exists():
            with zipfile.ZipFile(complement) as saved:
                assert saved.read('original-SHA256.json') == orig.read('SHA256.json')
                assert all(saved.read(n) == orig.read(n) for n in missing)
        else:
            with zipfile.ZipFile(complement, 'w', zipfile.ZIP_DEFLATED) as new:
                selected = {}
                for n in missing:
                    data = orig.read(n)
                    assert sha(data) == hashes[n]
                    new.writestr(n, data)
                    selected[n] = hashes[n]
                new.writestr('original-SHA256.json', orig.read('SHA256.json'))
                new.writestr('complement-SHA256.json', json.dumps(selected, indent=2, ensure_ascii=False) + '\n')
                new.writestr('README.md',
                             '# 短问答归档补交\n\n来源为本机完整原ZIP，不是截断副本。\n'
                             '60个文件的路径、字节和SHA逐项对应原99项索引中的缺失项。\n'
                             f'原ZIP字节数：{archives[1]["bytes"]}；SHA：{archives[1]["sha256"]}。\n'
                             'original-SHA256.json逐字节保留原清单；complement-SHA256.json仅列这60项。\n')
    receipt = verify_zip(complement, 'complement-SHA256.json')
    receipt['relationship'] = '60 byte-identical members from complete original, plus original and subset indexes'
    receipt['external_recovered_checks'] = len(external['checks'])
    receipt['union_coverage'] = len(set(missing) | {c['path'] for c in external['checks']})
    write('results/complement-verification.json', receipt)

    # SSE is untimestamped; raw event clocks substantiate the logged times, not GPU completion.
    p = ROOT / 'evidence/short-qa-20261013'
    normalized = json.loads((p / 'normalized-requests.json').read_text())
    raw = {r['request_id']: r for r in map(json.loads, (p / 'workload/requests.jsonl').read_text().splitlines())}
    events = list(map(json.loads, (p / 'workload/events.jsonl').read_text().splitlines()))
    checks = []
    for n in normalized:
        qid = n['request_id']
        r = raw[qid]
        data = (p / 'workload' / f'{qid}-response.sse').read_bytes()
        chunks, done = [], False
        for line in data.decode().splitlines():
            if not line.startswith('data: '):
                continue
            body = line[6:]
            if body == '[DONE]':
                done = True
            else:
                chunks.append(json.loads(body))
        choices = [c for x in chunks for c in x.get('choices', [])]
        finish = [c['finish_reason'] for c in choices if c.get('finish_reason')]
        usage = [x['usage'] for x in chunks if x.get('usage')]
        content = [c.get('delta', {}) for c in choices if c.get('delta', {}).get('content') or c.get('delta', {}).get('reasoning_content')]
        fields = ['submitted_at_utc', 'submit_mono_s', 'first_network_at_utc',
                  'first_model_content_at_utc', 'first_visible_content_at_utc',
                  'finish_reason_at_utc', 'client_end_at_utc', 'end_mono_s',
                  'duration_seconds', 'usage', 'finish_reason', 'status', 'done']
        same = all(n.get(f) == r.get(f) for f in fields)
        ev = [e for e in events if e.get('question_id') == qid]
        timing = []
        mapping = {'request_submit': 'submitted_at_utc',
                   'first_network_packet': 'first_network_at_utc',
                   'first_model_content': 'first_model_content_at_utc',
                   'first_visible_content': 'first_visible_content_at_utc',
                   'finish_reason': 'finish_reason_at_utc',
                   'request_end': 'client_end_at_utc'}
        for event, field in mapping.items():
            selected_events = [e for e in ev if e['event'] == event]
            timing.append(dict(event=event, count=len(selected_events),
                               timestamp=r.get(field),
                               log_delta_s=stamp(selected_events[0]['event_time_utc']) - stamp(r[field])
                               if selected_events and r.get(field) else None))
        ordered = [stamp(r[k]) for k in ['submitted_at_utc', 'first_network_at_utc',
                                         'first_model_content_at_utc', 'first_visible_content_at_utc',
                                         'finish_reason_at_utc', 'client_end_at_utc']]
        check = dict(request=qid, sse_sha256=sha(data), sse_bytes=len(data),
                     normalized_equals_raw=same, finish_matches=finish == [r['finish_reason']],
                     usage_matches=usage == [r['usage']], done_matches=done == r['done'],
                     has_content=bool(content), server_id_matches=all(x['id'] == r['server_request_id'] for x in chunks),
                     times_in_order=ordered == sorted(ordered),
                     duration_matches_mono=abs((r['end_mono_s'] - r['submit_mono_s']) - r['duration_seconds']) < 1e-8,
                     event_time_checks=timing, duration_s=r['duration_seconds'])
        check['event_times_match'] = all(t['count'] == 1 and t['log_delta_s'] is not None
                                         and abs(t['log_delta_s']) < 0.1 for t in timing)
        check['passed'] = all(check[k] for k in ['normalized_equals_raw', 'finish_matches', 'usage_matches',
                                                'done_matches', 'has_content', 'server_id_matches',
                                                'times_in_order', 'duration_matches_mono', 'event_times_match'])
        checks.append(check)
    write('results/request-sse-verification.json', dict(count=len(checks), formal_count=18,
                                                       checks=checks, passed=all(c['passed'] for c in checks),
                                                       timing_limit='SSE body has no per-chunk client timestamps; first-content times are client event evidence, not independently reconstructed from body or GPU end.'))
    assert all(a['passed'] for a in archives + private_checks + source_checks + [receipt])
    assert all(c['passed'] for c in checks)
    print(json.dumps(dict(archives=[{k:a[k] for k in ['name','bytes','sha256','indexed_count','passed']} for a in archives],
                          complement={k:receipt[k] for k in ['name','bytes','sha256','indexed_count','union_coverage','passed']},
                          request_checks=len(checks), request_passed=True), ensure_ascii=False))


if __name__ == '__main__':
    main()
