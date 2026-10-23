import asyncio
import copy
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
import pytest
from aiohttp import web
from tto_web.server import app_for
from tto_web.state import State
from tto_web.source import Publication
from producer import Producer,web_config,seed_predictions


@pytest.mark.asyncio
async def test_slow_display_queue_resync_is_bounded_without_source_backpressure():
    state=State(web_config());app=app_for(web_config(),start_source=False,state=state)
    runner=web.AppRunner(app);await runner.setup()
    queue=asyncio.Queue(maxsize=8);app['sse_clients'].add(queue)
    for i in range(8):queue.put_nowait(('old','snapshot',{}))
    await asyncio.sleep(1.15)
    assert queue.qsize()<=8 and state.dropped>=1
    items=[]
    while not queue.empty():items.append(queue.get_nowait())
    assert any(item[1]=='resync' for item in items)
    app['sse_clients'].remove(queue);await runner.cleanup()


def test_snapshot_cost_does_not_copy_all_prediction_history():
    p=Producer(time.monotonic()-120);s=State(web_config())
    for t in range(121):s.accept(p.step(t),now=p.start+t+.01)
    seed_predictions(s,p.step(121),range(0,120001,5000))
    # Count traversal copies directly: the snapshot must contain only six forecast summaries.
    snapshot=s.refresh(p.start+120.01)
    assert len(snapshot['predictions'])==6
    assert len(s.predictions)==75 and s.events.maxlen==1000


def test_late_and_cross_epoch_not_error_denominators():
    p=Producer(time.monotonic()-120);s=State(web_config())
    for t in range(121):s.accept(p.step(t),now=p.start+t+.01)
    seed_predictions(s,p.step(121))
    current=list(s.predictions.values())[-2]
    late=copy.deepcopy(current);late.update(prediction_id='late',origin_elapsed_ms=0,target_elapsed_ms=45000,status='late_publication')
    before=s.prediction_view(45)['summary'];s.predictions[late['prediction_id']]=late;after=s.prediction_view(45)['summary']
    assert after['late_publication_count']==before['late_publication_count']+1
    assert after['due_count']==before['due_count'] and after['matched_count']==before['matched_count']


def test_publication_path_error_is_explicit(tmp_path):
    pub=Publication(tmp_path/('x'*100)/'active.json')
    async def check():
        with pytest.raises(ValueError,match='短路径'):await pub.__aenter__()
    asyncio.run(check())


@pytest.mark.asyncio
async def test_prediction_delta_preserves_whole_window_denominator_and_recent_label_updates():
    p=Producer(1000.);p.step(0);s=State(web_config());packet=p.step(110)
    s.accept(packet,now=p.start+110.01)
    page=seed_predictions(s,packet,[0,110000])
    cached={r['prediction_id']:r for r in s.prediction_view(45)['records']}
    revised=copy.deepcopy(page);score=revised['records'][1]
    score.update(status='matched',observed_C=47.,error_C=1.,settled_elapsed_ms=45000,revision=7)
    backfill=copy.deepcopy(score)
    backfill.update(prediction_id='BACKFILLED-45',origin_elapsed_ms=5000,issued_elapsed_ms=5000.01,
                    input_cutoff_elapsed_ms=5000,target_elapsed_ms=50000,settled_elapsed_ms=52001,
                    status='missing_label',reason_code='missing_qualified_label_within_2s',observed_C=None,error_C=None,revision=8)
    revised.update(records=[score,backfill],cursor=8,watermark=8)
    s.accept_predictions(revised,now=p.start+111.01)
    app=app_for(web_config(),start_source=False,state=s)
    handler=next(r.handler for r in app.router.routes() if r.method=='GET' and r.resource.canonical=='/api/v1/predictions')
    delta=json.loads((await handler(SimpleNamespace(query={'horizon_s':'45','from':'0','records_after':'110010'}))).text)
    complete=s.prediction_view(45,0,111010)
    cached.update({r['prediction_id']:r for r in delta['records']})
    assert cached=={r['prediction_id']:r for r in complete['records']}
    assert cached[score['prediction_id']]['settled_elapsed_ms']==45000
    assert delta['summary']==complete['summary'] and delta['summary']['matched_count']==1
    assert delta['records_complete'] is False
    assert complete['records_complete'] is True
    # Re-delivering the same revision cannot make it a new change again.
    s.accept_predictions(revised,now=p.start+112.01)
    later=s.prediction_view(45,0,112010,records_after=111011)
    assert not {score['prediction_id'],backfill['prediction_id']} & {r['prediction_id'] for r in later['records']}


def test_lost_publication_does_not_call_next_available_tj_the_first_label():
    p=Producer(time.monotonic()-20);s=State(web_config())
    for t in range(13):s.accept(p.step(t),now=p.start+t+.01)
    seed_predictions(s,p.step(13))
    earlier=copy.deepcopy(s.predictions)
    packet=p.step(15);packet['publication_gap']=True;s.accept(packet,now=p.start+15.01)
    assert s.predictions==earlier
    assert any(e['source']=='publication' for e in s.events)
    assert any(point['value'] is None for point in s.history['temperature.tj'])
    values=copy.deepcopy(s.predictions)
    s.disconnect()
    assert s.predictions==values
    assert s.snapshot()['forecast']['latest_prediction_ids']==[]


def test_unconfigured_waiting_service_does_not_load_numerical_libraries():
    import subprocess,sys
    root=Path(__file__).parents[1]
    paths='' if os.environ.get('TTO_WEB_TEST_INSTALLED') else 'sys.path[:0]='+repr([str(root/'src'),str(root/'vendor')])+';'
    code="import sys,json;"+paths+"from tto_web.server import app_for;from tto_web.state import State;State(json.load(open("+repr(str(root/'config/web.json'))+")));assert 'numpy' not in sys.modules and 'scipy' not in sys.modules"
    subprocess.run([sys.executable,'-c',code],check=True)


def test_prediction_window_eviction_removes_inline_label_metadata():
    p=Producer(1000.);p.step(0);s=State(web_config());packet=p.step(115)
    s.accept(packet,now=p.start+115.01)
    page=seed_predictions(s,packet,[0,5000,10000,15000])
    removed=[r['prediction_id'] for r in page['records'] if r['origin_elapsed_ms']<10000]
    for row in page['records']:
        row.update(status='matched',observed_C=row['value_C'],error_C=0.,revision=row['revision']+len(page['records']),
                   label={'label_elapsed_ms':row['target_elapsed_ms'],'source_ref':'SYNTHETIC-LABEL','received_at_utc':None})
    page.update(cursor=24,watermark=24)
    s.accept_predictions(page,now=p.start+115.01)
    assert set(s.prediction_view(45)['labels'])=={r['prediction_id'] for r in page['records'] if r['horizon_s']==45}
    page.update(retained_from_mono_s=packet['origin_mono_s']+10,records=[])
    s.accept_predictions(page,now=p.start+115.01)
    assert len(s.predictions)==6 and all(id not in s.predictions for id in removed)
    result=s.prediction_view(45)
    assert set(result['labels'])=={r['prediction_id'] for r in result['records']}
    assert len(result['labels'])==2 and not set(removed)&set(result['labels'])
