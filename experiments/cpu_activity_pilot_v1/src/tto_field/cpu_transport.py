"""Independent diagnostic transport. Arrival logs never update native TTL, gate or model state."""
import asyncio,json,time,shlex
from pathlib import Path
from .support import utc

class Sidecar:
    def __init__(self,config,out,clock,pipeline,evidence,source_duration=1170):
        self.source_duration=source_duration;self.config=config;self.out=out;self.clock=clock;self.pipeline=pipeline;self.ev=evidence
        self.process=None;self.reader=None;self.status='baseline';self.closed=False;self.last_arrival=None;self.last_seq=None;self.domain=None;self.bytes=0;self.started=None
    async def tick(self,now,latest):
        if self.closed:return
        if self.process is None and now>=30:
            self.started=now
            argv=self.config.get('argv')
            if self.config.get('transport')=='existing_ssh_mux':
                socket=self.config['existing_control_socket']
                if not Path(socket).is_socket():self.status='existing_connection_missing';self.closed=True;self.record('connection_missing');return
                check=await asyncio.create_subprocess_exec('ssh','-S',socket,'-O','check',self.config['host'],stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                if await check.wait()!=0:self.status='existing_connection_invalid';self.closed=True;self.record('connection_invalid');return
                bootstrap="import sys,hashlib,json,runpy\np,h,c,ch,g,cmd,d=sys.argv[1:]\nif hashlib.sha256(open(p,'rb').read()).hexdigest()!=h: raise SystemExit('source SHA')\nif hashlib.sha256(open(c,'rb').read()).hexdigest()!=ch: raise SystemExit('config SHA')\nif json.load(open(g))['command_id']!=cmd: raise SystemExit('permission command')\nsys.argv=[p,'--config',c,'--permission',g,'--duration',d]\nrunpy.run_path(p,run_name='__main__')"
                remote=[self.config['remote_python'],'-c',bootstrap,self.config['remote_source_script'],self.config['source_script_sha256'],
                        self.config['remote_source_config'],self.config['source_config_sha256'],self.config['remote_source_permission'],self.config['command_id'],str(self.source_duration)]
                argv=['ssh','-S',socket,'-o','ControlMaster=no','-o','BatchMode=yes','-o','ProxyCommand=false',self.config['host'],shlex.join(remote)]
            if not argv:self.status='missing';self.closed=True;self.record('missing_source');return
            self.process=await asyncio.create_subprocess_exec(*argv,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=65536)
            self.status='running';self.reader=asyncio.create_task(self.receive());self.record('started')
        if self.process:
            if self.reader.done():await self.halt(self.status)
            if now-(self.last_arrival if self.last_arrival is not None else self.started)>1:
                await self.halt('source_stale_or_blocked')
            if latest:
                if self.pipeline.fan_success_times and time.monotonic()-self.pipeline.fan_success_times[-1]>2.5:
                    await self.halt('native_fan_gap_exceeds_original_TTL')
                callback_lag=latest['clock']['generated_at_mono_s']-latest['clock']['observer_input_mono_s']
                if callback_lag>.25:await self.halt('native_callback_delay_budget_exceeded')
                lag=time.monotonic()-latest['clock']['generated_at_mono_s']
                # Use newest arrival vs observer; stale native state cannot be renewed by sidecar.
                if lag>2.5:await self.halt('native_state_delay_exceeds_original_TTL')
    def record(self,event,**extra):
        self.ev.append('sidecar-events.jsonl',dict(event=event,mono_s=self.clock.now(),at_utc=utc(),status=self.status,**extra))
    async def receive(self):
        try:
            while True:
                line=await self.process.stdout.readline()
                if not line:break
                received=time.monotonic();self.last_arrival=self.clock.now();self.bytes+=len(line)
                row=json.loads(line);ident=row['identity'];seq=row['seq'];domain=(ident.get('host'),ident.get('boot_id'),ident.get('source_session'),ident.get('clock'))
                if row.get('schema')!='TTO-CPU-SOURCE-v1' or ident.get('command_id')!=self.config['command_id']:raise ValueError('identity_or_command_mismatch')
                if self.domain is not None and (domain!=self.domain or seq<=self.last_seq):raise ValueError('source_restart_or_sequence_regression')
                self.domain=domain;self.last_seq=seq
                qualified=all(domain) and domain[-1]=='CLOCK_MONOTONIC'
                if not qualified:raise ValueError('source_clock_identity_unknown')
                self.ev.append('cpu-sidecar-arrivals.jsonl',dict(source=row,received_at_mono_s=received,received_at_utc=utc(),receiver_domain=self.clock.domain,
                    decision_generated_mono_s=time.monotonic(),clock_status='source_identified_mapping_unknown' if qualified else 'clock_unknown',
                    command_id=self.config['command_id'],native_run_id=self.pipeline.run_id,evaluation_scope='arrival_side' if qualified else 'unusable_timing',
                    network_latency_s=None,production_observation=False,analysis_only=True))
                resources=row['resources'];elapsed=resources['elapsed_s']
                if (resources['read_duration_s']>.1 or resources['rss_bytes']>64*1024**2 or
                    (elapsed>=5 and resources['cpu_seconds']/elapsed>.05) or
                    (self.clock.now()-self.started>=5 and self.bytes/(self.clock.now()-self.started)>100*1024)):
                    self.status='source_budget_exceeded';self.record('stop_sidecar_only');return
        except (ValueError,KeyError,TypeError) as e:
            self.status='source_invalid';self.record('source_error',error=type(e).__name__)
        finally:
            if self.status=='running':self.status='source_eof';self.record('source_eof')
            if self.process.returncode is None:self.process.terminate()
    async def resource(self,cpu_pct,rss):
        if self.process and not self.closed and (rss>128*1024**2 or (self.clock.now()>35 and cpu_pct is not None and cpu_pct>8)):
            await self.halt('receiver_total_resource_budget_exceeded')
    async def halt(self,reason):
        if self.closed:return
        self.closed=True;self.status=reason;self.record('stop_sidecar_only')
        if self.process and self.process.returncode is None:self.process.terminate()
    async def close(self):
        await self.halt(self.status if self.status!='running' else 'native_run_ending')
        if self.process:
            try:await asyncio.wait_for(self.process.wait(),2)
            except asyncio.TimeoutError:self.process.kill();await self.process.wait()
        if self.reader:
            if not self.reader.done():self.reader.cancel()
            await asyncio.gather(self.reader,return_exceptions=True)
