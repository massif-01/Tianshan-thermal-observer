#!/usr/bin/env python3
"""TTO-MIDLOAD-DEV-v1.0: default plan is offline; live requires explicit targets."""
import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import sys
from datetime import datetime,timezone
import zipfile

# -I omits the script directory. Only this bundle's sibling modules are added.
if sys.flags.isolated:sys.path.insert(0,str(Path(__file__).resolve().parent))

EXPECTED_VERSION='0.2.4'
OVERRIDE_POLICY=json.loads((Path(__file__).resolve().parent.parent/'override-policy.json').read_text())
def override_identity():
    return dict(policy=OVERRIDE_POLICY,copy_hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(__file__).resolve().parent.glob('*.py'))},result_role='user_overridden_development_experiment_not_native_acceptance')


class RuntimeIdentityError(ValueError):pass


def runtime_identity():
    import importlib.metadata as metadata
    try:
        import tto
        installed_version=metadata.version('tianshan-thermal-observer')
    except (ImportError,metadata.PackageNotFoundError) as error:
        raise RuntimeIdentityError('没有找到本轮已安装TTO；请先安装0.2.4候选，再使用新安装目录的tto-midload入口。') from error
    path=Path(tto.__file__).resolve()
    if tto.__version__!=EXPECTED_VERSION or installed_version!=EXPECTED_VERSION or Path(sys.prefix) not in path.parents or 'site-packages' not in path.parts:
        raise RuntimeIdentityError(f'运行环境不匹配：需要TTO {EXPECTED_VERSION}，实际导入{tto.__version__}（{path}），安装记录为{installed_version}。请使用0.2.4新安装目录下的tto-midload入口；不是配置文件缺项。')
    return dict(version=tto.__version__,import_path=str(path),python=sys.executable,isolated=bool(sys.flags.isolated),non_editable=True)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def load_trial(path):
    config=json.loads(Path(path).read_text());inference=config['inference']
    if config.get('trial_id')!='TTO-MIDLOAD-DEV-v1.0':raise ValueError('测试计划编号不正确。')
    if not isinstance(inference.get('model'),str) or not inference['model']:raise ValueError('请在本地配置中指定模型。')
    if not isinstance(inference.get('messages'),list) or not inference['messages']:raise ValueError('缺少工作块请求文本。')
    if any(not isinstance(m,dict) or not isinstance(m.get('content'),str) or m.get('role') not in ('system','user','assistant') for m in inference['messages']):raise ValueError('请求文本格式不正确。')
    if any(k not in ('temperature','top_p','seed','stop') for k in inference.get('sampling',{})):raise ValueError('不能用采样参数覆盖固定测试预算。')
    return config


def preview(config,args):
    from trial import PHASES
    return dict(trial_id=config['trial_id'],mode='dry_run',connected=False,credentials_read=False,
                runtime=runtime_identity(),operator_override=override_identity(),
                nominal_duration_s=2480,hard_limit_s=2700,initial_check_within_background_s=180,strict_history_s=60,
                phases=[dict(id=i,kind=k,duration_s=d) for i,k,d in PHASES],max_total_requests=256,max_tokens=256,max_inflight=1,
                max_request_wall_s=30,max_drain_s=30,model=config['inference']['model'],
                inference_target_configured=bool(config['inference'].get('base_url')),tto_config_path=str(args.tto_config) if args.tto_config else None,
                ambient_temperature_default=None,not_thermal_equilibrium=True,
                message='约41分20秒；20/60/180秒是单路请求发起窗口，已有请求自然结束；最多45分钟。当前只预览，未连接设备。')


async def execute(args,config,clock=None,collector_factory=None,health_factory=None,requester_factory=None,phases=None,hard_limit_s=2700):
    from trial import RealClock,run_schedule,PHASES
    from health import TrialHealth
    from requester import Requester
    import tto
    from tto.config import load_config,public_config,require_live
    from tto.collector import collect
    runtime_identity()
    if not args.tto_config or not config['inference'].get('base_url'):raise ValueError('真实模式需要完整的本地TTO和推理服务配置。')
    c=load_config(args.tto_config,environ={});require_live(c,hard_limit_s)
    clock=clock or RealClock();start=clock.now();stop=asyncio.Event();health=(health_factory or TrialHealth)()
    output_root=args.output_root.expanduser();output_root.mkdir(parents=True,exist_ok=True)
    out=output_root/('midload-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(mode=0o700)
    events=(out/'events.jsonl').open('x');requests=(out/'requests.jsonl').open('x');collector_task=None;requester=None;result=None
    def emit(event,**fields):
        row=dict(event=event,mono_s=clock.now(),occurred_at_utc=clock.utc(),written_at_utc=datetime.now(timezone.utc).isoformat(),**fields)
        events.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');events.flush()
        if event=='request_end':requests.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');requests.flush()
        if event=='phase_start' or event=='phase_end':
            ambient=json.loads(args.ambient_file.read_text()) if args.ambient_file else {'temperature_c':None,'observed_at_utc':None,'written_at_utc':None,'measurement_point':None,'instrument':None}
            emit('ambient_snapshot',phase=fields['phase'],record=ambient,missing_boundary_measurement=ambient.get('temperature_c') is None)
    write(out/'frozen-plan.json',{**preview(config,args),'mode':'live_plan','execution_requested':True})
    write(out/'identity.json',dict(operator_override=override_identity(),trial_id=config['trial_id'],tto_version=tto.__version__,tto_import_path=tto.__file__,tto_config=public_config(c),
          tto_config_sha256=sha(args.tto_config),trial_config_sha256=sha(args.trial_config),runner_sha256=sha(__file__),
          clock_domain='observer_host_monotonic_and_UTC; service timestamps retained in collector payload',
          source_sampling_changed=False,fan_control_changed=False,data_role='new_development_process_not_independent_confirmation'))
    try:
        requester=(requester_factory or Requester)(config['inference'],out,clock,emit);await requester.open()
        resident=await requester.check_resident_idle();emit('resident_idle_check',evidence=resident)
        remaining=start+hard_limit_s-min(10,hard_limit_s*.05)-clock.now()
        if remaining<=0:raise ValueError('准备检查已经用完本轮时间预算。')
        collector_task=asyncio.create_task((collector_factory or collect)(c,remaining,data_root=out/'collection',episode=out.name,
                                         run_type='midload_collect',stop_event=stop,on_record=health.observe))
        emit('collector_started',one_collector=True)
        result=await run_schedule(clock,health,requester,stop,collector_task,emit,phases=phases or PHASES,hard_limit_s=hard_limit_s,start_mono=start)
    except asyncio.CancelledError:
        result=dict(status='stopped',stop_reason='operator_stop',server_request_completion='unknown');emit('operator_stop')
    except Exception as e:
        result=dict(status='stopped',stop_reason=type(e).__name__,server_request_completion='unknown');emit('preparation_or_collection_error',error_class=type(e).__name__)
        print('本轮未完成；记录已保存，请查看停止原因后交回复核。',flush=True)
    finally:
        stop.set()
        if requester is not None:await requester.close()
        if collector_task is not None:
            remaining=max(.01,start+hard_limit_s-clock.now())
            try:
                path,stats=await asyncio.wait_for(collector_task,remaining)
                result['collection_path']=str(path.relative_to(out));result['collector_stop_reason']=stats['stop_reason'];result['polling_health']=stats.get('polling_health')
            except (asyncio.TimeoutError,asyncio.CancelledError):
                result.update(status='stopped',stop_reason='collector_cleanup_deadline',collector_closed=False)
            except Exception as e:result.update(status='stopped',stop_reason='collector_failure:'+type(e).__name__)
        result.update(operator_override=override_identity(),output=str(out),elapsed_total_s=clock.now()-start,hard_limit_s=hard_limit_s,
                      live_validation='requires_independent_review; this executable does not authorize a field run',new_model_training='not_performed',control_authorization='none')
        write(out/'input-health.json',health.snapshot(clock.now()))
        write(out/'summary.json',result);events.close();requests.close()
        hashes={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.rglob('*')) if p.is_file()}
        write(out/'SHA256.json',hashes)
        archive=out/'trial-result.zip'
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob('*')):
                if p.is_file() and p!=archive:z.write(p,str(p.relative_to(out)))
        print('本轮采集已结束，风扇控制没有改动。请把这个结果包交回复核：'+str(archive),flush=True)
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description='中等负载测试准备：默认离线预览；现场须经复审并另获授权。')
    mode=ap.add_mutually_exclusive_group();mode.add_argument('--live',action='store_true');mode.add_argument('--dry-run',action='store_true');mode.add_argument('--plan',action='store_true')
    ap.add_argument('--trial-config',type=Path,default=Path(__file__).with_name('plan.example.json'))
    ap.add_argument('--tto-config',type=Path);ap.add_argument('--output-root',type=Path,default=Path.home()/'TTO-midload-trials')
    ap.add_argument('--ambient-file',type=Path)
    args=ap.parse_args(argv)
    try:
        runtime_identity()
        config=load_trial(args.trial_config)
        if not args.live:
            result=preview(config,args);print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        result=asyncio.run(execute(args,config));return 0 if result['status']=='completed' else 2
    except KeyboardInterrupt:
        print('已停止。若最后一条请求尚未确认结束，请不要再次启动测试。',flush=True);return 130
    except RuntimeIdentityError as error:
        print(str(error),file=sys.stderr);return 2
    except (ValueError,KeyError,OSError,json.JSONDecodeError):
        print('本地配置不完整或不可用；未启动测试。请按操作卡核对配置路径。',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
