"""Committed ledger -> real local query socket -> existing Web API state, no HTTP."""
import asyncio
import copy
import json
import time
import pytest
from types import SimpleNamespace

from tto_field.observe_predictions import Ledger
from tto_field.observe_runtime import Consumer
from tto_field.observe_storage import SessionStore
from tto_field.prediction_view import PredictionView, PAGE
from tto_field.web_encoding import SPEC_ID, SPEC
from tto_field.web_publication import Publication
from test_observe_contract import frame, outputs
from test_web_publication import BOOT, web_clock, pubdir, bundle
from tto_web.state import State
from tto_web.source import follow


def journal(root, origin, run='ledger-run-A'):
    view=PredictionView(origin)
    store=SessionStore(root,min_free=0)
    owner=SimpleNamespace(store=store,prediction_view=view)
    ledger=Ledger(lambda stream,row:Consumer.emit(owner,stream,row),
                  dict(run_id=run,model_id='frozen-g2',model_sha256=SPEC['model_sha256'],spec_sha256=SPEC_ID,clock_domain='fixture'))
    def tick(t,epoch=0):
        f=frame(t,epoch=epoch)
        f['identity'].update(run_id=run,model_sha256=SPEC['model_sha256'],spec_sha256=SPEC_ID)
        f['_communication']=dict(measurement=dict(TJ_and_rails=dict(raw_valid=True)))
        ledger.consume(f,t+.001,outputs(),state_status='tracking',wall_clock=dict(utc='2026-10-23T00:00:00Z',mono_s=t+.001))
        view.update(f,dict(observer=dict(phase='tracking')),t+2.5)
        return f
    return store,view,ledger,tick


async def until(check):
    for _ in range(300):
        if check():return
        await asyncio.sleep(.01)
    raise AssertionError('ledger subscription did not synchronize')


@pytest.mark.parametrize('publication_failure',[None,'worker','final_build','final_write','descriptor_write'])
def test_committed_socket_recovery_terminal_scores_and_new_producer(tmp_path,pubdir,publication_failure,monkeypatch):
    async def run():
        origin=time.monotonic()-300
        store,view,ledger,tick=journal(tmp_path/'session',origin)
        for n in range(61):tick(origin+n*5)
        p=Publication(pubdir/'active.json',BOOT,test_replay=True,prediction_view=view).start()
        assert await asyncio.to_thread(p.ready.wait,3)
        p.submit(*bundle(t=origin,run='ledger-run-A'))
        config={'source':{'active_descriptor':str(pubdir/'active.json')},'advisory':{}}
        state=State(config);stop=asyncio.Event()
        task=asyncio.create_task(follow(config,state,stop))
        try:
            await until(lambda:state.packet is not None and state.prediction_cursor==view.cursor and not state.prediction_syncing)
            assert len(state.predictions)==183  # Requires more than one real 128-row page.
            logged=[json.loads(x) for x in (store.root/'predictions.jsonl').read_text().splitlines()]
            g2={x['prediction_id']:x for x in logged if x['method']=='G2-HOLD'}
            assert set(g2)==set(state.predictions)
            for id,row in state.predictions.items():assert row['value_C']==g2[id]['value_C'] and row['ledger_run_id']==g2[id]['run_id']
            before=copy.deepcopy(state.predictions)
            state.disconnect();assert state.predictions==before  # Web loss cannot rewrite scoring.
            task.cancel();await asyncio.gather(task,return_exceptions=True)
            # Same publisher reconnect preserves the accumulated raw and ledger context.
            old_packet=copy.deepcopy(state.packet)
            task=asyncio.create_task(follow(config,state,stop))
            await until(lambda:state.source_connected and not state.prediction_syncing)
            assert state.packet==old_packet and state.predictions==before
            task.cancel();await asyncio.gather(task,return_exceptions=True)
            # A completely fresh Web state recovers all records, not just the latest three.
            state=State(config);task=asyncio.create_task(follow(config,state,stop))
            await until(lambda:state.packet is not None and state.prediction_cursor==view.cursor and not state.prediction_syncing)
            assert state.predictions==before
            if publication_failure:
                def broken_gap():raise RuntimeError('owned publisher failure')
                if publication_failure=='worker':
                    p._gap=broken_gap;p.invalidate()
                    await until(lambda:not p.thread.is_alive())
                else:
                    import tto_field.web_publication as module
                    atomic=module.atomic_json
                    def fail_write(path,row):
                        if publication_failure=='final_write' and path.name=='predictions-final.json' or publication_failure=='descriptor_write' and path.name=='active.json' and row.get('ended'):
                            raise OSError('owned terminal write failure')
                        return atomic(path,row)
                    def fail_final(*args):raise ValueError('owned final generation failure')
                    with monkeypatch.context() as patch:
                        if publication_failure=='final_build':patch.setattr(view,'final',fail_final)
                        else:patch.setattr(module,'atomic_json',fail_write)
                        ledger.finish(time.monotonic())
                        status=await asyncio.to_thread(p.close,completed=True)
                    assert status['worker_stopped'] and status['errors']>0
                meta=json.loads((pubdir/'active.json').read_text())
                assert meta['publication_failed'] and not meta['ended'] and not meta['prediction_final']
                await until(lambda:state.prediction_failed)
                assert not state.prediction_view(45)['records_complete']
                assert state.snapshot()['publication_status']=='failed'
                task.cancel();await asyncio.gather(task,return_exceptions=True)
                state=State(config);task=asyncio.create_task(follow(config,state,stop))
                await until(lambda:state.prediction_failed)
                assert state.snapshot()['publication_status']=='failed'
                assert not state.prediction_view(45)['records_complete'] and not state.snapshot()['forecast']['latest_prediction_ids']
                # The recorder remains writable after the publication worker has died.
                previous=view.cursor;tick(time.monotonic()+5)
                assert view.cursor>previous and (store.root/'predictions.jsonl').stat().st_size>0
                ledger.finish(time.monotonic()+5)
            else:
                end=time.monotonic()
                stop_frame=frame(end,epoch=1)
                stop_frame['identity'].update(run_id='ledger-run-A',model_sha256=SPEC['model_sha256'],spec_sha256=SPEC_ID)
                stop_frame['_communication']=dict(measurement=dict(TJ_and_rails=dict(raw_valid=False)))
                view.update(stop_frame,dict(observer=dict(phase='unavailable')),end)
                packet=list(bundle(t=origin,run='ledger-run-A'));packet[2]['identity']['source_epoch']=1;packet[2]['source_reset']=True
                p.submit(*packet)
                await until(lambda:state.packet is not None and state.packet['source_epoch']==1)
                assert not state.prediction_view(45)['records']  # Live queries cannot cross epochs.
                ledger.finish(end,'source_epoch_changed');assert p.close(completed=True)['worker_stopped']
                await until(lambda:state.prediction_ended and not state.prediction_syncing)
                assert state.snapshot()['source_epoch']==1
                assert state.snapshot()['prediction_history_identity']['source_epoch']==0
                assert state.prediction_view(45)['records']

                task.cancel();await asyncio.gather(task,return_exceptions=True)
                # Start after producer exit: final scores and API identity must still be available.
                state=State(config);task=asyncio.create_task(follow(config,state,stop))
                await until(lambda:state.prediction_ended and state.prediction_cursor==view.cursor)
                assert not any(r['status']=='pending' for r in state.predictions.values())
                response=state.prediction_view(45)
                assert response['records_complete'] and response['records'] and response['sync_status']=='synced'
                assert state.snapshot()['forecast']['latest_prediction_ids']==[]
                assert state.snapshot()['source_epoch']==1 and state.snapshot()['prediction_history_identity']['source_epoch']==0
                assert state.snapshot()['publication_status']=='ended'
                final_elapsed=state.snapshot()['run_elapsed_ms']
                state.refresh(state.prediction_ended_at+7200)
                assert state.snapshot()['run_elapsed_ms']==final_elapsed
                # Invoke the actual API handler in-process; do not start an HTTP service.
                from tto_web.server import app_for
                app=app_for(config,start_source=False,state=state)
                handler=next(r.handler for r in app.router.routes() if r.method=='GET' and r.resource.canonical=='/api/v1/predictions')
                api=json.loads((await handler(SimpleNamespace(query={'horizon_s':'45'}))).text)
                assert api['summary']==response['summary'] and api['records']==response['records']
                scores=[json.loads(x) for x in (store.root/'scores.jsonl').read_text().splitlines()]
                for r in scores:
                    if r['method']=='G2-HOLD' and r['status']=='scored':
                        actual=state.predictions[r['prediction_id']]
                        assert actual['error_C']==r['error_C'] and actual['observed_C']==r['label_value_C']
            old_publisher=p.publisher_id
            old_page=dict(view.page(now=time.monotonic()),boot_id=BOOT,publisher_id=old_publisher)
            other,new_view,new_ledger,new_tick=journal(tmp_path/'next',time.monotonic(),'ledger-run-B')
            new_tick(new_view.origin)
            p=Publication(pubdir/'active.json',BOOT,test_replay=True,prediction_view=new_view).start()
            assert await asyncio.to_thread(p.ready.wait,3)
            p.submit(*bundle(t=new_view.origin,run='ledger-run-B'))
            await until(lambda:state.packet is not None and state.packet['origin_mono_s']==new_view.origin and state.prediction_cursor==new_view.cursor and not state.prediction_syncing)
            assert len(state.predictions)==3 and all(r['ledger_run_id']=='ledger-run-B' for r in state.predictions.values())
            with pytest.raises(ValueError,match='publisher'):
                state.accept_predictions(old_page)
            # Hold a real query reply in flight. Its receiver must retire before
            # the sole lifecycle owner changes State to the next publisher.
            import tto_web.predictions as receiver
            query=receiver.prediction_page;entered=asyncio.Event();retired=asyncio.Event();release=asyncio.Event()
            previous_publisher=p.publisher_id
            async def delayed(directory,cursor,*,ended):
                page=await query(directory,cursor,ended=ended)
                if page['publisher_id']==previous_publisher and not ended:
                    entered.set()
                    try:await release.wait()
                    finally:retired.set()
                return page
            monkeypatch.setattr(receiver,'prediction_page',delayed)
            await until(entered.is_set)
            begin=state.begin_publication
            def ordered_begin(publisher):
                if publisher!=previous_publisher:assert retired.is_set()
                begin(publisher)
            monkeypatch.setattr(state,'begin_publication',ordered_begin)
            new_ledger.finish(time.monotonic());p.close(completed=True);other.close()
            other,new_view,new_ledger,new_tick=journal(tmp_path/'terminal',time.monotonic(),'ledger-run-C')
            try:
                new_tick(new_view.origin)
                p=Publication(pubdir/'active.json',BOOT,test_replay=True,prediction_view=new_view).start()
                assert await asyncio.to_thread(p.ready.wait,3)
                new_ledger.finish(time.monotonic());p.close(completed=True)
                fresh=State(config);fresh_task=asyncio.create_task(follow(config,fresh,stop))
                # The existing owner follows B -> C; only the comparison state is new.
                try:
                    await until(lambda:state.publisher_id==p.publisher_id and fresh.publisher_id==p.publisher_id
                                and state.prediction_ended and fresh.prediction_ended and not state.prediction_syncing)
                    assert len(state.predictions)==3 and state.predictions==fresh.predictions
                    assert state.packet is None and not state.history and not state.model_history
                    assert state.snapshot()['mode']=='ended' and not state.source_connected
                    assert state.snapshot()['forecast']['latest_prediction_ids']==[]
                    restored=state.prediction_view(45)
                    assert restored['records'] and restored['records_complete']
                    assert restored==fresh.prediction_view(45)
                    assert retired.is_set() and not release.is_set()
                    release.set()
                finally:
                    fresh_task.cancel();await asyncio.gather(fresh_task,return_exceptions=True)
            finally:other.close()
        finally:
            stop.set();task.cancel();await asyncio.gather(task,return_exceptions=True)
            p.close();store.close()
    asyncio.run(run())


def test_retention_revision_paging_and_withdrawal_require_new_prediction(tmp_path):
    origin=100.
    store,view,ledger,tick=journal(tmp_path/'session',origin)
    assert view.final(origin)['history_identity'] is None  # Nothing issued: no fabricated historical group.
    for n in range(750):f=tick(origin+n*5)
    now=f['t']+.01
    first=view.page(now=now)
    assert len(first['records'])==PAGE and first['has_more'] and first['cursor']<first['watermark']
    rows={};cursor=0
    while True:
        page=view.page(cursor,now=now)
        assert [r['revision'] for r in page['records']]==sorted(r['revision'] for r in page['records'])
        rows.update((r['prediction_id'],r) for r in page['records']);cursor=page['cursor']
        if not page['has_more']:break
    assert len(rows)<=2163 and all(r['origin_elapsed_ms']>=(now-origin-3600)*1000 for r in rows.values())
    assert first['forecast']['status']=='available'
    old_ids=first['forecast']['latest_prediction_ids']
    f=copy.deepcopy(f);f['t']+=.1;f['_communication']['measurement']['TJ_and_rails']['raw_valid']=False
    view.update(f,dict(observer=dict(phase='unavailable')),f['t']+2.5)
    f['t']+=.1;f['_communication']['measurement']['TJ_and_rails']['raw_valid']=True
    view.update(f,dict(observer=dict(phase='tracking')),f['t']+2.5)
    assert view.page(now=f['t'])['forecast']['status']=='unavailable'
    f=tick(f['t']+5)
    recovered=view.page(now=f['t']+.01)['forecast']
    assert recovered['status']=='available' and set(recovered['latest_prediction_ids']).isdisjoint(old_ids)
    # A score revision of an old ID must be included after an already acknowledged cursor.
    delta=view.page(cursor,now=f['t']+.01)
    assert any(r['origin_elapsed_ms']<(f['t']-origin)*1000 and r['status']=='matched' for r in delta['records'])
    ledger.finish(f['t']);store.close()
