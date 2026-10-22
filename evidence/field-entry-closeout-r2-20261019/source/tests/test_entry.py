import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tto_field.cli import preview,main
from tto_field.gate import readiness
from tto_field.runtime import verify_grant
from tto_field.support import Evidence
from tto_field.scheduler import Registry
from tto.storage import InstanceLock
from tto.config import load_config

class EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ['TTO_TEST_STATE_FILE'])
        cls.env=next(json.loads(x) for x in path.read_text().splitlines() if json.loads(x)['state']['observer']['phase']=='tracking')
        cls.now=cls.env['clock']['generated_at_mono_s']-cls.env['clock']['session_origin_mono_s']+.05
        cls.run_id=cls.env['native_run_id']
    def test_async_generated_not_equal_now_is_usable(self):
        self.assertTrue(readiness(self.env,self.now,self.run_id)['start_allowed'])
    def test_no_more_messages_expire_without_feed(self):
        g=readiness(self.env,self.now+20,self.run_id)
        self.assertFalse(g['collection_available']);self.assertFalse(g['model_available']);self.assertFalse(g['start_allowed'])
    def test_mismatched_clock_domain(self):
        e=copy.deepcopy(self.env);e['clock']['domain']='OTHER-HOST'
        self.assertFalse(readiness(e,self.now,self.run_id)['start_allowed'])
    def test_finite_model_does_not_override_expired_pwm(self):
        e=copy.deepcopy(self.env);e['state']['measurement']['last_successful_pwm']['valid_until_mono_s']=self.now+e['clock']['session_origin_mono_s']-.1
        g=readiness(e,self.now,self.run_id);self.assertTrue(g['model_available']);self.assertFalse(g['start_allowed'])
    def test_unknown_safety_is_not_normal(self):
        e=copy.deepcopy(self.env);e['state']['safety']['guard']=None
        self.assertFalse(readiness(e,self.now,self.run_id)['field_safety_available'])
    def test_provisional_finite_is_not_ready(self):
        e=copy.deepcopy(self.env);e['state']['observer']['phase']='provisional'
        self.assertFalse(readiness(e,self.now,self.run_id)['model_available'])
    def test_model_permission_not_authority(self):
        e=copy.deepcopy(self.env);e['binding']['authorization']['explicit_user_start']=False;e['state']['permission']['formal_field_authorized']=True
        self.assertFalse(readiness(e,self.now,self.run_id)['execution_authorized'])
    def test_diagnostic_can_never_emit_load(self):
        e=copy.deepcopy(self.env);e['mode']='diagnose'
        self.assertFalse(readiness(e,self.now,self.run_id)['execution_authorized'])
    def test_preview_no_socket_or_credential_reads(self):
        c=load_config(environ={})
        with patch('socket.socket',side_effect=AssertionError('network')),patch('tto.config.headers',side_effect=AssertionError('credentials')):
            r=preview(c,'diagnose')
        self.assertFalse(r['authorization']['explicit_user_start'])
    def test_run_requires_network_flag_before_clients(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json';p.write_text('{}')
            with patch('socket.socket',side_effect=AssertionError('network')):
                with self.assertRaises(SystemExit):main(['diagnose','--config',str(p),'--binding','missing','--output',str(Path(td)/'out')])
    def test_current_command_only_and_no_old_override(self):
        c=load_config(environ={});b=preview(c,'diagnose');b['command_id']='CURRENT';b['authorization'].update(command_id='OLD',explicit_user_start=True,evidence='test')
        with self.assertRaisesRegex(ValueError,'current command'):verify_grant(c,b,'diagnose',300)
        b['old_overrides']=True
        with self.assertRaisesRegex(ValueError,'old overrides'):verify_grant(c,b,'diagnose',300)
    def test_lifetime_lock_and_permanent_command_claim(self):
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'lock'
            with InstanceLock(lock):
                with self.assertRaises(ValueError):
                    with InstanceLock(lock):pass
            registry=Registry(Path(td)/'ledger');registry.claim('run','command')
            with self.assertRaises(FileExistsError):registry.claim('run','command')
    def test_wrong_runtime_import_is_rejected(self):
        from tto_field.identity import verify
        with patch('tto.__file__','/tmp/foreign/tto/__init__.py'):
            with self.assertRaisesRegex(ValueError,'outside the isolated'):verify()
    def test_threaded_evidence_counter(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as td:
            ev=Evidence(td)
            def f(k):
                for x in range(100):ev.append(str(k)+'.jsonl',{'row':x})
            with ThreadPoolExecutor(2) as pool:list(pool.map(f,[0,1]))
            ev.close();self.assertEqual(ev.bytes,sum(p.stat().st_size for p in Path(td).iterdir()))

if __name__=='__main__':unittest.main(verbosity=2)
