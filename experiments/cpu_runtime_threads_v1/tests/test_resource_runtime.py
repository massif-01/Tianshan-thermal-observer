"""Actual sole runtime/collector against owned loopback; deterministic resource counters only."""
import asyncio,collections,json,time,sys
from pathlib import Path
import pytest,psutil
from fake_source import FakeSource
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field import runtime,receiver_resources
from tto_field.support import Clock

@pytest.mark.parametrize('scenario',['high_cpu','high_rss','unknown','normal','later_cpu'])
def test_once_only_baseline_and_native_completion(tmp_path,monkeypatch,scenario):
    async def check():
        async with FakeSource() as server:
            class FastClock(Clock):
                def __init__(self):super().__init__();self.actual_start=time.monotonic()
                def now(self):return 28+8*(time.monotonic()-self.actual_start)
            monkeypatch.setattr(runtime,'Clock',FastClock)
            real_process=psutil.Process;start=time.monotonic()
            class Process:
                def __init__(self,*a,**k):self.p=real_process(*a,**k)
                def __getattr__(self,n):return getattr(self.p,n)
                def cpu_times(self):
                    t=8*(time.monotonic()-start)
                    rate=.2 if scenario=='high_cpu' else .005
                    cpu=rate*t
                    if scenario=='later_cpu' and t>8:cpu+=.20*(t-8)
                    return self.p.cpu_times()._replace(user=cpu,system=0)
                def memory_info(self):
                    m=self.p.memory_info();return m._replace(rss=129*1024**2 if scenario=='high_rss' else 80*1024**2)
            # Unknown is represented as an absent candidate sample without emitting nonfinite JSON.
            if scenario=='unknown':
                monkeypatch.setattr(receiver_resources,'read_sample',lambda now,previous:(dict(mono_s=now,interval_start_mono_s=None,cpu_pct_single_core=None,rss_bytes=None,cpu_times=None,resource_error='TEST_RESOURCE_UNAVAILABLE'),None))
            if scenario!='unknown':monkeypatch.setattr(psutil,'Process',Process)
            # Owned CPU source subprocess, no ssh command or real device call.
            c=load_config(environ={})
            for k in ('orin','tianshan'):c[k]['base_url']=server.url
            c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC loopback')
            b=preview(c,'capability');b.update(command_id='LOCAL-'+scenario,synthetic_loopback_only=True,
                sidecar=dict(command_id='LOCAL-'+scenario,query_target_s=.2,transport='synthetic',argv=[sys.executable,str(Path(__file__).with_name('fake_sidecar.py')),'--command-id','LOCAL-'+scenario]))
            b['authorization'].update(command_id=b['command_id'],explicit_user_start=True,evidence='OWNED LOOPBACK TEST ONLY')
            # Fake source CLI has a positional command, matching its existing test-only contract.
            b['sidecar']['argv']=[sys.executable,'-c',"import sys,time,runpy; original=time.sleep; time.sleep=lambda s:original(s/8); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')",str(Path(__file__).with_name('fake_sidecar.py')),b['command_id']]
            out=tmp_path/'run';s=await runtime.run(c,b,'diagnose',out,duration=60,cpu_pilot=True)
            admission=json.loads((out/'baseline-resource-admission.json').read_text());events=[json.loads(x) for x in (out/'sidecar-events.jsonl').read_text().splitlines()]
            starts=[x for x in events if x['event']=='started'];baseline=[x for x in events if x['event']=='baseline_resource_admission']
            assert len(baseline)==1 and s['reason']=='diagnostic_duration' and s['own_async_tasks_remaining']==0
            assert s['requester_instances_created']==0 and s['native_run_directories']==1 and s['observer_instances_created']==1
            assert not server.posts and not server.model_gets
            if scenario in ('high_cpu','high_rss','unknown'):
                assert not starts and not admission['allowed'] and not (out/'cpu-sidecar-wire.jsonl').exists()
                assert s['sidecar_status'].startswith('baseline_receiver_')
            else:
                assert admission['allowed'] and len(starts)==1
                assert (out/'cpu-sidecar-wire.jsonl').exists()
                if scenario=='later_cpu':assert s['sidecar_status']=='receiver_total_resource_budget_exceeded'
            assert json.loads((out/'thread-policy.json').read_text())['verified']
    asyncio.run(check())
