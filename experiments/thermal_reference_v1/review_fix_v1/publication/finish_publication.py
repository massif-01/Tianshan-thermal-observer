"""Authorized follow-up links in the existing Issue/comment, then exact remote readback."""
from pathlib import Path
import base64,datetime,hashlib,json,re,subprocess
from urllib.parse import quote
ROOT=Path(__file__).absolute().parent
CLONE=Path('/private/tmp/tto-ref-prep-docs-20261014-wpye8z78')
REPO='massif-01/Tianshan-thermal-observer';PR='https://github.com/'+REPO+'/pull/7'
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=CLONE,text=True).strip()
assert HEAD=='7ab8aca4d86a1f6757fe2866a98a7794f0aca342'

def save(name,value):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def api(path,method=None,payload=None):
 cmd=['gh','api','repos/'+REPO+'/'+path]
 if method:cmd+=['--method',method]
 if payload is not None:
  p=ROOT/'last-payload.json';p.write_text(json.dumps(payload,ensure_ascii=False));cmd+=['--input',str(p)]
 return json.loads(subprocess.check_output(cmd))

issue=api('issues/1');comments=api('issues/1/comments?per_page=100');pr=api('pulls/7')
save('immediately-before/issue.json',issue);save('immediately-before/comments.json',comments);save('immediately-before/pr7.json',pr)
assert issue['state']=='open'
text=issue['body'];prior=text
text=text.replace('/blob/722d92bfca2e847052e410e2f55a28fc9aec6661/',f'/blob/{HEAD}/')
oldline=next(l for l in text.splitlines() if l.startswith('- ADD1文档补充已推到'))
state='已合并' if pr['merged'] else '待审，尚未合并到main'
newline=f'- ADD1原分支提交[722d92b](https://github.com/{REPO}/commit/722d92bfca2e847052e410e2f55a28fc9aec6661)保留。依据本次审查收尾要求，[最小增量文档PR #7]({PR})从当前main补入ADD1及报告文案修正状态，head `{HEAD}`；**{state}**。它不重复PR #6已合并的首轮内容，不含软件，不自动合并或关闭本Issue。'
text=text.replace(oldline,newline,1)
text=text.replace('新软件仍在独立研究目录等待复审','通用工具已获独立审查接受，报告文案修正仍在独立研究目录待复审',1)
text=text.replace('本地26项针对性检查及20个CLI/检查调用通过','ADD1原26项针对性检查及20个CLI/检查调用通过',1)
mark='<!-- TTO-REF-PREP-REVIEW-FIX -->'
assert mark not in text
addition=f'''\n\n### 2026-10-14 独立审查收尾\n\n通用工具获接受。P3生成报告文案已在本地修正：JSON/Markdown/HTML共用结果对象中的来源说明，覆盖零数值、全合成、声明外部测量及混合来源。原26项保留，新增4项后30项通过；20个CLI/检查调用完成。声明外部类别的测试值也是人工构造，不是新现场测温；品牌格式、探头响应与表面/Ts物理对应不因synthetic=false变成已验证。原温度/时间/模型范围/增量/资格逐项一致，旧证据ZIP保持原SHA。\n\n[文档PR #7]({PR})只含四份Markdown增量，当前{state}；代码和修正证据仍本地交复审。真实YET短CSV尚未收到，现场未执行，不启动测试对话、新负载、部署或模型训练。\n\n{mark}\n'''
text+=addition
for i in range(6):assert f'### M{i} ' in text
assert set(re.findall(r'\b[0-9a-f]{64}\b',prior))<=set(re.findall(r'\b[0-9a-f]{64}\b',text))
assert api('issues/1')['body']==prior,'Issue changed during preparation; preserve new progress before retry'
save('after/issue-write-response.json',api('issues/1','PATCH',dict(body=text)))
existing=[c for c in comments if '<!-- TTO-REF-PREP-v1.0-status -->' in c.get('body','')]
assert len(existing)==1
comment=existing[0];comment_text=comment['body']
assert mark not in comment_text
comment_text+=f'''\n\n{mark}\n审查收尾：通用工具已获独立接受；P3文案统一四种来源，原26项加4项回归共30项通过，20个CLI/检查调用完成。false来源类别仅用人工构造数据测试，未取得新YET CSV、未现场测温；数值、时间、模型、资格和旧证据不变。\n\n[最小增量文档PR #7]({PR})补入PR6合并后遗漏的ADD1和本次状态，head `{HEAD}`，当前{state}，不自动合并；软件修正本地待复审。先前“不另建PR”是上轮停止点，本次按用户要求完成最小发布收尾，不重建主Issue或重复首轮文档。'''
save('after/comment-write-response.json',api('issues/comments/'+str(comment['id']),'PATCH',dict(body=comment_text)))
issue=api('issues/1');comments=api('issues/1/comments?per_page=100');pr=api('pulls/7');main=api('commits/main');files=api('pulls/7/files?per_page=100')
assert issue['body']==text and issue['state']=='open'
tagged=[c for c in comments if '<!-- TTO-REF-PREP-v1.0-status -->' in c.get('body','')];assert len(tagged)==1 and tagged[0]['body']==comment_text
assert pr['head']['sha']==HEAD and pr['auto_merge'] is None
allowed=json.loads((ROOT/'final-gate.json').read_text())['files'];assert {f['filename'] for f in files}==set(allowed)
content_sha={}
for name in allowed:
 remote=api('contents/'+quote(name,safe='/')+'?ref='+HEAD)
 data=base64.b64decode(remote['content']);assert data==(CLONE/name).read_bytes()
 p=ROOT/'after/documents'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 content_sha[name]=hashlib.sha256(data).hexdigest()
checks=api('commits/'+HEAD+'/check-runs')
for name,value in [('issue',issue),('comments',comments),('pr7',pr),('main',main),('pr-files',files),('checks',checks)]:save('after/'+name+'.json',value)
(ROOT/'docs-only.patch').write_bytes(subprocess.check_output(['git','diff',pr['base']['sha']+'..'+HEAD,'--',*allowed],cwd=CLONE))
receipt=dict(status='pass',read_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 issue_url=issue['html_url'],issue_state=issue['state'],progress_comment_url=tagged[0]['html_url'],unique_progress_comments=1,
 pr_url=PR,pr_state=pr['state'],pr_merged=pr['merged'],auto_merge_enabled=False,merge_executed=False,
 head=HEAD,base=pr['base']['sha'],branch=pr['head']['ref'],main_sha=main['sha'],
 only_four_Markdown_files=True,files_sha256=content_sha,check_runs_count=checks['total_count'],
 CI_claim='no check runs is not CI success',local_software_published=False,
 current_issue_body_sha256=hashlib.sha256(text.encode()).hexdigest(),
 milestones_and_historical_hashes_preserved=True)
save('publication-receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False))
