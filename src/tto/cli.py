import argparse
import asyncio
import json
import multiprocessing
import os
from pathlib import Path
from . import __version__
from .config import load_config, public_config, headers, require_live
from .util import digest, write_json


def _train_worker(dataset, split, output):
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    from .training import train
    train(dataset, split, output)


def bounded_train(dataset, split, output):
    import time
    import psutil
    context = multiprocessing.get_context('spawn')
    p = context.Process(target=_train_worker, args=(dataset, split, output))
    p.start()
    process = psutil.Process(p.pid)
    started, peak = time.monotonic(), 0
    try:
        while p.is_alive():
            try:
                peak = max(peak, process.memory_info().rss)
            except psutil.NoSuchProcess:
                break
            if peak > 2 * 1024 ** 3 or time.monotonic() - started > 600:
                p.terminate()
                raise ValueError('training exceeded CPU time/RSS budget')
            p.join(.1)
        p.join()
        if p.exitcode != 0:
            raise ValueError('training failed; see finite, offline error above')
        write_json(str(output) + '.resource.json', {'peak_rss_mib_sampled': peak / 1024 ** 2, 'wall_s': time.monotonic() - started, 'threads': 1, 'scope': 'current_host_not_N305'})
    finally:
        if p.is_alive():
            p.terminate()
            p.join(3)
            if p.is_alive():
                p.kill()
                p.join()
        p.close()


def parser():
    p = argparse.ArgumentParser(prog='tto', description='天山热观察器：只记录、预测和评估，无控制输出。')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'collect', 'shadow'):
        q = sub.add_parser(name)
        q.add_argument('--config', required=True)
        q.add_argument('--duration', type=float)
        q.add_argument('--orin-url')
        q.add_argument('--tianshan-url')
        q.add_argument('--data-root')
        q.add_argument('--deployment-record', help='local user-filled final package/config evidence; never a remote verifier')
        q.add_argument('--source-interval-ms', type=int)
        q.add_argument('--source-interval-evidence')
        q.add_argument('--episode', help='short process grouping; reuse for the same continuous thermal process')
        if name == 'doctor':
            q.add_argument('--live', action='store_true', help='explicit bounded read-only device check')
            q.add_argument('--model')
        if name == 'shadow':
            q.add_argument('--model', required=True)
    q = sub.add_parser('summarize'); q.add_argument('--run', required=True)
    q = sub.add_parser('report'); q.add_argument('--run', required=True); q.add_argument('--output', required=True); q.add_argument('--diagnostic-input-v2', action='store_true', help='旧run另做新版输入诊断；不替换历史预测/评分')
    q = sub.add_parser('split'); q.add_argument('--runs', nargs='+', required=True); q.add_argument('--output', required=True); q.add_argument('--exploratory', action='store_true')
    q = sub.add_parser('train'); q.add_argument('--dataset', required=True); q.add_argument('--split', required=True); q.add_argument('--output', required=True)
    q = sub.add_parser('evaluate'); q.add_argument('--dataset', required=True); q.add_argument('--split', required=True); q.add_argument('--models'); q.add_argument('--output', required=True)
    q = sub.add_parser('demo'); q.add_argument('--output', required=True)
    return p


def run(args):
    if args.command in ('doctor', 'collect', 'shadow'):
        overrides = {'orin.base_url': args.orin_url, 'tianshan.base_url': args.tianshan_url, 'storage.data_root': args.data_root, 'orin.source_sample_interval_ms': args.source_interval_ms, 'orin.source_interval_evidence': args.source_interval_evidence, 'run.default_duration_s': args.duration}
        c = load_config(args.config, overrides)
        for s in ('orin', 'tianshan'):
            headers(c, s)
        from .deployment import deployment_record
        deployment = deployment_record(args.deployment_record)
        model = None
        model_error = None
        if getattr(args, 'model', None):
            from .model import load_model
            try:
                model = load_model(args.model)
            except (ValueError, OSError, TypeError, KeyError):
                model_error = '模型不可用；撤下模型预测，采集和基线仍可运行。'
            if model and model.get('simulated') and args.command == 'shadow':
                raise ValueError('模拟模型不能连接真实端点作为旁路候选。')
        duration = args.duration or (c['run']['doctor_duration_s'] if args.command == 'doctor' else c['run']['default_duration_s'])
        if args.command == 'doctor' and not args.live:
            return {'status': 'offline_config_valid', 'connected': False, 'deployment_status': deployment['deployment_status'], 'config_sha256': digest(public_config(c)), 'source_period_confirmed': c['orin']['source_sample_interval_ms'] is not None, 'model': ('legacy_offline_only_new_run_incompatible' if model and model['schema_version']==1 else 'valid') if model else ('unavailable' if model_error else 'not_requested'), 'input_selection': 'automatic_remote_platform_declaration', 'message': model_error or '离线检查完成；尚未连接设备，平台和控制资格将在记录中检查。'}
        require_live(c, duration)
        if args.episode is not None and (len(args.episode) > 80 or not args.episode or any(x in args.episode for x in ('\n', '\r', '<', '>'))):
            raise ValueError('episode must be a short scene word, not task text')
        if model_error:
            print(model_error, flush=True)
        from .collector import collect
        path, stats = asyncio.run(collect(c, duration, model=model, episode=args.episode, deployment=deployment, run_type=args.command))
        from .report import summarize
        result = summarize(path)
        result['run'] = str(path)
        result['observer_stop_reason'] = stats['stop_reason']
        result['command_success'] = stats['stop_reason'] in ('duration', 'SIGINT', 'SIGTERM')
        if args.command == 'doctor':
            result['message'] = '只读入口检查完成；实际安装包与最终配置身份仍需用户部署记录，不能从HTTP推定。'
        return result
    if args.command == 'summarize':
        from .report import summarize
        result = summarize(args.run)
        result['recorded_results'] = {k:v for k,v in result['recorded_results'].items() if k not in ('prediction_references','scored_records')}
        return result
    if args.command == 'report':
        from .report import run_report
        result = run_report(args.run, args.output, args.diagnostic_input_v2)
        return {'output': args.output, 'report_type': result['report_type'], 'conclusion': result['conclusion'], 'next_step': result['next_step'], 'missing_required_logs': result['missing_required_logs'], 'recorded_origins': result['recorded_results']['issued_prediction_origins']}
    if args.command == 'split':
        from .dataset import freeze_split
        return {'output': str(freeze_split(args.runs, args.output, args.exploratory))}
    if args.command == 'train':
        bounded_train(args.dataset, args.split, args.output)
        return {'model': args.output, 'status': 'frozen_not_activated'}
    if args.command == 'evaluate':
        from .evaluation import evaluate
        result = evaluate(args.dataset, args.split, args.models, args.output)
        return {'output': args.output, 'conclusion': result['conclusion']}
    if args.command == 'demo':
        from .demo import demo
        return {'output': str(demo(args.output)), 'simulated': True, 'message': '模拟演示完成；真实预测效果待验证。'}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result.get('command_success', True) else 1
    except (ValueError, OSError, KeyError, TypeError) as e:
        # Configuration/model errors do not print selected environment values or credentials.
        print(json.dumps({'status': 'error', 'message': str(e) if isinstance(e, ValueError) else type(e).__name__}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
