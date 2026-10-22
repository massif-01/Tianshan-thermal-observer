"""Package the checked public study into the repository's report convention."""
from pathlib import Path
import argparse, csv, datetime, difflib, hashlib, io, json, re, shutil, zipfile


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def finalize(private, public, replay, checkout):
    private, public, replay, checkout = map(Path, [private, public, replay, checkout])
    matches = {}
    for p in sorted((private / 'runs/deliverable/results').glob('*')):
        if p.suffix in ['.json', '.jsonl']:
            assert sha(p) == sha(replay / 'results' / p.name), p.name
            matches[p.name] = sha(p)
    assert len(matches) == 15
    assert sha(private / 'runs/deliverable/data.json') == sha(replay / 'data.json')
    completion = json.loads((replay / 'completion.json').read_text())
    tests = (replay / 'tests.log').read_text()
    assert '8 passed' in tests and 'skipped' not in tests and not completion['network_attempts']
    source_files = [p for p in public.rglob('*') if p.is_file() and p.suffix in ['.py', '.c'] and not {'cache', '__pycache__', 'reference-output'}.intersection(p.relative_to(public).parts)]
    runtime_sha = {str(p.relative_to(public)): sha(p) for p in sorted(source_files)}
    receipt = dict(status='pass', checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   command=['python', 'run.py', '--archive', 'inputs/evidence-public.zip', '--output', 'NEW_OUTPUT'],
                   input_archive_sha256=sha(public / 'inputs/evidence-public.zip'),
                   original_private_input_archive_sha256=sha(private / 'inputs/本轮完整原始证据.zip'),
                   tests='8 passed, no skips', network_attempts=[], dynamic_parameter_updates=0,
                   source_SHA256=runtime_sha, scientific_files_byte_exact=matches,
                   native_replayed_data_byte_exact=True, data_sha256=sha(replay / 'data.json'),
                   strict_model_states=completion['legal_model_states'], strictly_time_paired_points=0,
                   model_surface_ranking_valid=False)
    write(public / 'publication-replay.json', receipt)
    for n in ['stage1-freeze.json', 'completion.json', 'tests.log', 'environment-resources.json']:
        b = (replay / n).read_bytes()
        if n.endswith('.json'):
            d = json.loads(b)
            if n == 'environment-resources.json':
                d['executable'] = '<independent-study-python>'
            write(public / 'publication-run' / n, d)
        else:
            (public / 'publication-run' / n).write_bytes(b)
    (public / 'README.md').write_text('''# YET-610L同步短问答：公开复核归档

2026-10-18；run `1ae9a7d7-bec7-4e45-a9d6-4415b4a8dece`。真实CH1 2027条、accepted TJ 1843条；352个原生严格片段最长26.013秒，未达到冻结60秒初始化。三套冻结G2合法状态均为0；严格仪表时钟配对为0，不能给G2/LP30排名或宣布Ts物理验证。全部模型deployable=false。

这是原离线研究的公开复核副本。原研究spec、三模型、33份vendor源文件、全部15份科学结果及native data.json保持身份/数值；基础设施字段脱敏及发布适配独立留痕。没有重训、放宽TTL/质量、设备访问或外部温度纠偏。原spec中禁止Git写入描述原研究阶段，本次文档发布由用户后续另行授权。

## 独立重跑

先解压本归档。使用Python 3.12、C编译器及requirements.txt中的科学库；若缺中文字体，先安装Noto Sans CJK，影响图中文字显示，不改变数值。研究依赖放在独立环境，不安装本归档中的TTO vendor副本，也不修改生产依赖。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --archive inputs/evidence-public.zip --output new-independent-output
```

准备依赖与实际运算分开；run.py运算阶段阻断socket连接、解析、绑定/监听并禁用动态拟合入口。输出目录必须不存在；完整入口核验公开输入ZIP的SHA/CRC/55项成员、三模型和全部vendor SHA，原生回放5319条观察，核对实际CSV逐行原值，生成所有情景/图/报告并执行8项测试。只在新输出和本研究cache写派生文件。资源值是本机离线研究，不是N305现场成绩。

## 内容与身份

- `reference-output/`：本轮原计算结果，包含native data.json、全部15份科学JSON/JSONL、三张PNG/SVG、中文报告及原测试/资源回执；三份状态文件/得分合法为空，空值及拒绝原因均保留。私有路径/执行环境字段仅作发布脱敏。
- `inputs/evidence-public.zip`：公开复核输入。保留本run的全部5319条原始观察、原生事件/评分、真实原CSV和2027行导入记录、阶段/18条请求时间、异常/恢复及测点/时钟文字证据；照片、重复服务检查快照、实测控制脚本和非必要推理正文不发布。它不冒充私有完整原包。
- 内层`PUBLIC-DERIVATION.json`及`provenance/public-input-derivation.json`：逐文件私有原件SHA、公开副本SHA、保留/省略清单。原私有输入ZIP SHA为`c0c3e1895ca9893d90a27559a491093aa4de1209ab1ae317494adc5ef3c94273`，255项已核对。真实原CSV SHA仍为`698c3842216bb34a263ba630a2760aaf9858a6232050de798d5922a47eb15e80`，未改写。
- `provenance/original-*`：原源身份、原完整研究证据ZIP身份、计算前冻结与原计算回执。它们描述原研究，不表示本公开归档逐字节等于私有包。
- `provenance/publication-adaptation.patch`：只调整公开输入SHA读取、回执字段和可移植报告；科学算法/参数/资格不变。归档格式导入脚本原作者私有默认路径改为必填`--tool`；运行入口不依赖此历史导入脚本。
- `publication-replay.json`及`publication-run/`：公开副本重跑8项测试、全部15份科学输出和native data.json与原件逐字节相等的回执；额外的最终ZIP独立解压重跑回执在GitHub报告旁的`analysis/final-archive-replay.json`。
- `research-code.patch`：可在无既有研究目录的干净检出中恢复代码/冻结JSON；不要覆盖已有研究。优先直接在本解压目录运行。
- ZIP顶层`SHA256.json`列出所有发布成员的SHA和字节数；`python -m zipfile -t evidence.zip`可检查CRC。

照片未公开，因此同框钟点的文字观察属于归档记录转述，不是公开照片复审；文字本身也没有建立仪表误差界。时间情景不是误差界，未按温度挑偏移；新环境温度未知，旧M的24°C不迁入。
''')
    chunks = []
    source_paths = source_files + [public / 'README.md', public / 'spec.json', public / 'source-identity.json', public / 'requirements.txt'] + sorted((public / 'models').glob('*.json'))
    for p in sorted(source_paths):
        n = 'experiments/thermal_yet610l_comparison_v1/' + str(p.relative_to(public))
        chunks.append('diff --git a/' + n + ' b/' + n + '\nnew file mode 100644\n')
        chunks.extend(difflib.unified_diff([], p.read_text().splitlines(True), fromfile='/dev/null', tofile='b/' + n))
    (public / 'research-code.patch').write_text(''.join(chunks))
    output = checkout / 'docs/reports/2026-10-18-yet610l-sync-shortqa'
    output.mkdir(parents=True, exist_ok=False)
    (output / 'analysis').mkdir()
    members = {}
    for p in sorted(public.rglob('*')):
        if p.is_file() and not {'cache', '__pycache__'}.intersection(p.relative_to(public).parts) and p.suffix != '.so':
            n = 'thermal_yet610l_comparison_v1/' + str(p.relative_to(public))
            members[n] = {'sha256': sha(p), 'bytes': p.stat().st_size}
    with zipfile.ZipFile(output / 'evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for n in members:
            z.write(public / n.split('/', 1)[1], n)
        z.writestr('SHA256.json', json.dumps({'contract': 'TTO-YET-FROZEN-COMPARE-v1.0-public', 'files': members}, ensure_ascii=False, indent=2) + '\n')
    results = public / 'reference-output/results'
    report = (results / 'TTO-YET610L同步短问答-冻结模型比较报告.md').read_text()
    for p in sorted(results.glob('图*')):
        if p.suffix not in ['.png', '.svg']:
            continue
        dest = output / 'analysis' / p.name
        if p.suffix == '.svg':
            dest.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines()) + '\n')
        else:
            shutil.copyfile(p, dest)
        report = report.replace('](' + p.name + ')', '](analysis/' + p.name + ')')
    report += '''
## 本次项目归档

本页是用户授权发布的脱敏报告，研究阶段的“未提交/未推送”边界保留为历史记录。本PR仅新增报告与归档，不改生产模块、安装器、runner、风扇或旧研究成绩，不部署、不重训、不自动合并。

- [完整公开研究证据与可独立重跑入口](evidence.zip)：代码/patch、冻结spec和三模型、复核输入、完整逐点结果、图、诊断、测试、环境与SHA。解压后从README运行；内部SHA清单区分私有原件和公开副本。
- [科学摘要](analysis/comparison-summary.json)、[阶段覆盖](analysis/model-coverage.json)、[真实CSV映射核对](analysis/actual-CSV-mapping-verification.json)、[唯一固定背景](analysis/fixed-reference.json)、[全部时间情景统计](analysis/surface-phase-sensitivity.json)、[18条请求时间表](analysis/request-summary.csv)。
- [公开副本与原研究逐字节核对](analysis/publication-replay.json)、[最终ZIP独立解压重跑](analysis/final-archive-replay.json)、[发布文件SHA](publication-manifest.json)。

原私有完整研究证据ZIP为20145199字节、SHA `5e5efe9c578c9eca4197ebe2ef48ddebae0451929325076a1e229323262ea975`；本页公开evidence.zip另有独立SHA，不能替代私有原件身份。原CSV、所有科学结果、模型和spec身份保留；照片及基础设施/重复服务材料不上传。时钟文字证据并不等于公开照片复核，仪表误差界仍未知。
'''
    (output / 'analysis-report.md').write_text(report)
    for n in ['comparison-summary.json', 'model-coverage.json', 'actual-CSV-mapping-verification.json', 'fixed-reference.json', 'surface-phase-sensitivity.json']:
        shutil.copyfile(results / n, output / 'analysis' / n)
    shutil.copyfile(public / 'publication-replay.json', output / 'analysis/publication-replay.json')
    with zipfile.ZipFile(public / 'inputs/evidence-public.zip') as z:
        requests = [json.loads(l) for l in z.read('workload-output/requests.jsonl').decode().splitlines()]
    cols = ['question_id', 'phase', 'submitted_at_utc', 'first_model_content_at_utc', 'first_visible_content_at_utc', 'client_end_at_utc', 'duration_seconds', 'finish_reason', 'done', 'status', 'completion_tokens']
    with (output / 'analysis/request-summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        for r in requests:
            w.writerow({**{k: r[k] for k in cols if k != 'completion_tokens'}, 'completion_tokens': r['usage']['completion_tokens']})
    index = checkout / 'docs/reports/README.md'
    s = index.read_text().replace('# 实机采集报告', '# 实机采集与离线研究报告')
    old = '|---|---|---|---|---|'
    row = '| 2026-10-18 | RM-01 Thor与YET-610L局部鳍片接触测温，同步短问答；冻结模型离线复核 | [研究报告](2026-10-18-yet610l-sync-shortqa/analysis-report.md) | [温度与输入](2026-10-18-yet610l-sync-shortqa/analysis/图1-真实温度与输入.png) · [资格覆盖](2026-10-18-yet610l-sync-shortqa/analysis/图2-原生资格与初始化覆盖.png) · [时间边界](2026-10-18-yet610l-sync-shortqa/analysis/图3-时间敏感性与比较边界.png) | [脱敏证据/代码/完整结果](2026-10-18-yet610l-sync-shortqa/evidence.zip) · [请求时间CSV](2026-10-18-yet610l-sync-shortqa/analysis/request-summary.csv) · [发布校验](2026-10-18-yet610l-sync-shortqa/publication-manifest.json) |'
    index.write_text(s.replace(old, old + '\n' + row) + '\nYET-610L本轮真实表面记录2027条、accepted TJ 1843条。352个原生严格片段最长26.013秒，未达到原60秒初始化；三套冻结G2合法状态和严格时钟配对均为0。保留完整不可用结果，不作G2/LP30胜负、Ts物理验证或控制收益结论。\n')
    print(json.dumps({'report_directory': str(output), 'evidence_zip_bytes': (output / 'evidence.zip').stat().st_size, 'evidence_zip_sha256': sha(output / 'evidence.zip'), 'evidence_members': len(members), 'scientific_files_exact': len(matches)}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for n in ['private_study', 'public_study', 'public_replay', 'clean_checkout']:
        p.add_argument(n, type=Path)
    a = p.parse_args()
    finalize(a.private_study, a.public_study, a.public_replay, a.clean_checkout)
