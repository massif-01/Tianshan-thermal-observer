#!/usr/bin/env python3
"""Offline preparation entrypoint. No field network execution in this R2 candidate."""
import argparse,asyncio,copy,json,sys
from pathlib import Path
from scheduler import resolve_plan
from drivers import virtual_run,write,SEED
ROOT=Path(__file__).resolve().parent

def scaled_http_profile(profile):
    # Only loopback timing is scaled. The schedule engine stays the same.
    p=copy.deepcopy(profile)
    for s in p['stages']:s['seconds']=.23 if s['kind']=='work' else .025
    p.update(hard_limit_seconds=8,cleanup_reserve_seconds=1,preparation_reserve_seconds=1,drain_per_work_max_seconds=1)
    return p

def main(argv=None):
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='command',required=True)
    for name in ('plan','dry-run','loopback'):
        p=sp.add_parser(name);p.add_argument('--profile',default='fixed-anchors');p.add_argument('--output',type=Path)
        if name=='dry-run':
            p.add_argument('--scenario',default='healthy',choices=['healthy','startup','short_gap','long_gap','http_timeout','mode_change','binding_change','guard','fault','unknown_safety','unavailable_observer','permission_missing'])
            p.add_argument('--run-id',default='synthetic-mix-r2');p.add_argument('--command-id',default='dry-run-r2');p.add_argument('--seed',type=int,default=SEED)
        if name=='loopback':p.add_argument('--behavior',choices=['normal','incomplete'],default='normal')
    p=sp.add_parser('execute');p.add_argument('--binding',type=Path,required=True)
    args=ap.parse_args(argv)
    if args.command=='execute':
        # Deliberately closed until one integrated #8/#9 candidate and fresh field authorization are reviewed.
        raise ValueError('现场执行未放行：本R2候选只支持plan/dry-run/loopback；绑定模板不是本轮现场授权。')
    plan=json.loads((ROOT/'inputs/mix-plan.json').read_text());profile=resolve_plan(plan,args.profile)
    if args.command=='plan':
        result={'profile':profile,'request_policy':plan['request_policy'],'irregular_seed':SEED,'schedule_origin':'explicit list from supplied mix-plan; no thermal selection',
                'model_configuration':json.loads((ROOT/'model-profiles.json').read_text())[profile['model_profile']],
                'offline_only':True,'field_authorized':False}
        if args.output:write(args.output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.output is None:raise ValueError('--output needs a new local directory')
    if args.command=='dry-run':s=virtual_run(profile,plan['request_policy'],args.output,args.scenario,args.seed,args.run_id,args.command_id)
    else:
        from fake_http import FakeService
        from drivers import loopback_run
        async def http():
            async with FakeService(args.behavior) as service:
                s=await loopback_run(scaled_http_profile(profile),plan['request_policy'],args.output,service.url,args.behavior,
                                     run_id='loopback-'+args.behavior,command_id='loopback-'+args.behavior)
                write(args.output/'fake-service-proof.json',{'bind':'127.0.0.1:ephemeral','posts':service.posts,'peak_server_handlers':service.peak,
                                                         'physical_interpretation':'fake HTTP handlers only; not GPU concurrency','one_request_scheduler':True,
                                                         'no_board_polling':True,'no_live_model_requests':True})
                return s
        s=asyncio.run(http())
    print(json.dumps({'reason':s.reason,'requests':s.submitted,'peak_client_inflight':s.peak,'elapsed_mono_s':s.now,'offline_only':True}));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,FileExistsError) as e:print(str(e),file=sys.stderr);sys.exit(2)
