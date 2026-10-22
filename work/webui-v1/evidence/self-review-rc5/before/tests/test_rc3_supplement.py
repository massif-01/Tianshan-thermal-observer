"""Only rc3 credential classification; no device, transport, or native lock is opened."""
import asyncio
import json
import pytest
from producer import native_config,web_config
from tto_web.state import State
from tto_web.common import atomic_json
import tto_web.source as source


@pytest.mark.parametrize('section,case',[
    ('orin','permissions'),('orin','json'),('tianshan','header_type'),
    ('tianshan','transport_header'),('orin','missing'),
])
async def test_bad_credentials_stop_before_any_collector_round(tmp_path,monkeypatch,section,case):
    credentials=tmp_path/'headers.json';credentials.write_text('{"Authorization":"SYNTHETIC-SECRET"}');credentials.chmod(0o600)
    if case=='permissions':credentials.chmod(0o644)
    elif case=='json':credentials.write_text('{"Authorization":')
    elif case=='header_type':credentials.write_text('{"Authorization":123}')
    elif case=='transport_header':credentials.write_text('{"Host":"SYNTHETIC"}')
    native=native_config();native[section]['headers_file']=str(credentials)
    path=tmp_path/'native.json';atomic_json(path,native)
    if case=='missing':credentials.unlink()
    config=web_config();config['source'].update(mode='observe',observation_config=str(path))
    calls=[];stop=asyncio.Event();state=State(config)
    async def collect(*args,**kwargs):
        calls.append(1)
        # A controlled native budget terminal, exposing repeated owner rounds on rc2.
        if len(calls)>=2:stop.set()
        return None,dict(stop_reason='reconnect_attempt_budget')
    monkeypatch.setattr(source,'collect',collect)
    monkeypatch.setattr(source,'OBSERVE_RETRY_INITIAL_S',.001)
    monkeypatch.setattr(source,'OBSERVE_RETRY_MAX_S',.001)
    await asyncio.wait_for(source.observe(config,state,stop),1)
    assert not calls, 'local credential error reached collector rounds: '+str(len(calls))
    assert not state.source_connected and '配置无效' in state.source_status
    assert 'SYNTHETIC-SECRET' not in state.source_status and str(credentials) not in state.source_status


async def test_credentials_rechecked_before_network_recovery_round(tmp_path,monkeypatch):
    credentials=tmp_path/'headers.json';credentials.write_text('{"Authorization":"SYNTHETIC"}');credentials.chmod(0o600)
    native=native_config();native['orin']['headers_file']=str(credentials)
    path=tmp_path/'native.json';atomic_json(path,native)
    config=web_config();config['source'].update(mode='observe',observation_config=str(path))
    calls=[];stop=asyncio.Event();state=State(config)
    async def collect(*args,**kwargs):
        calls.append(1);credentials.chmod(0o644)
        if len(calls)>=2:stop.set()
        return None,dict(stop_reason='reconnect_attempt_budget')
    monkeypatch.setattr(source,'collect',collect)
    monkeypatch.setattr(source,'OBSERVE_RETRY_INITIAL_S',.001)
    await asyncio.wait_for(source.observe(config,state,stop),1)
    assert len(calls)==1 and '凭据配置无效' in state.source_status
    assert not stop.is_set() and not state.source_connected


async def test_valid_credentials_reach_exactly_one_stopped_round(tmp_path,monkeypatch):
    credentials=tmp_path/'headers.json';credentials.write_text('{"Authorization":"SYNTHETIC"}');credentials.chmod(0o600)
    native=native_config()
    for section in ('orin','tianshan'):native[section]['headers_file']=str(credentials)
    path=tmp_path/'native.json';atomic_json(path,native)
    config=web_config();config['source'].update(mode='observe',observation_config=str(path))
    calls=[];stop=asyncio.Event();state=State(config)
    async def collect(*args,**kwargs):calls.append(1);return None,dict(stop_reason='external_stop')
    monkeypatch.setattr(source,'collect',collect)
    await source.observe(config,state,stop)
    assert len(calls)==1 and not state.source_connected
