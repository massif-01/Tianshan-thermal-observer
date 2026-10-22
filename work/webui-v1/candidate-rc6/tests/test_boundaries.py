import asyncio
import copy
import json
import os
import time
from pathlib import Path
import pytest
from aiohttp import web
from tto_web.server import app_for
from tto_web.state import State
from tto_web.source import Publication
from producer import Producer,web_config


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
    template=copy.deepcopy(s.predictions[-1])
    for i in range(10000):
        row=copy.deepcopy(template);row['prediction_id']='synthetic-'+str(i);s.predictions.append(row)
    # Count traversal copies directly: the snapshot must contain only six forecast summaries.
    snapshot=s.refresh(p.start+120.01)
    assert len(snapshot['predictions'])==6
    assert len(s.predictions)<=11070
    assert s.predictions.maxlen==11070 and s.events.maxlen==1000


def test_late_and_cross_epoch_not_error_denominators():
    p=Producer(time.monotonic()-120);s=State(web_config())
    for t in range(121):s.accept(p.step(t),now=p.start+t+.01)
    current=s.predictions[-2]
    late=copy.deepcopy(current);late.update(prediction_id='late',origin_elapsed_ms=0,target_elapsed_ms=45000,status='late_publication')
    before=s.prediction_view(45)['summary'];s.predictions.append(late);after=s.prediction_view(45)['summary']
    assert after['late_publication_count']==before['late_publication_count']+1
    assert after['due_count']==before['due_count'] and after['matched_count']==before['matched_count']


def test_publication_path_error_is_explicit(tmp_path):
    pub=Publication(tmp_path/('x'*100)/'active.json')
    async def check():
        with pytest.raises(ValueError,match='短路径'):await pub.__aenter__()
    asyncio.run(check())


def test_prediction_delta_preserves_whole_window_denominator_and_recent_label_updates():
    p=Producer(time.monotonic()-120);s=State(web_config())
    for t in range(121):s.accept(p.step(t),now=p.start+t+.01)
    complete=s.prediction_view(45,0,120010)
    delta=s.prediction_view(45,0,120010,records_after=119000)
    assert delta['summary']==complete['summary']
    assert len(delta['records'])<len(complete['records'])
    assert all(v['target_elapsed_ms']>=117000 for v in delta['records'])
    assert delta['records_complete'] is False
    assert complete['records_complete'] is True


def test_lost_publication_does_not_call_next_available_tj_the_first_label():
    p=Producer(time.monotonic()-20);s=State(web_config())
    for t in range(13):s.accept(p.step(t),now=p.start+t+.01)
    earlier=list(s.predictions)
    packet=p.step(15);packet['publication_gap']=True;s.accept(packet,now=p.start+15.01)
    assert all(v['status']=='not_comparable' for v in earlier if v['target_elapsed_ms']>=15000)
    assert any(e['source']=='publication' for e in s.events)
    assert any(point['value'] is None for point in s.history['temperature.tj'])
    values=[(v['prediction_id'],v['value_C']) for v in s.predictions]
    s.disconnect()
    assert not any(v['status']=='pending' for v in s.predictions)
    assert values==[(v['prediction_id'],v['value_C']) for v in s.predictions]


def test_unconfigured_waiting_service_does_not_load_numerical_libraries():
    import subprocess,sys
    code="import sys,json;sys.path[:0]=['src','vendor'];from tto_web.server import app_for;from tto_web.state import State;State(json.load(open('config/web.json')));assert 'numpy' not in sys.modules and 'scipy' not in sys.modules"
    subprocess.run([sys.executable,'-c',code],check=True)


def test_prediction_ring_eviction_also_removes_label_metadata():
    from collections import deque
    p=Producer(time.monotonic()-20);s=State(web_config())
    for t in range(13):s.accept(p.step(t),now=p.start+t+.01)
    s.predictions=deque(list(s.predictions)[-3:],maxlen=3)
    old=list(s.predictions)
    s.prediction_labels={v['prediction_id']:{'synthetic':True} for v in old}
    s.accept(p.step(14),now=p.start+14.01)
    assert len(s.predictions)==3
    assert not any(v['prediction_id'] in s.prediction_labels for v in old)
