"""One optional single-client scenario, for a future reviewed unified execute integration.
No CLI can invoke live work. Caller owns the existing safety gate, Requester and collector.
"""
import asyncio
import json
import time

PLAN = dict(id='natural-gap-single-recovery-proposed-v1', status='offline_candidate_not_field_authorized',
            trigger='whole approved natural window lacks sustained work or recovery; explicit new approval',
            stages=[dict(kind='background', seconds=300), dict(kind='work', seconds=360, concurrency=1),
                    dict(kind='final_recovery', seconds=480)],
            max_requests=24, max_tokens=256, request_timeout_s=30,
            nominal_seconds=1140, hard_limit_seconds=1500,
            preparation_max_seconds=300, drain_max_seconds=30, cleanup_max_seconds=30,
            requester='reference/requester.py (unmodified accepted Requester)',
            device_id=None, model_profile=None, authorization=None,
            requires_reviewed_unified_execute_integration=True)

async def run(requester, *, gate, stop, emit, now=time.monotonic, sleep=asyncio.sleep):
    """gate() must be the old execute safety decision, including explicit field permission.
    This helper does not establish permission or construct/query a model client.
    1500s is an outer budget including caller's <=300s preparation and <=30s cleanup.
    No retries. Unknown server termination stops all subsequent requests.
    """
    if not gate():
        raise ValueError('existing_execute_gate_not_ready')
    started = now()
    async def wait(seconds):
        until = now() + seconds
        while now() < until:
            if stop() or not gate():
                return False
            await sleep(min(1, until - now()))
        return True
    emit('scenario_start', plan_id=PLAN['id'])
    if not await wait(300):
        emit('scenario_stop', reason='stop_or_gate'); return
    work_end = now() + 360
    for i in range(24):
        if stop() or not gate() or now() + 30 > work_end:
            break
        task = asyncio.create_task(requester.request(f'SUP-{i+1:03d}', timeout_s=30))
        reason = None
        deadline = now() + 30
        while not task.done():
            if stop() or not gate() or now() >= deadline:
                reason = 'stop_or_gate_or_deadline_server_end_unknown'
                task.cancel()
                break
            await sleep(min(1, max(0, deadline-now())))
        try:
            record = await task
        except asyncio.CancelledError:
            record = {'status':'termination_unknown'}
        if reason or record.get('status') != 'completed' or not record.get('done') or record.get('finish_reason') is None:
            emit('scenario_stop', reason=reason or 'protocol_end_unknown_no_retry'); return
    if not await wait(max(0, work_end-now())) or not await wait(480):
        emit('scenario_stop', reason='stop_or_gate'); return
    emit('scenario_end', reason='completed', elapsed_s=now()-started)

if __name__ == '__main__':
    print(json.dumps(PLAN, ensure_ascii=False, indent=2))
