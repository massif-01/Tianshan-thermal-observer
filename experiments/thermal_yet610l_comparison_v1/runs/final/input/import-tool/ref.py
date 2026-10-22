#!/usr/bin/env python3
"""Single local CLI: surface-reference sidecars only. Never invokes TTO or a camera."""
from pathlib import Path
import argparse
import json
import sys
import time
import uuid
from refprep.files import read,write,lines,now_utc
from refprep.records import register_session,load_session,normalize,commit_record,import_file,latest_records,session_event
from refprep.cues import load_plan,replay_events,read_events,watch_file
from refprep.trajectory import adapt
from refprep.compare import compare

ROOT=Path(__file__).absolute().parent


def print_json(value):print(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))


def parser():
    ap=argparse.ArgumentParser(description='TTO外部局部表面参照：离线记录/导入/对齐，零设备接口。')
    sp=ap.add_subparsers(dest='command',required=True)
    p=sp.add_parser('plan',help='打印测点准备与固定提醒计划；不运行试验')
    p.add_argument('--cue-plan',type=Path)
    p=sp.add_parser('init-session',help='登记不可变的run/测点/设置会话；未知字段保持null')
    p.add_argument('--store',type=Path,required=True);p.add_argument('--session',type=Path,required=True)
    p.add_argument('--run-id');p.add_argument('--session-id');p.add_argument('--site-id')
    p=sp.add_parser('watch-events',help='只读指定本地runner事件；默认一次离线检查，--replay为虚拟时钟回放')
    p.add_argument('--events',type=Path,required=True);p.add_argument('--cue-plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--replay',action='store_true');mode.add_argument('--follow',action='store_true')
    for name,helptext in [('mark','先保存按键打点，可空温度/空图片；不冒充曝光'),('record','补录/修订，或交互记录；旧记录不覆盖')]:
        p=sp.add_parser(name,help=helptext)
        p.add_argument('--store',type=Path,required=True);p.add_argument('--session-id',required=True)
        p.add_argument('--record-id');p.add_argument('--revise',action='store_true')
        p.add_argument('--value');p.add_argument('--unit',choices=['C','F'])
        p.add_argument('--measured-at');p.add_argument('--interval-start');p.add_argument('--interval-end')
        p.add_argument('--uncertainty-s',type=float);p.add_argument('--time-source')
        p.add_argument('--artifact',type=Path);p.add_argument('--image-metadata-time');p.add_argument('--note')
        p.add_argument('--cue-ledger',type=Path);p.add_argument('--checkpoint-id')
        p.add_argument('--capture-interval',action='store_true',help='交互开始至输入完成的主机时间区间；不是精确曝光')
    p=sp.add_parser('import',help='显式映射CSV/JSON，支持迟录/空值/原图；重复文件不增加点数')
    p.add_argument('--store',type=Path,required=True);p.add_argument('--file',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True)
    p=sp.add_parser('session-event',help='记录开始/结束/校时及探头移动/重贴/松脱；探头变化须新会话')
    p.add_argument('--store',type=Path,required=True);p.add_argument('--session-id',required=True)
    p.add_argument('--type',dest='event_type',required=True,choices=['recording_start','recording_end','clock_check','probe_moved','probe_reattached','probe_loose'])
    p.add_argument('--measured-at');p.add_argument('--uncertainty-s',type=float);p.add_argument('--note')
    p=sp.add_parser('adapt-trajectories',help='复制已有冻结轨迹为最小对照接口；不重估状态/参数')
    p.add_argument('--slowstate-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--run',choices=['L','S','M'])
    p=sp.add_parser('compare',help='合法as-of/完整时间区间对照；零测温也生成中文报告')
    p.add_argument('--store',type=Path,required=True);p.add_argument('--trajectory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--plot-python',type=Path);p.add_argument('--no-plots',action='store_true')
    return ap


def do_record(args):
    start_utc=now_utc();start_mono=time.monotonic()
    session=load_session(args.store,args.session_id)
    record_id=args.record_id or str(uuid.uuid4())
    prior=next((r for r in latest_records(args.store) if r['session_id']==args.session_id and r['record_id']==record_id),None)
    if args.revise and prior is None:raise ValueError('--revise record not found')
    if prior and not args.revise:raise ValueError('Existing record: use --revise to append a correction')
    values={k:prior.get(k) for k in ['original_value','original_unit','measured_at_raw','measured_interval_raw',
            'time_uncertainty_s','time_source','note','synthetic','clock_domain']} if prior else {}
    values['record_id']=record_id
    if args.command=='record' and args.value is None:
        value=input('固定测点读数（留空=无数值，仅材料；默认°C）：').strip()
        values['original_value']=value or None
        values['original_unit']=args.unit or 'C'
    elif args.value is not None:
        values['original_value']=args.value;values['original_unit']=args.unit or values.get('original_unit') or 'C'
    if args.measured_at:
        values['measured_at_raw']=args.measured_at;values['measured_interval_raw']=None
    if args.interval_start or args.interval_end:
        values['measured_interval_raw']=dict(start=args.interval_start,end=args.interval_end);values['measured_at_raw']=None
    if args.capture_interval:
        if args.command!='record' or args.value is not None:raise ValueError('--capture-interval requires interactive record')
        values['measured_at_raw']=None
        values['measured_interval_raw']=dict(start=start_utc,end=now_utc())
        profile=session.get('time',{})
        values['clock_domain']='run_utc' if profile.get('clock_domain')=='run_utc' and profile.get('sync_basis') else 'operator_host_utc'
        values['time_source']='operator_start_to_input_complete_interval_exposure_not_verified'
        if args.uncertainty_s is None:values['time_uncertainty_s']=None
    for arg,key in [('uncertainty_s','time_uncertainty_s'),('time_source','time_source'),('note','note')]:
        if getattr(args,arg) is not None:values[key]=getattr(args,arg)
    if args.artifact:values['artifact_path']=str(args.artifact)
    if args.image_metadata_time:values['image_metadata_time_raw']=args.image_metadata_time
    if args.command=='mark':
        values.update(operator_mark_at_utc=start_utc,operator_mark_mono_s=start_mono,
                      operator_mark_clock_domain='local_tool_host_not_automatically_run_clock')
    if args.cue_ledger and args.checkpoint_id:
        found=next((r for r in reversed(lines(args.cue_ledger)) if args.checkpoint_id in r['checkpoint_ids']),None)
        if found is None:raise ValueError('Checkpoint ID not present in cue ledger')
        values.update(checkpoint_ids=found['checkpoint_ids'],prompt_due_at_utc=found['prompt_due_at_utc'],
                      prompt_emitted_at_utc=found['prompt_emitted_at_utc'])
    rec=normalize(args.store,args.session_id,values,dict(operation=args.command,late_revision=bool(prior)))
    if prior and not args.artifact:rec['artifact']=prior.get('artifact')
    return commit_record(args.store,rec,values.get('artifact_path'),allow_revision=args.revise)


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=='plan':
            result=dict(contract='TTO-REF-PREP-v1.0',mode='offline_plan',backup_sparse_cue_plan=load_plan(args.cue_plan),
                default_input_path='numeric_export',continuous_mode_prompts=['开始独立记录','开始附近独立校时','结束附近独立校时及停止记录','移动/重贴/松脱时记事件并换会话'],
                measurement_sites='主参照YET-610L+K型探头，用耐温聚酰亚胺胶带固定同一局部表面；背板另测点，人工/红外为备用',
                preparation='用户已购买仪表与胶带；真实CSV列格式待1–2分钟试记录；接触式不要求IR发射率/反射/ROI；实际接触和探头响应未验证',
                clocks='提醒/按键/实际拍摄或区间/写入分别保存；mtime与聊天时间不当测量时间',
                missing='遗漏记未采，不延长、不补跑；外部测温不是全局建模前置',
                device_access=False,workload_actions=False)
        elif args.command=='init-session':
            session=read(args.session)
            for key in ['run_id','session_id','site_id']:
                if getattr(args,key):session[key]=getattr(args,key)
            result=register_session(args.store,session)
        elif args.command=='watch-events':
            if args.events.absolute()==args.output.absolute():raise ValueError('Sidecar output cannot overwrite event file')
            plan=load_plan(args.cue_plan)
            if args.replay:
                state=replay_events(read_events(args.events),plan)
                args.output.mkdir(parents=True,exist_ok=True)
                from refprep.files import dump_lines
                dump_lines(args.output/'reminders.jsonl',state['history'])
                write(args.output/'replay-state.json',state)
            else:state=watch_file(args.events,plan,args.output,follow=args.follow)
            result=dict(mode='virtual_replay' if args.replay else 'local_file_watch' if args.follow else 'offline_startup_scan',
                prompts=state['emitted_count'],checkpoints=len(state['history']),pending=len(state['pending']),
                model_driven=False,workload_extended=False)
        elif args.command in ['mark','record']:result=do_record(args)
        elif args.command=='import':result=import_file(args.store,args.file,read(args.mapping))
        elif args.command=='session-event':result=session_event(args.store,args.session_id,args.event_type,args.measured_at,args.uncertainty_s,args.note)
        elif args.command=='adapt-trajectories':result=adapt(args.slowstate_dir,args.output,args.run)
        else:result=compare(args.store,args.trajectory,args.output,args.plot_python,not args.no_plots)
        print_json(result);return 0
    except (ValueError,KeyError,OSError,TypeError) as error:
        print('本地参照工具未完成：'+str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
