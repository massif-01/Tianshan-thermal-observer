"""O1/O2 actual consumer retention and installed CLI against the real session store."""
import copy,json,subprocess,sys
from pathlib import Path
from tto_field.observe_storage import SessionStore
from tto_field.projection import SavedStream


def test_quality_history_policy_preserves_frames():
    # Small direct policy check; the independent 86400-row probe uses the real native engine.
    from tto.engine import engine_for
    from tto.config import load_config
    from tto_field.g2_model.g2_runtime import Predictor
    config=load_config(environ={})
    manifest={'config':config,'observer_run_id':'synthetic-policy-unit','config_sha256':'synthetic','source_identity':{'sha256':'synthetic'}}
    spec=Predictor().spec
    old=SavedStream(manifest,spec,engine_for(config,record_schema=2))
    live=SavedStream(manifest,spec,engine_for(config,record_schema=2),retain_quality_history=False)
    processed={'quality':{'accepted':False,'reason':'synthetic_test'}}
    for n in range(10):
        raw=dict(mono_s=float(n),kind='boundary',reason='test',ref=str(n),received_at_utc='2026-10-21T00:00:00Z')
        assert old.feed(raw,copy.deepcopy(processed))==live.feed(raw,copy.deepcopy(processed))
    assert old.retain_quality_history and len(old.quality)==old.quality_seen==10
    assert live.quality_seen==10 and live.quality==[] and not live.retain_quality_history


def test_installed_live_history_equals_closed_across_fragments(tmp_path):
    store=SessionStore(tmp_path/'session',budget=1000000,segment_bytes=100000,chunk_bytes=160,min_free=0)
    for name in ('states','predictions','observations'):
        for n in range(20):store.append(store.root,name,dict(n=n,example='synthetic-only'))
    # The former prefix glob must not pull a different logical stream into the query.
    (store.root/'states-extra.jsonl').write_text('{"n":999}\n')
    files_before={p.name:p.read_bytes() for p in store.root.glob('*.jsonl')}
    def query(name,last):
        p=subprocess.run([str(Path(sys.executable).with_name('tto-observe')),'history','--session',str(store.root),'--stream',name,'--last',str(last)],capture_output=True,text=True,check=True,timeout=10)
        return [x['n'] for x in json.loads(p.stdout)]
    live={(name,last):query(name,last) for name in ('states','predictions','observations') for last in (3,7,25)}
    assert all(rows==list(range(max(0,20-last),20)) for (name,last),rows in live.items())
    assert files_before=={p.name:p.read_bytes() for p in store.root.glob('*.jsonl')}
    store.close()
    assert live=={(name,last):query(name,last) for name,last in live}
    # Number ordering remains correct beyond four digits, with no full-index dependency.
    numeric=tmp_path/'numeric';numeric.mkdir()
    for filename,n in [('states.jsonl',1),('states-9999.jsonl',9999),('states-10000.jsonl',10000)]:
        (numeric/filename).write_text(json.dumps({'n':n})+'\n')
    p=subprocess.run([str(Path(sys.executable).with_name('tto-observe')),'history','--session',str(numeric),'--stream','states','--last','2'],capture_output=True,text=True,check=True,timeout=10)
    assert [x['n'] for x in json.loads(p.stdout)]==[9999,10000]
