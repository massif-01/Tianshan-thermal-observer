"""Own Socket.IO/HTTP service -> original native/state + real source.stream -> real Sidecar.receive."""
import asyncio,hashlib,json,sys
from pathlib import Path
from fake_source import FakeSource
from tto.config import load_config
from tto_field.cpu_cli import preview
from tto_field.runtime import run
from tto_field.support import write

class SignalSource(FakeSource):
    def packet(self):
        p=super().packet();p['gpu']['utilization_pct']=99
        p['power']['vdd_gpu']['current']=30000;p['power']['vdd_cpu_soc_mss']['current']=18000
        return p
    async def tick(self):
        while True:
            if self.elapsed()>=40 and not self.did_disconnect:
                self.did_disconnect=True
                for sid in list(self.connections):await self.sio.disconnect(sid)
            self.silent=40<=self.elapsed()<43
            if self.connections and not self.silent:await self.sio.emit('tegrastats_update',self.packet())
            await asyncio.sleep(1.)

async def main(out):
    out.mkdir(parents=True,exist_ok=False)
    async with SignalSource() as service:
        c=load_config(environ={})
        for k in ('orin','tianshan'):c[k]['base_url']=service.url
        c['orin'].update(source_sample_interval_ms=1000,source_interval_evidence='SYNTHETIC own 1s service timer')
        b=preview(c,'capability');command='SYNTHETIC-CPU2-JOINT-20261020';b.update(command_id=command,synthetic_loopback_only=True)
        b['authorization'].update(command_id=command,explicit_user_start=True,evidence='OWN SYNTHETIC SERVICES; NO DEVICE PERMISSION')
        b['sidecar']=dict(query_target_s=.2,command_id=command,argv=[sys.executable,str(Path(__file__).with_name('source_fixture.py').resolve()),str((out/'synthetic-proc').resolve()),command],synthetic=True)
        write(out/'source-config.json',dict(synthetic=True,query_target_s=.2,nvml=False,rails=[],cpu_fixture='two synthetic cores, cumulative ticks, reset7s, offline9..11s, actual serializer',coarse_native_disconnect_gap_session_s=[40,43]))
        result=await run(c,b,'diagnose',out/'run',duration=60,cpu_pilot=True)
        assert service.posts==service.model_gets==result['requester_instances_created']==0
        rows=[json.loads(x) for x in (out/'run/cpu-sidecar-arrivals.jsonl').read_text().splitlines()]
        assert len(rows)>=100
        assert all(x['source'].get('raw_cpu') and x['source']['identity']['command_id']==command for x in rows)
        assert any(x['source']['cpu'] and not x['source']['cpu']['complete_online_set'] for x in rows)
        assert {x['native_run_id'] for x in rows}=={result['native_run_id']}
        assert result['native_run_directories']==1 and result['observer_instances_created']==1 and result['own_async_tasks_remaining']==0
        write(out/'sample-receipt.json',dict(synthetic=True,device_connections=0,inference_POSTs=service.posts,model_queries=service.model_gets,source_packets=len(rows),native_run_id=result['native_run_id'],actual_sender='cpu_source.stream/read_cpu/utilization with synthetic proc filesystem only',actual_receiver='Sidecar.receive',native_source='original collector via own FakeSource',source_code_sha256=hashlib.sha256(Path(__import__('tto_field.cpu_source',fromlist=['__file__']).__file__).read_bytes()).hexdigest(),receiver_code_sha256=hashlib.sha256(Path(__import__('tto_field.cpu_transport',fromlist=['__file__']).__file__).read_bytes()).hexdigest()))
        print(json.dumps(dict(packets=len(rows),run=result['native_run_id'],reason=result['reason']),indent=2))
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve()))
