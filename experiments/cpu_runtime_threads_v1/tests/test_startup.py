import asyncio,base64,json,socket,tempfile,time
from pathlib import Path
import pytest
from tto_field import cpu_transport as tr

class Clock:
    domain='SYNTHETIC-LOCAL'
    def now(self):return 30
class Evidence:
    def __init__(self):self.rows=[]
    def append(self,name,row):self.rows.append((name,row))
class Pipeline:run_id='SYNTHETIC-NATIVE';fan_success_times=[]
class Process:
    next_pid=1000000
    def __init__(self,code=None,lines=b'',stderr=b''):
        self.pid=Process.next_pid;Process.next_pid+=1;self.returncode=code;self.done=asyncio.Event();self.terms=0;self.kills=0
        if code is not None:self.done.set()
        self.stdout=asyncio.StreamReader();self.stdout.feed_data(lines);self.stdout.feed_eof()
        self.stderr=asyncio.StreamReader();self.stderr.feed_data(stderr);self.stderr.feed_eof()
    async def wait(self):await self.done.wait();return self.returncode
    def terminate(self):self.terms+=1;self.returncode=-15;self.done.set()
    def kill(self):self.kills+=1;self.returncode=-9;self.done.set()

def packet(seq=1):
    return dict(schema='TTO-CPU-SOURCE-v1',identity=dict(host='SYNTHETIC',boot_id='SYNTHETIC',source_session='SYNTHETIC',clock='CLOCK_MONOTONIC',command_id='C'),seq=seq,resources=dict(elapsed_s=.2,read_duration_s=.001,rss_bytes=1000,cpu_seconds=.001))
def configuration(mux):return dict(transport='existing_ssh_mux',existing_control_socket=str(mux),host='rm01@10.10.99.98',command_id='C',remote_python='/synthetic/python',remote_source_script='/synthetic/source.py',source_script_sha256='FAKE',remote_source_config='/synthetic/cfg.json',source_config_sha256='FAKE',remote_source_permission='/synthetic/permit.json')

@pytest.mark.parametrize('scenario',['check_hangs','stop','deadline','check_fails','normal','source_fails'])
def test_bounded_startup_and_evidence(monkeypatch,scenario):
    async def check():
        with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-') as folder:
            sock=socket.socket(socket.AF_UNIX);path=Path(folder)/'mux';sock.bind(str(path))
            created=[];calls=[];ev=Evidence()
            async def spawn(*argv,**kw):
                calls.append(argv);is_check='-O' in argv
                if is_check:p=Process(5 if scenario=='check_fails' else None if scenario in ('check_hangs','stop','deadline') else 0,stderr=b'E'*5000)
                else:p=Process(7 if scenario=='source_fails' else None,lines=b'' if scenario=='source_fails' else (json.dumps(packet())+'\n').encode(),stderr=b'SOURCE-FAILED' if scenario=='source_fails' else b'')
                created.append(p);return p
            monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
            monkeypatch.setattr(tr,'CHECK_BUDGET_S',.03);monkeypatch.setattr(tr,'STARTUP_BUDGET_S',.1)
            monkeypatch.setattr(tr,'TERM_GRACE_S',.02);monkeypatch.setattr(tr,'KILL_GRACE_S',.02)
            s=tr.Sidecar(configuration(path),Path(folder),Clock(),Pipeline(),ev)
            t=time.monotonic();await s.tick(30,None);assert time.monotonic()-t<.01
            await asyncio.sleep(.005)
            if scenario in ('stop','deadline'):
                await s.halt('user_stop' if scenario=='stop' else 'diagnostic_deadline')
            else:await asyncio.sleep(.06)
            t=time.monotonic();await s.close();assert time.monotonic()-t<.2
            assert s.startup_task.done() and all(p.returncode is not None for p in created)
            if scenario=='check_hangs':assert s.status=='mux_check_timeout'
            if scenario=='stop':assert s.status=='user_stop'
            if scenario=='deadline':assert s.status=='diagnostic_deadline'
            if scenario=='check_fails':assert s.status=='existing_connection_invalid' and len(created)==1
            if scenario=='normal':
                assert any(n=='cpu-sidecar-arrivals.jsonl' for n,r in ev.rows)
                assert 'ProxyCommand=false' in calls[-1] and calls[0][3:5]==('-O','check')
            if scenario=='source_fails':assert any(r.get('returncode')==7 and r.get('child_stage')=='source_start' for n,r in ev.rows)
            stderr=[r for n,r in ev.rows if n=='sidecar-stderr.jsonl'];assert stderr and all(len(base64.b64decode(r['captured_base64']))<=4096 for r in stderr)
            assert any(r['truncated'] for r in stderr)
            assert all(p.pid>=1000000 for p in created) # own child substitutes only, no master object exists
            assert any(r.get('own_tasks_remaining')==0 for n,r in ev.rows if r.get('event')=='cleanup_finished')
            sock.close()
    asyncio.run(check())

def test_invalid_raw_bytes_are_retained_not_analyzed():
    async def check():
        ev=Evidence();s=tr.Sidecar(dict(command_id='C'),Path('/tmp'),Clock(),Pipeline(),ev);s.started=30
        raw=b'not-json-\xff\n';s.process=Process(0,raw)
        await s.receive()
        wire=[r for n,r in ev.rows if n=='cpu-sidecar-wire.jsonl'];assert base64.b64decode(wire[0]['raw_base64'])==raw
        assert not any(n=='cpu-sidecar-arrivals.jsonl' for n,r in ev.rows)
        reject=[r for n,r in ev.rows if r.get('event')=='source_rejected'];assert reject[0]['wire_seq']==wire[0]['wire_seq'] and reject[0]['detail']
    asyncio.run(check())

def test_legacy_helper_latest_invalid_revokes_old():
    from tto_field.cpu_interface import causal_inputs
    valid=dict(field='cpu_max_percent',value=42,valid=True,clock_domain='R',observed_window_end_s=10.,available_at_s=10.,decision_generated_s=10.)
    invalid=dict(valid,valid=False,available_at_s=10.3,decision_generated_s=10.3,error='counter_reset')
    result=causal_inputs([valid,invalid],10.5,'R')
    assert result['INPUT-CORE']['cpu_max_percent'] is None
    recovered=dict(valid,value=40,observed_window_end_s=10.6,available_at_s=10.7,decision_generated_s=10.7)
    assert causal_inputs([valid,invalid,recovered],10.8,'R')['INPUT-CORE']['cpu_max_percent']['value']==40

def test_owned_real_child_timeout_and_stderr(tmp_path,monkeypatch):
    import sys
    async def check():
        with tempfile.TemporaryDirectory(dir='/private/tmp',prefix='cpu2-child-') as folder:
            path=Path(folder)/'mux';sock=socket.socket(socket.AF_UNIX);sock.bind(str(path));original=asyncio.create_subprocess_exec
            async def own_child(*argv,**kw):
                assert argv[0]=='ssh' and '-O' in argv
                return await original(sys.executable,'-c',"import sys,time;sys.stderr.write('LOCAL SYNTHETIC MUX CHILD\\n');sys.stderr.flush();time.sleep(30)",**kw)
            monkeypatch.setattr(asyncio,'create_subprocess_exec',own_child);monkeypatch.setattr(tr,'CHECK_BUDGET_S',.1)
            ev=Evidence();s=tr.Sidecar(configuration(path),tmp_path,Clock(),Pipeline(),ev)
            await s.tick(30,None);await s.startup_task;await s.close()
            assert s.status=='mux_check_timeout' and len(s.owned)==1 and s.owned[0][1].returncode is not None
            stderr=[r for n,r in ev.rows if n=='sidecar-stderr.jsonl'];assert b'LOCAL SYNTHETIC MUX CHILD' in base64.b64decode(stderr[0]['captured_base64'])
            sock.close()
    asyncio.run(check())
