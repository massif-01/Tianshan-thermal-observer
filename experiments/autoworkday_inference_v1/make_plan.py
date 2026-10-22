"""Freeze a bounded synthetic workday. This module never constructs a client."""
import hashlib
import json
from pathlib import Path
import random

SEED = 20261022
STAGES = [
    ('background_health', 0, 7200, 'no_added_requests'),
    ('sparse_qa', 7200, 21600, 'single_sparse'),
    ('conversation_clusters', 21600, 28800, 'single_clusters'),
    ('bounded_batch', 28800, 32400, 'single_batch_blocks'),
    ('cooldown', 32400, 36000, 'no_added_requests'),
    ('long_rest', 36000, 64800, 'no_added_requests'),
    ('irregular_mix', 64800, 84600, 'single_mixed'),
    ('final_recovery', 84600, 86400, 'no_added_requests'),
]
TASKS = [
    ('qa_heat', '问答', '请用中文解释为什么计算机芯片在不同负载下温度会不同。避免编造具体设备参数。'),
    ('qa_network', '问答', '请用中文解释网络延迟和吞吐量的区别，举一个日常例子。'),
    ('summary', '摘要', '请概括以下虚构工作记录：上午整理公开文档，午间休息，下午复核表格，最后归档。列出三项关键安排。'),
    ('rewrite', '改写', '请把这句话改写得清晰简洁：在完成对已经整理的文件进行再次检查之后，我们准备开始实施归档工作。'),
    ('code_explain', '代码解释', '只解释、不执行下面的Python代码，并说明结果：values=[2,4,6]; total=sum(v*v for v in values); print(total)。'),
    ('compare', '比较', '请比较列表和集合的用途，给出适合初学者的例子。不要运行代码。'),
    ('outline', '提纲', '请为一篇介绍散热器、空气流动与环境温度关系的科普文章拟一个简短提纲。'),
    ('translation', '翻译', '请将这段非敏感示例译成中文并解释：A clear plan includes work, rest, and a definite stopping time.'),
]

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def plan_digest(plan):
    return digest({k:v for k,v in plan.items() if k != 'plan_sha256'})

def generate():
    rng = random.Random(SEED)
    tasks = [dict(task_id=k, kind=t, messages=[dict(role='user', content=s)]) for k,t,s in TASKS]
    slots = []
    def add(stage, block, at, end, gap):
        if at + 30 > end or len(slots) >= 600:
            return
        slots.append(dict(slot_id=f'W{len(slots)+1:04d}', stage_id=stage, block_id=block,
                          planned_submit_s=at, latest_submit_s=min(at+5, end-30),
                          issue_window_end_s=end, min_gap_after_previous_end_s=gap,
                          task_id=rng.choice(tasks)['task_id']))
    def sparse(stage, start, end, block):
        at = start
        gap = 0
        while at+30 <= end:
            add(stage, block, at, end, gap)
            gap = rng.randint(120,450)
            at += 30+gap
    def clusters(stage, start, end, block):
        at = start
        group = 0
        while at+30 <= end:
            group += 1
            for j in range(rng.randint(4,8)):
                gap = 0 if j == 0 else rng.randint(3,15)
                if j: at += 30+gap
                if at+30 > end: return
                add(stage, f'{block}-g{group}', at, end, gap)
            at += 30+rng.randint(480,1200)
    def batch(stage, start, end, block):
        # Fixed ten-second opportunities; late/busy opportunities are skipped, never queued.
        for at in range(start, end-29, 10):
            add(stage, block, at, end, 0)
    sparse('sparse_qa',7200,21600,'sparse')
    clusters('conversation_clusters',21600,28800,'conversation')
    for i,(start,end) in enumerate([(28800,29160),(29640,30180),(30660,30960)]):
        batch('bounded_batch',start,end,f'batch-{i+1}')
    at=64800;index=0
    while at+30 <= 84600:
        index+=1;kind=rng.choice(['sparse','clusters','batch'])
        length=rng.randint(1800,2700) if kind=='sparse' else rng.randint(1200,1800) if kind=='clusters' else rng.choice([300,360,540])
        end=min(at+length,84600)
        {'sparse':sparse,'clusters':clusters,'batch':batch}[kind]('irregular_mix',at,end,f'mix-{index}-{kind}')
        at=end+rng.randint(480,1200)
    plan=dict(schema='TTO-AUTOWORKDAY-FROZEN-v1', status='OFFLINE_CANDIDATE_NOT_FIELD_AUTHORIZED',
              field_authorized=False, seed=SEED, total_elapsed_seconds=86400,
              health_checkpoint_seconds=7200, last_new_request_latest_s=84570,
              max_concurrency=1, max_submissions=600, max_client_inflight_seconds=18000,
              request_max_tokens=256, request_protocol_budget_seconds=30, unready_grace_seconds=60,
              no_catch_up=True, pause_extends_window=False, cache_policy='unchanged_hit_unknown',
              predictor_reads_future_schedule=False,
              stages=[dict(id=k,start_s=a,end_s=b,workload=w) for k,a,b,w in STAGES], tasks=tasks, slots=slots)
    plan['plan_sha256']=plan_digest(plan)
    return plan

if __name__=='__main__':
    print(json.dumps(generate(),ensure_ascii=False,indent=2))
