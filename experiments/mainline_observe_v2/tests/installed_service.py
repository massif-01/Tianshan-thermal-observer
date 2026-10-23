"""Actual installed observe console in a subprocess; this process owns only loopback services."""
import asyncio,json,os,signal,socket,sys,time,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from aiohttp import web
from fake_source import FakeSource
from tto.recordio import read_records

class Mixed(FakeSource):
    async def status(self,r):
        kind=r.match_info['kind'];t=self.elapsed();self.status_gets.append(dict(path=r.path,at_s=t))
        if kind=='fan' and 5<=t<54:return web.Response(status=503)
        value=self.payload(kind)
        if kind=='fan' and 59<=t<61:value['data']['fans'][0]['guard_active']=True
        return web.json_response(value)
    async def tick(self):
        while True:
            if 13<=self.elapsed()<16:
                if self.connections and not self.did_disconnect:
                    self.did_disconnect=True
                    for sid in list(self.connections):await self.sio.disconnect(sid)
            elif self.connections:await self.sio.emit('tegrastats_update',self.packet())
            await asyncio.sleep(1)

async def main(prefix,out):
    out.mkdir();reg=dict(device_id='SYNTHETIC-DEVICE',thermal_config_id='SYNTHETIC-THERMAL',observer_host_id=socket.gethostname(),session_id=str(uuid.uuid4()),expected_platform=dict(family='jetson_thor',soc='tegra264'))
    async with Mixed() as server:
        cfg=dict(orin=dict(base_url=server.url,source_sample_interval_ms=1000,source_interval_evidence='owned fixture 1s'),tianshan=dict(base_url=server.url),storage=dict(data_root=str(out/'unused')))
        c=out/'configuration.json';c.write_text(json.dumps(cfg));r=out/'registration.json';r.write_text(json.dumps(reg))
        preview_cmd=[str(prefix/'bin/tto-observe'),'preview','--config',str(c),'--registration',str(r),'--duration','70']
        pre=await asyncio.create_subprocess_exec(*preview_cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        data,err=await pre.communicate();assert pre.returncode==0,err.decode();(out/'preview.json').write_bytes(data)
        g=json.loads(data)['grant_template'];now=datetime.now(timezone.utc);g.update(explicit_user_start=True,evidence='OWNED LOOPBACK SERVICE, NO REAL DEVICE',self_owned_loopback=True,not_before_utc=(now-timedelta(seconds=1)).isoformat(),expires_at_utc=(now+timedelta(seconds=120)).isoformat())
        grant=out/'grant.json';grant.write_text(json.dumps(g));run=out/'session'
        cmd=[str(prefix/'bin/tto-observe'),'observe','--config',str(c),'--registration',str(r),'--grant',str(grant),'--duration','70','--output',str(run),'--allow-network','--local-loopback']
        with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
            p=await asyncio.create_subprocess_exec(*cmd,stdout=stdout,stderr=stderr)
            try:await asyncio.wait_for(p.wait(),83)
            except asyncio.TimeoutError:p.kill();await p.wait();raise
        assert p.returncode==0,(out/'stderr.log').read_text()
        s=json.loads((run/'summary.json').read_text());pol=json.loads((run/'thread-policy.json').read_text());idx=json.loads((run/'stream-index.json').read_text())
        def rows(name):
            return [x for n in idx['streams'].get('./'+name,[]) for x in read_records(run/n)]
        obs=rows('observations');pred=rows('predictions');scores=rows('scores')
        assert not rows('states')
        origin=json.loads((run/'launch.json').read_text())['clock_start']['mono_before_s']
        gap=[x for x in obs if 8<=x['mono_s']-origin<12 and x['kind']=='orin']
        assert gap and any(x['measurement']['tj'] and x['measurement']['tj']['raw_valid'] and not x['measurement']['last_successful_pwm']['raw_valid'] for x in gap)
        g2=[x for x in pred if x['method']=='G2-HOLD']
        assert any(x['conditional_assumptions']['assumptions'] for x in g2 if x['conditional_assumptions'])
        assert any('long_missing_last_successful_pwm' in x['reason'] for x in g2 if x['reason'])
        assert any('explicit_guard_fault_mode_or_manual_state' in x['reason'] for x in g2 if x['reason'])
        assert any(x['observed_through_mono_s']-origin>62 and x['origin_state_status'] in ('tracking','degraded') for x in pred)
        assert scores and any(x['status']=='scored' for x in scores)
        assert pred and all(x['publication_mode']=='live' and x['issued_at']['mono_s']>=x['measurement_received_mono_s'] for x in pred)
        binding=json.loads((run/'native-binding.json').read_text());assert binding['collector_engine_instance_id']==binding['I02_shared_engine_instance_id']==s['shared_native_engine_id']
        assert s['native_callbacks']==s['I02_processed_views']
        assert pol['verified'] and pol['pid']==s['pid']==s['clock_end']['pid']
        assert s['Requester_count']==s['sidecar_count']==server.posts==server.model_gets==0
        assert s['collector_count']==s['stateful_observer_count']==1 and s['consumer_stopped']
        receipt=dict(scope='actual installed console; owned loopback only, not target field',elapsed_s=s['elapsed_s'],pid=s['pid'],
            native_run_id=s['native_run_id'],same_pid_thread_policy=True,fan_gap_raw_continues=True,quality_remains_expired=True,
            explicit_guard_model_unavailable_raw_continues=True,source_disconnect_recovery=True,long_fan_gap_model_unavailable_raw_continues=True,model_recovery=True,
            observations=len(obs),full_states_persisted=False,predictions=len(pred),mature_scored=sum(x['status']=='scored' for x in scores),
            no_Requester_sidecar_or_inference=True,reason=s['reason'],raw_store_SHA_index='session/files.json',host_target_verified=False)
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':asyncio.run(main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
