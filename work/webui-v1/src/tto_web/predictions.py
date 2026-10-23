"""Read committed predictions for the registration owned by source.follow."""
import asyncio
import contextlib
import json


def final_page(path):
    with path.open('rb') as stream:
        data=stream.read(4*1024*1024+1)
    if len(data)>4*1024*1024:raise ValueError('terminal prediction view exceeds budget')
    return json.loads(data)


async def prediction_page(directory, cursor, *, ended):
    if ended:return await asyncio.to_thread(final_page,directory/'predictions-final.json')
    writer=None
    try:
        reader,writer=await asyncio.open_unix_connection(str(directory/'predictions.sock'),limit=512*1024)
        writer.write(json.dumps(dict(cursor=cursor)).encode()+b'\n')
        await asyncio.wait_for(writer.drain(),.5)
        return json.loads(await asyncio.wait_for(reader.readline(),1.))
    finally:
        if writer:
            writer.close()
            with contextlib.suppress(OSError):await writer.wait_closed()


async def follow_predictions(directory, state, stop, *, ended=False):
    while not stop.is_set():
        try:
            page=await prediction_page(directory,state.prediction_cursor,ended=ended)
            if not isinstance(page,dict) or page.get('ended') is not ended:
                raise ValueError('prediction lifecycle mismatch')
            state.accept_predictions(page)
            if ended:return
            if page['has_more']:continue
        except (OSError,ValueError,asyncio.TimeoutError):
            state.prediction_syncing=True
            state.refresh()
        await asyncio.sleep(.5)
