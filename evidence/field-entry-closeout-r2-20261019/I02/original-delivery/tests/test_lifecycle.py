import copy,importlib.util,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_health_i02',R/'scripts/source_health.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest=json.loads((R/'inputs/Y-manifest.json').read_text());template=json.loads((R/'inputs/source-fixture.json').read_text())
def sample(t=100,seq=1,epoch=1,fresh=True):
 r=copy.deepcopy(template);r.update(mono_s=t,ref=f'test/{t}',connection_epoch=epoch);r['payload']['telemetry_meta'].update(sample_seq=seq,sample_age_ms=0,fresh=fresh);return r
def event(t,reason=None):return {'kind':'boundary' if reason else 'tick','mono_s':t,'payload':None,'ref':f'test/{t}','received_at_utc':'2026-10-18T00:00:00+00:00',**({'reason':reason} if reason else {})}
def replay(rows):return list(m.export_records(copy.deepcopy(manifest),rows))
def value(node):return node['measurement']['TJ_and_rails']
class Lifecycle(unittest.TestCase):
 def test_normal_sequence(self):
  out=replay([sample(),event(100.2),sample(101,2)]);self.assertEqual([value(x)['raw_valid'] for x in out],[True,True,True])
 def test_disconnect_retains_trace_but_invalidates(self):
  out=replay([sample(),event(100.1,'socketio_disconnected'),event(100.2)]);self.assertEqual([value(x)['raw_valid'] for x in out],[True,False,False]);self.assertEqual(value(out[0])['source'],value(out[2])['source'])
 def test_cached_replay_cannot_restore_before_or_during_reconnect(self):
  out=replay([sample(),event(100.1,'socketio_disconnected'),sample(100.2),event(100.3,'socketio_connecting'),sample(100.4,1,2),event(100.5)]);self.assertEqual([value(x)['raw_valid'] for x in out],[True,False,False,False,False,False]);self.assertEqual(value(out[0])['source'],value(out[-1])['source'])
 def test_fresh_new_source_restores_after_reconnect(self):
  out=replay([sample(),event(100.1,'socketio_disconnected'),event(100.2,'socketio_connecting'),sample(100.3,1,2),sample(100.4,2,2)]);self.assertEqual([value(x)['raw_valid'] for x in out],[True,False,False,False,True]);self.assertEqual(value(out[-1])['source']['key'][-1],2)
 def test_late_callback_before_reconnect_does_not_restore(self):
  out=replay([sample(),event(100.1,'socketio_disconnected'),sample(100.2,2),event(100.3,'socketio_connecting'),sample(100.4,3,2)]);self.assertFalse(value(out[2])['raw_valid']);self.assertEqual(value(out[0])['source'],value(out[2])['source']);self.assertTrue(value(out[-1])['raw_valid'])
 def test_invalid_new_source_and_TTL_are_not_bypassed(self):
  out=replay([sample(),event(100.1,'socketio_disconnected'),event(100.2,'socketio_connecting'),sample(100.3,2,2,False),sample(100.4,3,2),event(106)]);self.assertFalse(value(out[3])['raw_valid']);self.assertTrue(value(out[4])['raw_valid']);self.assertFalse(value(out[5])['raw_valid']);self.assertEqual(value(out[4])['source'],value(out[5])['source']);self.assertEqual(value(out[4])['source']['valid_until_mono_s'],105.4)
if __name__=='__main__':unittest.main(verbosity=2)
