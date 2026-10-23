"""Read the producer's committed prediction ledger; never compute a forecast."""
import asyncio
import contextlib
import json
from pathlib import Path
from .common import boot_id, load


def final_page(path):
    with path.open('rb') as stream:
        data=stream.read(4*1024*1024+1)
    if len(data)>4*1024*1024:raise ValueError('terminal prediction view exceeds budget')
    return json.loads(data)


async def follow_predictions(config, state, stop):
    descriptor=config['source'].get('active_descriptor')
    if not descriptor:return
    path=Path(descriptor)
    while not stop.is_set():
        writer=None
        try:
            meta=load(path)
            if meta.get('schema')!='TTO-WEB-ACTIVE-v1' or meta.get('boot_id')!=boot_id():
                raise ValueError('prediction descriptor identity')
            if meta.get('publication_failed'):
                state.prediction_failed=True;state.prediction_syncing=False;state.forecast=None
                state.refresh();await asyncio.sleep(.5);continue
            if not meta.get('prediction_socket') and not meta.get('prediction_final'):
                state.forecast=None;state.prediction_syncing=False;state.prediction_failed=False
                await asyncio.sleep(.5);continue
            if meta['ended'] and state.prediction_publisher==meta['publisher_id'] and state.prediction_ended and not state.prediction_syncing:
                await asyncio.sleep(.5);continue
            state.begin_predictions(meta['publisher_id'])
            if meta['ended']:
                if meta.get('prediction_final')!='predictions-final.json':raise ValueError('terminal prediction filename')
                page=await asyncio.to_thread(final_page,path.parent/'predictions-final.json')
                state.accept_predictions(page)
            else:
                if meta.get('prediction_socket')!='predictions.sock' or meta.get('prediction_protocol')!='TTO-PREDICTION-PAGE-v1':
                    raise ValueError('prediction protocol')
                reader,writer=await asyncio.open_unix_connection(str(path.parent/'predictions.sock'),limit=512*1024)
                writer.write(json.dumps(dict(cursor=state.prediction_cursor)).encode()+b'\n')
                await asyncio.wait_for(writer.drain(),.5)
                page=json.loads(await asyncio.wait_for(reader.readline(),1.))
                state.accept_predictions(page)
                if page['has_more']:continue
        except (OSError,ValueError,asyncio.TimeoutError):
            state.prediction_syncing=True
            state.refresh()
        finally:
            if writer:
                writer.close()
                with contextlib.suppress(OSError):await writer.wait_closed()
        await asyncio.sleep(.5)
