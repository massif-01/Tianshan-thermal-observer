from pathlib import Path
import json,hashlib,zipfile,datetime
R=Path(__file__).resolve().parents[1];files=set()
def add_tree(folder):
 for p in folder.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files.add(p)
for rel in ['scripts','tests','analysis','deliverables','sources/candidate-wheel/tto','work/runtime-024/tto']:
 add_tree(R/rel)
for kind in ['Y-raw','M-raw']:
 run=next((R/'sources'/kind).rglob('observations-0001.jsonl')).parent;add_tree(run)
files.add(next((R/'sources/Y-raw').rglob('requests.jsonl')))
for rel in ['issue-9-live.json','issue-9-comments-live.json']:files.add(R/rel)
for name in ['README.md','00-共同执行合同.md','02-新通讯专项对话-Codex指令.md','04-三线接口与集成.md','05-来源与最短开工路径.md','SOURCE-MANIFEST.json']:files.add(R/'handoff'/name)
for rel in ['components/ts_net/src/ts_http_server.c','components/ts_webui/src/ts_webui_api.c','components/ts_webui/src/ts_ws_subscriptions.c','components/ts_api/src/ts_api.c','components/ts_api/src/ts_api_fan.c','components/ts_drivers/src/ts_fan.c','components/ts_drivers/src/ts_temp_source.c']:files.add(R/'work/TianshanOS'/rel)
for p in list(files):
 if p.suffix=='.zip' or p.name=='archive-verification.json':files.remove(p)
manifest={str(p.relative_to(R)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)}
archive=R/'deliverables/TTO-fan-status-R2-离线证据包.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(files):z.write(p,str(p.relative_to(R)))
 z.writestr('SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 z.writestr('README-EVIDENCE.md','私有通讯调查证据；不要公开上传原记录/配置。\n主报告在deliverables/。包含Y/M原run通讯复算子集、原始匹配TTO源码和诊断候选、16项测试与只读来源摘要。\n默认无真实设备操作；重跑测试只启动127.0.0.1假服务。\n根目录执行 scripts/analyze.py、scripts/phase_analysis.py、tests/loopback.py baseline/candidate、scripts/source_health.py。依赖见analysis/test-environment.txt。\nscripts/verify_sources.py 另需用户原交接包的handoff/inputs ZIP，不重复装入本包。\nTianshanOS仅所列参考源码，不是完整固件构建树；完整原件保留在独立工作目录。\n')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name,item in manifest.items():
  b=z.read(name);assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
receipt={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'crc_ok':True,'files_sha256_verified':len(manifest),'contains_private_evidence':True,'no_device_or_deployment_performed':True}
(R/'deliverables/archive-verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False))
