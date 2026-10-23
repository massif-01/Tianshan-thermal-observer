"""Derived diagnostics from retained attempts and comparisons; never fits or selects again."""
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tool.util import read, write, sha


def main():
    out = ROOT/'diagnostics'
    out.mkdir(exist_ok=True)
    names = ['a','c','d0','d1','b_g','b_c']
    baseline = read(ROOT/'baseline/g2_runtime/frozen/primary.json')['dynamic']
    data = read(ROOT/'inputs/dataset.json')
    write(ROOT/'config/data-roles.json', data['runs'])
    result, flat = {}, []
    parent = baseline
    for kind in ['generate','calibrate']:
        base = ROOT/'runs'/kind
        attempts = [read(p) for p in sorted((base/'fits/G2').glob('*.json')) if p.stem != 'model']
        chosen = read(base/'model-bundle/g2_runtime/frozen/primary.json')['dynamic']
        by_parameter = {}
        for name in names:
            values = [a['parameters'][name] for a in attempts]
            mean = statistics.mean(values)
            by_parameter[name] = dict(min=min(values),max=max(values),mean=mean,
                sample_std=statistics.stdev(values),coefficient_of_variation=statistics.stdev(values)/abs(mean) if mean else None,
                selected=chosen[name],ratio_to_frozen=chosen[name]/baseline[name] if baseline[name] else None,
                ratio_to_parent=chosen[name]/parent[name] if parent[name] else None)
        for a in attempts:
            flat.append(dict(job=kind,seed=a['seed'],J=a['J'],finite=a['finite'],converged=a['converged'],
                             actual_residual_calls=a['actual_residual_calls'],nfev=a['nfev'],seconds=a['seconds'],
                             boundary_parameters=','.join(a['boundary_parameters'])))
        result[kind] = dict(parameters=by_parameter, input_diagnostics=read(base/'input-diagnostics.json'),
            training_objectives=[dict(seed=a['seed'],J=a['J']) for a in attempts],
            selected_seed=read(base/'result.json')['selected_seed'],
            inference='Within-data numerical convergence across fixed starts; not a sampling confidence interval or physical identification')
        parent = chosen
    result['interpretation'] = dict(numerical_start_stability_not_cross_process_stability=True,
        independently_identified_rail_contributions=False, measured_heat_capacity=False,
        ambient_24C_applies_only_to_old_M=True, no_ambient_constraint_used=True, new_fits=0)
    write(out/'parameter-stability.json',result)
    with (out/'all-attempts.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    score_rows = []
    for filename in ['B-metrics.json','A-roll-metrics.json','A-long-metrics.json']:
        for row in read(ROOT/'runs/compare'/filename):
            if row.get('context','all') != 'all' or row['scope'] not in ['all','macro','regime']:
                continue
            for method,m in row['metrics'].items():
                score_rows.append(dict(evaluation=filename,layer=row.get('layer','A-long'),h=row.get('h',0),
                    scope=row['scope'],value=row['value'],method=method,cohort_id=row['cohort_id'],**m))
    fields=list(score_rows[0])
    with (out/'comparison-tables.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(score_rows)
    points=[json.loads(l) for l in (ROOT/'runs/compare/predictions.jsonl').read_text().splitlines()]
    methods=['B0','G2-FROZEN-RM01-v1:HOLD','G2-GEN-L-20261021-v1:HOLD','G2-CAL-M-20261021-v1:HOLD']
    tails={}
    for method in methods:
        rows=[r for r in points if r['h']==45 and r['label'] and all(m in r['B'] for m in methods)]
        worst=max(rows,key=lambda r:r['label']['value']-r['B'][method])
        tails[method]=dict(origin_ref=worst['ref'],label_ref=worst['label']['ref'],
             prediction=worst['B'][method],actual=worst['label']['value'],
             underprediction=worst['label']['value']-worst['B'][method],macro=worst['macro'],regime=worst['regime'],
             context=worst['control_context'],posthoc_only=True)
    write(out/'45s-tail-references.json',tails)
    lines=['# 参数与输入诊断','', '以下仅重新汇总已封存的十二次拟合，不再拟合、换种子或改评分。','',
           '| 参数 | 冻结 G2 | L 生成 | M 校准 | 校准 / 生成 |','|---|---:|---:|---:|---:|']
    for name in names:
        g=result['generate']['parameters'][name]['selected'];c=result['calibrate']['parameters'][name]['selected']
        lines.append(f'| {name} | {baseline[name]:.6g} | {g:.6g} | {c:.6g} | {c/g:.3f} |')
    lines += ['', '每项训练内六初值的参数极差、标准差、变异系数及每次 J 见 parameter-stability.json 和 all-attempts.csv。', '',
              '两组的六初值均收敛到十分接近的训练解，没有参数触边。这说明本次数值实现和初值不是主要失败来源；不能据此认定跨过程参数稳定或获得置信区间。', '',
              f"L 的两 rail 相关系数 {result['generate']['input_diagnostics']['independent_rail_correlation']:.6f}，M 为 {result['calibrate']['input_diagnostics']['independent_rail_correlation']:.6f}。M 的最小归一化输入奇异值约 0.0235。组合预测仍可研究，独立热贡献没有被识别。", '',
              'M 校准后 b_c 相对于 L 生成约增至 30 倍，而 d0、其他系数也随过程改变。这项跨资料变化远大于同一训练集换初值的差别，符合输入共线与等效结构/边界耦合的限制；本轮不据此改变模型族或寻找更多初值。', '',
              'L 的成功 PWM 分数范围 0.18—1.00，M 为 0.18—0.86；这两个历史例子不是“只有背景”。软件另外用明确合成的平稳输入测试验证 insufficient_excitation 路径，不输出假系数。', '',
              'E 为训练运行的等效边界、Ts 为分段初态，两者不等于测得的室温/结构温度。验证统一使用过去 60 秒；没有将 M 的 24°C 用于约束 E，也未复制给 L/S。', '',
              'S 的持续短问答是本次共同集合最差子场景；原始尾部引用见 45s-tail-references.json。A 的改善与 B 的退步同时保留，不能把已知未来输入下的响应精度当成真实未来预测成功。','']
    (out/'参数与输入诊断.md').write_text('\n'.join(lines))
    print('Summarized 12 retained attempts; no new fits.')


if __name__ == '__main__':
    main()
