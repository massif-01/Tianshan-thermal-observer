"""Authorized Issue #1 body/comment and existing PR metadata update, with readback."""
from pathlib import Path
import base64
import datetime
import hashlib
import json
import re
import subprocess
from urllib.parse import quote
ROOT=Path(__file__).absolute().parents[1]
PUB=ROOT/'publication'
REPO='massif-01/Tianshan-thermal-observer'
MARK='<!-- TTO-REF-PREP-v1.0-status -->'

def api(path,method=None,payload=None):
    command=['gh','api','repos/'+REPO+'/'+path]
    if method:command+=['--method',method]
    if payload is not None:
        payload_path=PUB/'last-payload.json';payload_path.write_text(json.dumps(payload,ensure_ascii=False))
        command+=['--input',str(payload_path)]
    return json.loads(subprocess.check_output(command))

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def digest(s):return hashlib.sha256(s.encode()).hexdigest()

def publish():
    clone=Path(json.loads((PUB/'local-checkout.json').read_text())['directory'])
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip()
    assert commit=='722d92bfca2e847052e410e2f55a28fc9aec6661'
    before=api('issues/1');comments=api('issues/1/comments?per_page=100')
    save(PUB/'immediately-before/issue-1.json',before);save(PUB/'immediately-before/comments-1.json',comments)
    original=json.loads((PUB/'before/issue-1.json').read_text())
    assert before['body']==original['body'],'New Issue progress appeared: merge it before writing'
    assert before['state']=='open'
    body=(PUB/'issue-body-ready.md').read_text()
    assert commit in body and '尚未进入main' in body and '26项' in body
    for i in range(6):assert f'### M{i} ' in body
    assert set(re.findall(r'\b[0-9a-f]{64}\b',original['body']))<=set(re.findall(r'\b[0-9a-f]{64}\b',body))
    patched=api('issues/1','PATCH',dict(body=body))
    save(PUB/'after/issue-write-response.json',patched)
    assert patched['body']==body and patched['state']=='open'
    comment=f'''{MARK}
2026-10-14 / TTO-REF-PREP-v1.0 + ADD1：研究目录软件本地完成，等待独立复审。

主参照改为已购YET-610L+K型探头、聚酰亚胺胶带固定同一局部表面的独立连续CSV；人工/红外及稀疏提醒保留备用。通用映射、原CSV/SHA/原行号与值、空值/ERR台账、通道/测点、首末独立时钟锚点、探头移动事件及冻结G2/QS/LP30/LP120独立对照已完成。相邻等温不去重，缺点不插补，不按温度寻优时差，不进入模型/状态/控制。

26项本地检查及20个CLI/检查调用通过；连续CSV240行双通道明确为合成，238个数值、1空值、1行ERR另留拒绝原因；原模型/既有工作树44612份文件SHA未变。**通用软件已完成／真实YET CSV映射待1～2分钟样例／现场测温未执行。** 购买仪表不是物理验证，24°C只绑定旧M。

文档首版[PR #6](https://github.com/{REPO}/pull/6)已被账号massif-01合并，merge `2155178eab40bc1e1ced1f4eef479d1051eba5d2`；本轮执行端未发起合并。ADD1补充已推同一原分支，固定commit [{commit[:7]}](https://github.com/{REPO}/commit/{commit})，尚未进入main；按用户要求不重复建PR。Issue正文已更新ADD1，M0—M5与历史证据保留，Issue不关闭。

本地软件patch、离线日志、连续测温操作卡及实施报告随证据包交回复审；没有设备访问、新负载、部署、模型重训或控制。下一步只需收到真实短CSV后补必要映射与回归，不启动测试对话。'''
    (PUB/'progress-comment-ready.md').write_text(comment+'\n')
    # Re-read before comment mutation. Unknown outcomes can be retried without duplicate comments.
    comments=api('issues/1/comments?per_page=100');tagged=[c for c in comments if MARK in c.get('body','')]
    assert len(tagged)<=1,'Duplicate existing progress markers require reconciliation'
    response=api('issues/comments/'+str(tagged[0]['id']),'PATCH',dict(body=comment)) if tagged else api('issues/1/comments','POST',dict(body=comment))
    save(PUB/'after/comment-write-response.json',response)
    initial_pr=api('pulls/6')
    pr_body=initial_pr['body'] or ''
    addendum=f'''\n\n<!-- TTO-REF-PREP-ADD1-publication -->
ADD1增量：已购YET-610L/K型探头固定表面连续CSV为主路径，人工/红外为备用。通用软件26项本地检查通过；真实CSV格式待1～2分钟样例、现场测温未执行。DEC-020及连续路径说明在同一原分支commit [{commit[:7]}](https://github.com/{REPO}/commit/{commit})。

回读确认本PR首版已由账号massif-01合并（merge `2155178eab40bc1e1ced1f4eef479d1051eba5d2`）；本轮执行端未发起合并。ADD1提交发生在合并之后，**不属于本PR已合并内容，尚未进入main**。按用户“不重复建PR”要求不另建PR；Issue #1正文/进度评论已同步新事实。软件未上传。'''
    if '<!-- TTO-REF-PREP-ADD1-publication -->' not in pr_body:
        save(PUB/'after/pr-metadata-write-response.json',api('pulls/6','PATCH',dict(body=pr_body+addendum)))
    issue=api('issues/1');comments=api('issues/1/comments?per_page=100');pr=api('pulls/6')
    main=api('commits/main');branch=api('git/ref/heads/docs/tto-ref-prep-roadmap-20261014')
    files=api('pulls/6/files?per_page=100');checks=api('commits/'+pr['head']['sha']+'/check-runs')
    for name,value in [('issue-1',issue),('comments-1',comments),('pr-6',pr),('main',main),('branch',branch),('pr-files',files),('pr-checks',checks)]:save(PUB/'after'/(name+'.json'),value)
    assert issue['body']==body and issue['state']=='open'
    tagged=[c for c in comments if MARK in c.get('body','')];assert len(tagged)==1 and tagged[0]['body']==comment
    assert branch['object']['sha']==commit and pr['merged'] and pr['auto_merge'] is None
    allowed=json.loads((PUB/'docs-allowlist.json').read_text());assert {f['filename'] for f in files}==set(allowed)
    contents={}
    for name in allowed:
        data=api('contents/'+quote(name,safe='/')+'?ref='+commit)
        actual=base64.b64decode(data['content']);expected=(clone/name).read_bytes();assert actual==expected
        target=PUB/'after/pushed-documents'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(actual)
        contents[name]=hashlib.sha256(actual).hexdigest()
    patch=subprocess.check_output(['git','diff','a27ddb6f41c887fd9f08d4120f98d97eed31f4d0..HEAD','--',*allowed],cwd=clone)
    (PUB/'docs-only.patch').write_bytes(patch)
    (PUB/'add1-docs-only.patch').write_bytes(subprocess.check_output(['git','show','--format=fuller','--binary',commit],cwd=clone))
    receipt=dict(status='pass',read_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        issue_url=issue['html_url'],issue_body_sha256=digest(body),issue_state=issue['state'],
        progress_comment_url=tagged[0]['html_url'],unique_progress_comments=1,pr_url=pr['html_url'],
        initial_docs_commit=pr['head']['sha'],pr_state=pr['state'],pr_merged=pr['merged'],pr_merged_at=pr['merged_at'],
        pr_merged_by=(pr.get('merged_by') or {}).get('login'),main_sha_at_readback=main['sha'],
        merge_was_executed_by_this_turn=False,auto_merge_enabled=False,new_duplicate_PR_created=False,
        add1_docs_commit=commit,add1_branch=branch['ref'],add1_docs_in_main=False,
        pushed_docs_exact_bytes_verified=contents,merged_PR_files_verified=[f['filename'] for f in files],
        check_runs_count=checks['total_count'],CI_conclusion='no check runs observed; not a CI success claim',
        local_software_published=False,device_access=False)
    save(PUB/'publication-receipt.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':publish()
