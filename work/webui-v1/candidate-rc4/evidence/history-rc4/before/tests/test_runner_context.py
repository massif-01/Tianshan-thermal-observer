import copy
import time
from types import SimpleNamespace
from producer import Producer,web_config
from tto_web.context import TaskContext
from tto_web.state import State


def test_runner_registration_slots_and_protocol_do_not_claim_gpu_idle():
    start=time.monotonic()-20;ctx=TaskContext({'inference':{'model':'registered-model','messages':[{'content':'SECRET PROMPT'}]}},'execute',SimpleNamespace(origin=start))
    ctx.record({'event':'phase_start','mono_s':10,'stage':{'kind':'work','concurrency':2}})
    ctx.record({'event':'request_submit','mono_s':11,'request_id':'one','prompt':'SECRET'})
    ctx.record({'event':'request_submit','mono_s':11,'request_id':'one'})
    ctx.record({'event':'protocol_DONE','mono_s':12,'request_id':'one'})
    assert ctx.snapshot()['context']['active_requests']==1
    ctx.record({'event':'request_end','mono_s':13,'request_id':'one'})
    snapshot=ctx.snapshot()
    assert snapshot['context']['active_requests']==0 and snapshot['context']['client_slots']==4
    assert snapshot['context']['planned_slots']==2 and snapshot['context']['server_running'] is None
    assert 'SECRET' not in str(snapshot)
    p=Producer(start);s=State(web_config());packet=p.step(0);packet['task']=snapshot;s.accept(packet,now=start+20)
    assert s.snapshot()['context']['task_metadata_available'] and s.snapshot()['context']['active_requests']==0
    assert any('GPU状态未确认' in e['reason'] for e in s.events)


def test_unknown_task_and_demand_are_not_zero():
    ctx=TaskContext({},'diagnose',SimpleNamespace(origin=0)).snapshot()['context']
    assert ctx['task_metadata_available'] is False and ctx['active_requests'] is None
    assert ctx['task_model'] is None
