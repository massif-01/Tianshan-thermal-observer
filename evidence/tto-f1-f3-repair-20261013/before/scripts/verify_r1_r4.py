#!/usr/bin/env python3
"""Repair-only production-path probes. Synthetic objects + owned loopback servers.
Original reviewer scripts are retained separately; this is their labelled adaptation
for the repaired rejection paths and layered-decision/report contract.
"""
import argparse
import asyncio
import copy
import json
from pathlib import Path
from aiohttp import web
import aiohttp
from tto.demo import record_demo
from tto.dataset import freeze_split, build_dataset, load_dataset, check_split
from tto.training import train
from tto.evaluation import evaluate, value_conclusion
from tto.model import load_model
from tto.engine import Engine
from tto.storage import Journal
from tto.report import summarize
from tto.cli import main as cli_main
from tto.config import load_config
from tto.collector import sessions
from tto.util import read_json, write_json, seal, file_hash


async def redirects(cross_origin):
    seen=[];runners=[]
    async def target(request):
        seen.append({'path':request.path,'header':request.headers.get('X-TTO-Test')})
        ws=web.WebSocketResponse();await ws.prepare(request);await ws.close();return ws
    async def start(app):
        r=web.AppRunner(app);await r.setup();runners.append(r)
        site=web.TCPSite(r,'127.0.0.1',0);await site.start()
        return f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    target_url=None
    async def redirect(request):raise web.HTTPFound(target_url)
    try:
        app=web.Application();app.router.add_get('/socket.io/',redirect);app.router.add_get('/api/v1/fan/status',redirect);app.router.add_get('/not-authorized',target)
        origin=await start(app)
        if cross_origin:
            other=web.Application();other.router.add_get('/not-authorized',target);target_url=await start(other)+'/not-authorized'
        else:target_url=origin+'/not-authorized'
        c=load_config(environ={});c['orin']['base_url']=c['tianshan']['base_url']=origin
        async with sessions(c,'orin',socketio=True) as session:
            try:
                await session.ws_connect(origin+'/socket.io/?EIO=4&transport=websocket',headers={'X-TTO-Test':'nonsecret-fixture'})
                raise AssertionError('redirect was accepted')
            except ValueError as e:assert 'redirect' in str(e)
        assert session.closed and seen==[]
        async with sessions(c,'tianshan') as session:
            try:
                await session.get(origin+'/api/v1/fan/status');raise AssertionError('GET redirect was accepted')
            except ValueError:pass
        assert session.closed and seen==[]
        return {'cross_origin':cross_origin,'target_request_count':len(seen),'session_closed':session.closed,'aiohttp':aiohttp.__version__}
    finally:
        for r in reversed(runners):await r.cleanup()


def verify(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    runs=record_demo(root/'base-runs',count=5,seconds=720)
    frozen=freeze_split(runs,root/'frozen')
    base_model=train(frozen/'dataset.json',frozen/'split.json',root/'base-model.json')
    d,s=load_dataset(frozen/'dataset.json'),read_json(frozen/'split.json')
    ids=set(s['partitions']['test']);field=next(c for c in base_model['methods']['ridge_full']['columns'] if c.startswith('vdd_'))
    for r in d['rows']:
        if r['id'] in ids:
            for c in list(r['features']):
                if c==field or c.startswith(field+'_mean_'):r['features'][c]=None
    d.pop('sha256');d=seal(d);s.pop('sha256');s['dataset_sha256']=d['sha256'];s=seal(s)
    missing=root/'missing-m1';missing.mkdir();write_json(missing/'dataset.json',d);write_json(missing/'split.json',s)
    model=train(missing/'dataset.json',missing/'split.json',missing/'model.json')
    assert model['methods']==base_model['methods']
    ev=evaluate(missing/'dataset.json',missing/'split.json',missing/'model.json',missing/'evaluation')
    assert ev['comparisons']['m0']['horizons']['45']['matched_count']==198
    assert ev['comparisons']['m1']['horizons']['45']['matched_count']==0
    unit_data=copy.deepcopy(d);unit_data['simulated']=False
    for r in unit_data['runs']:r['deployment_status']='user_recorded_not_independently_verified'
    decision=value_conclusion(unit_data,s,[r for r in d['rows'] if r['id'] in ids],ev['comparisons'])
    assert 'M0有初步价值' in decision
    r2={'synthetic_only':True,'unchanged_training_methods':True,'missing_field':field,'matched_counts_45s':{k:v['horizons']['45']['matched_count'] for k,v in ev['comparisons'].items()},'decision_function_only_with_explicit_unit_flags':decision,'persisted_evaluation_conclusion':ev['conclusion']}
    chrono=record_demo(root/'chrono-runs',count=6,seconds=400)
    for i,path in enumerate(chrono):
        ep='A' if i in (0,5) else chr(ord('A')+i)
        m=read_json(path/'manifest.json');m.update(episode=ep,started_at_utc=f'2026-01-{i+1:02d}T00:00:00+00:00');(path/'manifest.json').write_text(json.dumps(m))
        for file in path.glob('observations-*'):
            records=[dict(json.loads(l),episode=ep) for l in file.read_text().splitlines()];file.write_text(''.join(json.dumps(r)+'\n' for r in records))
    try:
        freeze_split(chrono,root/'invalid-creation');raise AssertionError('non-contiguous grouping accepted')
    except ValueError as e:creation=str(e);assert '非连续' in creation
    bad_data=build_dataset(chrono);mapping=dict(A='train',B='train',C='validation',D='test',E='test')
    bad_split=seal({'schema_version':1,'dataset_sha256':bad_data['sha256'],'sources':bad_data['sources'],'scope':'chronological_episodes','episodes_order':list('ABCDE'),'partitions':{p:[r['id'] for r in bad_data['rows'] if mapping[r['episode']]==p] for p in ('train','validation','test')}})
    try:
        check_split(bad_data,bad_split);raise AssertionError('old bad partition accepted')
    except ValueError as e:validation=str(e);assert '非连续' in validation
    r1={'synthetic_only':True,'sequence':'A-B-C-D-E-A','creation_rejected':creation,'direct_validation_rejected':validation}
    # Same 400-second Engine/Journal path as the original reviewer.
    config=read_json(chrono[1]/'manifest.json')['config'];j=Journal(config,root/'shadow-runs',simulated=True,episode='shadow-fixture',run_type='shadow',model_sha256=base_model['sha256']);e=Engine(config,base_model)
    pn=sn=0
    for file in sorted(chrono[1].glob('observations-*')):
        for line in file.read_text().splitlines():
            out=e.process(j.observation(json.loads(line)))
            if out['prediction']:
                j.append('predictions',out['prediction']);pn+=int('ridge_full' in out['prediction']['values'])
            for score in out['scores']:
                j.append('scores',score);sn+=int('ridge_full' in score.get('errors',{}))
    for score in e.invalidate('run_end'):j.append('scores',score)
    j.close({'stop_reason':'synthetic_completed'})
    hashes={name:file_hash(j.path/name) for name in ('predictions.jsonl','scores.jsonl')}
    assert cli_main(['report','--run',str(j.path),'--output',str(root/'shadow-report')])==0
    before=summarize(j.path);group=before['recorded_results']['models'][base_model['sha256']]
    report_scores=sum(data['methods']['ridge_full']['scored'] for data in group['horizons'].values())
    assert pn==44 and sn==102 and report_scores==sn
    model_file=root/'base-model.json';backup=model_file.read_bytes();model_file.write_text('{"later_model":true}')
    assert summarize(j.path)==before;model_file.unlink();assert summarize(j.path)==before;model_file.write_bytes(backup)
    assert hashes=={name:file_hash(j.path/name) for name in hashes}
    for name in hashes:(j.path/name).rename(j.path/(name+'.removed-test-copy'))
    after=summarize(j.path);assert after!=before and len(after['missing_required_logs'])==2
    # Restore original fixture bytes for independent report replay.
    for name in hashes:(j.path/(name+'.removed-test-copy')).rename(j.path/name)
    r3={'synthetic_only':True,'stored_full_model_predictions':pn,'stored_full_model_scores':sn,'report_full_model_scores':report_scores,'changed_model_file_did_not_change_statistics':True,'log_removal_reported':after['missing_required_logs'],'prediction_and_score_logs_unchanged':True,'shadow_run':str(j.path.relative_to(root))}
    r4=[asyncio.run(redirects(cross)) for cross in (True,False)]
    findings={'R1':r1,'R2':r2,'R3':r3,'R4':r4,'hardware_executed':False}
    write_json(root/'findings.json',findings)
    print(json.dumps(findings,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();verify(a.output)
