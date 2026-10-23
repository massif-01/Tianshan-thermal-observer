"""Prepare a public replay copy; never write the private study or raw originals."""
from pathlib import Path
import argparse, collections, difflib, hashlib, ipaddress, json, re, shutil, zipfile


def digest(b):
    return hashlib.sha256(b).hexdigest()


def encoded(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def prepare(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(parents=True, exist_ok=False)
    replacements = collections.Counter()
    endpoint_aliases = {}

    def text(s):
        def endpoint(m):
            replacements['private_endpoint'] += 1
            value = m.group()
            if value not in endpoint_aliases:
                endpoint_aliases[value] = 'http://endpoint-' + str(len(endpoint_aliases) + 1) + '.invalid'
            return endpoint_aliases[value]
        s = re.sub(r'https?://[^\s\"<>]+', endpoint, s)
        s, n = re.subn(r'/(?:Users|home)/[^\s\"<>]+|/(?:private/)?(?:var/folders|tmp)/[^\s\"<>]+', '<private-path>', s)
        replacements['private_path'] += n
        def address(m):
            v = m.group()
            try:
                ip = ipaddress.ip_address(v)
            except ValueError:
                return v
            if ip.is_private and not ip.is_loopback:
                replacements['private_address'] += 1
                return 'host.invalid'
            return v
        return re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', address, s)

    def scrub(x):
        if isinstance(x, dict):
            return {k: scrub(v) for k, v in x.items()}
        if isinstance(x, list):
            return [scrub(v) for v in x]
        if isinstance(x, str):
            return text(x)
        return x

    def clean_bytes(name, b):
        if name == 'mapping/import_yet610l.py':
            # Archived format adapter: require an explicit tool instead of publishing its author's local default.
            s, n = re.subn(r"default=Path\('/Users/[^']+'\)", 'required=True', b.decode())
            replacements['archived_import_tool_default_path_removed'] += n
            compile(s, name, 'exec')
            return s.encode()
        if name.endswith('.json'):
            d = json.loads(b)
            c = scrub(d)
            return b if c == d else encoded(c)
        if name.endswith('.jsonl'):
            rows = [json.loads(l) for l in b.decode().splitlines() if l]
            clean = [scrub(r) for r in rows]
            return b if clean == rows else ('\n'.join(json.dumps(r, ensure_ascii=False) for r in clean) + '\n').encode()
        return b

    raw = source / 'inputs/本轮完整原始证据.zip'
    raw_bytes = raw.read_bytes()
    assert digest(raw_bytes) == 'c0c3e1895ca9893d90a27559a491093aa4de1209ab1ae317494adc5ef3c94273'
    z = zipfile.ZipFile(raw)
    assert z.testzip() is None
    original_manifest = json.loads(z.read('SHA256.json'))['files']
    for n, v in original_manifest.items():
        b = z.read(n)
        assert len(b) == v['bytes'] and digest(b) == v['sha256'], n
    keep = {'plan.json', 'policy.json', 'authorization.json', 'probe-description.json',
            'checks/computer-side-verification.json', 'checks/instrument-coverage.json',
            'checks/original-csv-receipt.json', 'checks/start-file-identities.json',
            'checks/start-confirmation.json', 'checks/end-confirmation.json',
            'remote-result/native-health.json', 'remote-result/final-native-health.json',
            'remote-result/transient-temp-events.jsonl', 'workload/frozen-request-plan.json',
            'workload/questions.json', 'workload/operator-final.json',
            'workload-output/events.jsonl', 'workload-output/requests.jsonl',
            'workload-output/summary.json', 'workload-output/status.json',
            'mapping/import_yet610l.py'}
    for n in original_manifest:
        if n.startswith(('remote-result/collection/', 'imported-instrument-v2/', 'original-csv/')):
            keep.add(n)
        if n.startswith('clock-evidence/') and n.endswith('.json'):
            keep.add(n)
    payload = {n: clean_bytes(n, z.read(n)) for n in sorted(keep)}
    manifest_name = next(n for n in payload if '/collection/' in n and n.endswith('/manifest.json'))
    m = json.loads(payload[manifest_name])
    original_config_hash = m['config_sha256']
    m['config_sha256'] = digest(json.dumps(m['config'], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    m['publication'] = {'kind': 'public_replay_derivative', 'original_manifest_sha256': digest(z.read(manifest_name)),
                        'original_config_sha256': original_config_hash,
                        'note': 'Only infrastructure strings redacted; config hash describes this public copy. Not an executable live configuration.'}
    payload[manifest_name] = encoded(m)
    index_name = manifest_name.rsplit('/', 1)[0] + '/files.json'
    index = json.loads(payload[index_name])
    for n in index:
        index[n] = digest(payload[index_name.rsplit('/', 1)[0] + '/' + n])
    payload[index_name] = encoded(index)
    evidence = {'kind': 'public-replay-derivative-v1', 'original_private_archive_sha256': digest(raw_bytes),
                'original_private_archive_bytes': len(raw_bytes), 'original_verified_members': len(original_manifest),
                'rules': 'Temperature/power/PWM/flags/timestamps/references unchanged; no quality relaxation. Photos, live scripts, duplicated service snapshots and unrelated payload bodies omitted.',
                'retained': {n: {'original_sha256': digest(z.read(n)), 'public_sha256': digest(b), 'bytes': len(b), 'unchanged': z.read(n) == b} for n, b in payload.items()},
                'omitted': {n: {'sha256': v['sha256'], 'bytes': v['bytes'], 'reason': 'Not required for offline numerical replay; private photograph, infrastructure/live tooling or duplicate/contextual capture. Original preserved privately.'} for n, v in original_manifest.items() if n not in payload},
                'redaction_counts': dict(replacements)}
    payload['PUBLIC-DERIVATION.json'] = encoded(evidence)
    public_manifest = {'kind': 'public-replay-input-v1', 'files': {n: {'sha256': digest(b), 'bytes': len(b)} for n, b in payload.items()}}
    (target / 'inputs').mkdir()
    archive = target / 'inputs/evidence-public.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=8) as out:
        for n, b in payload.items():
            out.writestr(n, b)
        out.writestr('SHA256.json', encoded(public_manifest))

    for dirname in ['models', 'vendor', 'tests']:
        for p in sorted((source / dirname).rglob('*')):
            if p.is_file() and p.suffix in ['.py', '.c', '.json'] and '__pycache__' not in p.parts:
                dest = target / p.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dest)
    for n in ['run.py', 'replay_new.py', 'trajectories.py', 'compare_surface.py', 'plots_report.py', 'requirements.txt', 'spec.json']:
        shutil.copyfile(source / n, target / n)
    identity = json.loads((source / 'source-identity.json').read_text())
    identity['original_private_input_archive_sha256'] = identity['input_archive_sha256']
    identity['original_private_members_verified'] = identity['data_members_verified']
    identity['input_archive_sha256'] = digest(archive.read_bytes())
    identity['data_members_verified'] = len(public_manifest['files'])
    identity['publication_derivative'] = True
    (target / 'source-identity.json').write_bytes(encoded(identity))
    p = target / 'run.py'
    s = p.read_text().replace("assert sha(archive)=='c0c3e1895ca9893d90a27559a491093aa4de1209ab1ae317494adc5ef3c94273'", "assert sha(archive)==read(ROOT/'source-identity.json')['input_archive_sha256']")
    s = s.replace('original_255_members_unchanged=True', 'public_input_members_unchanged=True,verified_input_members=len(protected)')
    p.write_text(s)
    p = target / 'plots_report.py'
    s = p.read_text()
    for n in ['图1-真实温度与输入', '图2-原生资格与初始化覆盖', '图3-时间敏感性与比较边界']:
        s = s.replace("{out.absolute()/'" + n + ".png'}", n + '.png')
    s = s.replace('来源ZIP为18020171字节', '私有原始来源ZIP为18020171字节')
    s = s.replace('CRC及255项成员已再次核对；', '原计算阶段CRC及255项成员已核对；公开复核副本的独立SHA、保留/省略清单见inputs/evidence-public.zip内PUBLIC-DERIVATION.json，不能冒称私有原件；')
    s = s.replace('本轮只在独立研究目录生成派生文件；', '以下边界指原离线研究计算阶段；本次另以文档PR发布脱敏副本。原研究只在独立研究目录生成派生文件；')
    p.write_text(s)

    prov = target / 'provenance'
    prov.mkdir()
    (prov / 'public-input-derivation.json').write_bytes(encoded(evidence))
    (prov / 'original-source-identity.json').write_bytes((source / 'source-identity.json').read_bytes())
    (prov / 'original-evidence-identity.json').write_bytes((source / 'artifact-SHA256.json').read_bytes())
    for n in ['stage1-freeze.json', 'completion.json', 'environment-resources.json', 'tests.log']:
        (prov / ('original-' + n)).write_bytes(clean_bytes(n, (source / 'runs/deliverable' / n).read_bytes()))
    changes = []
    for n in ['run.py', 'plots_report.py', 'source-identity.json']:
        changes.extend(difflib.unified_diff((source / n).read_text().splitlines(True), (target / n).read_text().splitlines(True), fromfile='private-study/' + n, tofile='public-study/' + n))
    (prov / 'publication-adaptation.patch').write_text(''.join(changes))
    original = target / 'reference-output'
    for p in sorted((source / 'runs/deliverable').rglob('*')):
        rel = p.relative_to(source / 'runs/deliverable')
        if not p.is_file() or rel.parts[0] in ['input', 'pytest-cache'] or p.suffix == '.so':
            continue
        dest = original / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        b = p.read_bytes()
        if p.suffix == '.md':
            b = text(b.decode()).encode()
        else:
            b = clean_bytes(p.name, b)
        dest.write_bytes(b)
    # Preserve the reviewed report, including its independent replay appendix, with portable images.
    report = (source / 'delivery/TTO-YET610L同步短问答-冻结模型比较报告.md').read_text()
    for n in ['图1-真实温度与输入', '图2-原生资格与初始化覆盖', '图3-时间敏感性与比较边界']:
        report = re.sub(r'!\[图\d\]\([^\n]*' + re.escape(n) + r'\.png\)', '![' + n[:2] + '](' + n + '.png)', report)
    report = report.replace('本轮只在独立研究目录生成派生文件；', '以下边界指原离线研究计算阶段；本次另以文档PR发布脱敏副本。原研究只在独立研究目录生成派生文件；')
    report = report.replace('来源ZIP为18020171字节', '私有原始来源ZIP为18020171字节')
    report = report.replace('CRC及255项成员已再次核对；', '原计算阶段CRC及255项成员已核对；公开复核副本的独立SHA、保留/省略清单见inputs/evidence-public.zip内PUBLIC-DERIVATION.json，不能冒称私有原件；')
    report = report.replace('回执在delivery/portable-replay.json，候选与最终包的代码SHA另核对。', '此段描述私有完整证据包的原验收；本次公开副本的重跑回执另存publication-replay.json，候选与最终包的代码SHA另核对。')
    (original / 'results/TTO-YET610L同步短问答-冻结模型比较报告.md').write_text(report)
    print(json.dumps({'public_study': str(target), 'input_sha256': identity['input_archive_sha256'], 'public_members': len(public_manifest['files']), 'unchanged_input_members': sum(v['unchanged'] for v in evidence['retained'].values()), 'omitted_members': len(evidence['omitted'])}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('private_study', type=Path)
    p.add_argument('new_public_study', type=Path)
    a = p.parse_args()
    prepare(a.private_study, a.new_public_study)
