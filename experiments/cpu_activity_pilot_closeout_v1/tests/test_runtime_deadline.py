"""Actual sole runtime checks STOP/diagnostic deadline while owned mux child never exits."""
import asyncio,json,socket,tempfile,time
from pathlib import Path
import pytest
from fake_source import FakeSource
from test_startup import Process,configuration
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field import runtime
from tto_field.support import Clock,write

@pytest.mark.parametrize('reason',['user_stop','diagnostic_duration'])
def test_clock_loop_keeps_advancing(tmp_path,monkeypatch,reason):
    async def check():
        async with FakeSource() as server:
            with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-loop-') as short:
                sock=socket.socket(socket.AF_UNIX);path=Path(short)/'mux';sock.bind(str(path));children=[]
                async def spawn(*argv,**kw):
                    assert argv[0]=='ssh' and '-O' in argv
                    p=Process(None);children.append(p);return p
                monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
                class OffsetClock(Clock):
                    def __init__(self):super().__init__();self.origin-=30 if reason=='user_stop' else 59.8
                monkeypatch.setattr(runtime,'Clock',OffsetClock)
                c=load_config(environ={})
                for key in ('orin','tianshan'):c[key]['base_url']=server.url
                c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC only')
                b=preview(c,'capability');b.update(command_id='FAKE-'+reason,synthetic_loopback_only=True,sidecar=configuration(path))
                b['sidecar'].update(command_id=b['command_id'],query_target_s=.2)
                b['authorization'].update(command_id=b['command_id'],explicit_user_start=True,evidence='LOCAL SIMULATED RUNTIME ONLY')
                out=tmp_path/'run'
                async def stop():await asyncio.sleep(.2);(out/'STOP').touch()
                task=asyncio.create_task(stop()) if reason=='user_stop' else None
                start=time.monotonic();result=await runtime.run(c,b,'diagnose',out,duration=60,cpu_pilot=True)
                if task:await task
                elapsed=time.monotonic()-start
                assert elapsed<3 and result['reason']==reason and result['requester_instances_created']==0
                assert children and all(p.returncode is not None for p in children)
                events=[json.loads(x) for x in (out/'sidecar-events.jsonl').read_text().splitlines()]
                assert any(x['event']=='cleanup_finished' and x['own_tasks_remaining']==x['unreaped_children']==0 for x in events)
                assert not server.posts and not server.model_gets
                write(tmp_path/'verification.json',dict(reason=reason,wall_elapsed_s=elapsed,mux_wait_never_returns=True,own_children_reaped=True,real_devices=0,real_inference=0))
                sock.close()
    asyncio.run(check())
