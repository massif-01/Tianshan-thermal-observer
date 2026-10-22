from pathlib import Path
import shutil,json,hashlib,re,zipfile
P=Path(__file__).parent
out=Path('/private/tmp/tto-shortqa-share-d2a7593a-v2');out.mkdir(exist_ok=False)
run=next(P.glob('run-*'));keep=[P/'TTO-第二轮补充与短问答实测报告.md',P/'第二轮核对与补充说明.md',P/'round2-verification.json',P/'round2-resource-verification.json',P/'input-package-checks.json',P/'01-Codex执行指令.md',P/'02-短问答题目.json',P/'normalized-requests.json',P/'normalized-phases.json',P/'collection-stop-state.json',P/'verify-round2.py',P/'firmware-ready.json',P/'fan-ready.json',P/'temp-ready.json',P/'readiness.json']
keep+=list(run.iterdir())+list((P/'analysis').iterdir())+[f for f in (P/'workload').iterdir() if f.is_file() and not f.name.endswith('metrics.txt')]
session=P/'tto-short-qa-v1-20261013-052807'
for name in ['settings.json','collector-worker.py','runtime-identity.json','private-current-config.json','collection.log','report.log','worker.log']:
 if (session/name).exists():keep.append(session/name)
orig={};redacted=[]
def redact(text):
 for old,new in [('10.10.99.98','compute-host'),('10.10.99.99','observer-host'),('10.10.99.97','board-host'),('/Users/massif','/workspace'),('/home/rm01','/home/observer')]:text=text.replace(old,new)
 return text
for f in keep:
 if not f.is_file():continue
 rel=f.relative_to(P);target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);blob=f.read_bytes();orig[str(rel)]=hashlib.sha256(blob).hexdigest()
 if f.suffix in ['.json','.jsonl','.csv','.md','.py','.txt','.log','.svg']:
  txt=blob.decode();revised=redact(txt).encode()
  if revised!=blob:redacted.append(str(rel))
  blob=revised
 target.write_bytes(blob)
for name in ['findings.json','phase-fan-snapshots.json']:
 f=Path('/private/tmp/tto-short-qa-v1-package/reference/independent/results')/name;q=out/'reference'/name;q.parent.mkdir(exist_ok=True);q.write_text(redact(f.read_text()))
source_idx=json.loads((run/'files.json').read_text());(out/'original-run-file-hashes.json').write_text(json.dumps(source_idx,indent=2)+'\n')
q=out/run.name;idx={n:hashlib.sha256((q/n).read_bytes()).hexdigest() for n in source_idx};(q/'files.json').write_text(json.dumps(idx,indent=2)+'\n')
receipt={'run_id':'d2a7593a-e68a-4b6f-9d4d-875fafa73c02','old_run_reference':'929742d7-6f4d-4d80-b53e-4436d45ac12c','raw_originals_preserved':True,'original_run_index_passed':8,'new_share_is_sanitized_copy':True,'redacted_files':redacted,'original_selected_file_sha256':orig,'scope':'Only new run and added old-analysis verification; no old full dataset, credentials or private address list.','manifest_note':'Source manifest and config_sha256 describe original executed private configuration. Address aliases are redaction, not executed endpoint changes. Share files.json indexes redacted copy; original-run-file-hashes.json indexes untouched original.'}
(out/'sanitization-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
(out/'README.md').write_text('''# TTO短问答最小证据包

首先阅读《TTO-第二轮补充与短问答实测报告.md》。新run、19次逐请求/SSE、167个任务事件、冻结题目/参数、脚本、现场身份、完整统计和图表均保存。

这是脱敏副本，原始私人记录在采集设备及工作区保持不变。compute-host、observer-host、board-host是非路由地址别名，未附私有地址清单。路径也已改为通用标识。运行脚本若需要复用，应按原用户已知端点映射恢复；不得凭别名直接执行。原始manifest中的配置SHA是执行时原配置身份，不是脱敏配置SHA；两套文件索引分别保存，不能误当成原件完全相同。

旧run只引用身份、哈希、核对说明及少量峰值/异常上下文，不包含旧七工况全套原始证据。verify-round2.py的复核需要用户另有的旧原run和独立补充；不以新数据替代旧数据。

新统计由analysis/normalize.py、analyze-shortqa.py生成；plot-shortqa.py需要matplotlib。报告含人工审阅的语义/异常说明。原1秒/5秒采样、AUTO、曲线、保护、功耗模式及源服务未调整。用户基础曲线待合并。不得将本包当训练结果或独立因果A/B。
''')
for f in out.rglob('*'):
 if f.is_file() and f.suffix in ['.json','.jsonl','.csv','.md','.py','.txt','.log','.svg']:
  txt=f.read_text();assert not re.search(r'(?<![\w.])(?:10|192\.168)\.\d+\.\d+(?:\.\d+)?',txt),f
  assert 'pwd:rm01' not in txt and 'SSH_ASKPASS' not in txt and 'PRIVATE KEY-----' not in txt,f
hashes={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.rglob('*') if f.is_file()}
(out/'SHA256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
archive=Path('/Users/massif/Tianshan-thermal-observer/deliverables/TTO-短问答实测证据包-20261013-d2a7593a.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in out.rglob('*'):
  if f.is_file():z.write(f,str(f.relative_to(out)))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 hashes=json.loads(z.read('SHA256.json'));assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in hashes.items())
print(json.dumps({'archive':str(archive),'size_bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files_checked':len(hashes),'redacted_files':len(redacted)},ensure_ascii=False))
(P/'evidence-package-receipt.json').write_text(json.dumps({'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files_checked':len(hashes),'size_bytes':archive.stat().st_size},indent=2)+'\n')
