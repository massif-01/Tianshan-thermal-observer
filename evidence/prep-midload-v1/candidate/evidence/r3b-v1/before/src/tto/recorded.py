"""Historical prediction/score facts only. Never loads or runs a model."""
import json
from collections import Counter
from pathlib import Path
from .evaluation import METHODS, group_metrics
from .model import HORIZONS
from .util import file_hash, finite


def recorded_results(run, manifest):
    run = Path(run)
    logs, issues = {}, []
    def read_log(name):
        path = run / name
        logs[name] = {'present': path.is_file(), 'sha256': file_hash(path) if path.is_file() else None, 'record_count': None}
        if not path.is_file():
            return []
        rows = []
        with path.open() as f:
            for index, line in enumerate(f, 1):
                ref = f'{name}:{index}'
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError('record is not an object')
                    rows.append((ref, row))
                except ValueError:
                    issues.append({'record_ref': ref, 'reason': 'invalid_JSON_record'})
        logs[name]['record_count'] = len(rows)
        return rows
    predictions = {}
    for ref, p in read_log('predictions.jsonl'):
        if p.get('id') in predictions:
            issues.append({'record_ref': ref, 'reason': 'duplicate_prediction_identity'})
            continue
        if not isinstance(p.get('id'), str) or p.get('origin', {}).get('run_id') != manifest['observer_run_id']:
            issues.append({'record_ref': ref, 'reason': 'prediction_run_identity_mismatch'})
            continue
        predictions[p['id']] = (ref, p)
    scores = {}
    for ref, score in read_log('scores.jsonl'):
        key = (score.get('prediction_id'), score.get('horizon_s'))
        if key[0] not in predictions or key[1] not in HORIZONS:
            issues.append({'record_ref': ref, 'reason': 'unmatched_prediction_or_horizon'})
            continue
        _, prediction = predictions[key[0]]
        if 'model_sha256' in score and score['model_sha256'] != prediction.get('model_sha256'):
            issues.append({'record_ref': ref, 'reason': 'score_model_identity_mismatch'})
            continue
        if key in scores:
            issues.append({'record_ref': ref, 'reason': 'duplicate_terminal_score'})
            continue
        scores[key] = (ref, score)
    models, points, origins = {}, [], {}
    for id_, (prediction_ref, p) in predictions.items():
        model = p.get('model_sha256')
        key = model or 'baseline_no_model'
        group = models.setdefault(key, {'model_sha256': model, 'prediction_origins': 0, 'actual_methods': Counter(), 'fallback_origins': 0, 'unavailable_method_reasons': {m:Counter() for m in METHODS}, 'horizons': {str(h): {'issued_origins':0,'scored_origins':0,'unscored_reasons':Counter(),'methods':{m:{'issued':0,'scored':0,'unscored_reasons':Counter()} for m in METHODS}} for h in HORIZONS}})
        group['prediction_origins'] += 1
        group['actual_methods'][p.get('actual_method','unknown')] += 1
        group['fallback_origins'] += int(p.get('fallback') is True)
        for method,reason in p.get('unavailable',{}).items():
            if method in METHODS:
                group['unavailable_method_reasons'][method][reason] += 1
        origin = p['origin']
        origins[id_] = {'prediction_record_ref':prediction_ref,'origin_ref':origin['ref'],'raw_refs':origin.get('raw_refs',[]),'model_sha256':model,'actual_method':p.get('actual_method'),'origin_t':origin['t']}
        for h in HORIZONS:
            hk = str(h); counts = group['horizons'][hk]; counts['issued_origins'] += 1
            score_ref, score = scores.get((id_,h), (None,{}))
            status = score.get('status','no_terminal_score_yet')
            scored_methods = 0
            for method in METHODS:
                predicted = p.get('values',{}).get(method,{}).get(hk)
                if not finite(predicted):
                    continue
                mc = counts['methods'][method]; mc['issued'] += 1
                error = score.get('errors',{}).get(method)
                if status != 'scored' or not finite(error) or not finite(score.get('truth')):
                    reason = status if status != 'scored' else 'method_score_missing'
                    mc['unscored_reasons'][reason] += 1
                    continue
                if abs((predicted-score['truth'])-error)>1e-9:
                    issues.append({'record_ref':score_ref,'reason':'saved_error_disagrees_with_saved_prediction','method':method})
                    mc['unscored_reasons']['inconsistent_saved_score'] += 1
                    continue
                mc['scored'] += 1; scored_methods += 1
                points.append({'id':id_,'episode':origin['episode'],'run_id':origin['run_id'],'segment':origin['segment'],'origin_t':origin['t'],'target_t':origin['t']+h,'label_t':score['label_t'],'label_ref':score['label_ref'],'origin_ref':origin['ref'],'prediction_record_ref':prediction_ref,'score_record_ref':score_ref,'horizon_s':h,'method':method,'actual_method':p.get('actual_method'),'model_sha256':model,'prediction':predicted,'truth':score['truth'],'error':error,'phase':origin['phase'],'high_temperature':origin['high_temperature']})
            if scored_methods:
                counts['scored_origins'] += 1
            else:
                counts['unscored_reasons'][status if status!='scored' else 'method_score_missing'] += 1
    for key, group in models.items():
        for h, counts in group['horizons'].items():
            for method, mc in counts['methods'].items():
                matching = [p for p in points if (p['model_sha256'] or 'baseline_no_model')==key and p['horizon_s']==int(h) and p['method']==method]
                mc['output_fraction'] = mc['issued']/counts['issued_origins'] if counts['issued_origins'] else None
                mc['coverage_fraction'] = mc['scored']/counts['issued_origins'] if counts['issued_origins'] else None
                mc['score_fraction_of_issued'] = mc['scored']/mc['issued'] if mc['issued'] else None
                mc['metrics'] = group_metrics(matching)
                if not logs['scores.jsonl']['present']:
                    mc['scored'] = mc['coverage_fraction'] = mc['score_fraction_of_issued'] = None
                    mc['metrics'] = {'time_pooled': {'n': None, 'status': 'evidence_missing'}, 'episode_equal_macro': {'status': 'evidence_missing'}, 'episodes': {}, 'time_weighted': {'status': 'evidence_missing'}}
            if not logs['scores.jsonl']['present']:
                counts['scored_origins'] = None
    missing = [name for name,details in logs.items() if not details['present']]
    return {'source':'persisted_predictions_and_scores','logs':logs,'missing_logs':missing,'log_evidence_complete':not missing and not issues,'issues':issues,'models':models,'issued_prediction_origins':len(predictions) if logs['predictions.jsonl']['present'] else None,'terminal_score_records':logs['scores.jsonl']['record_count'],'matched_terminal_score_records':len(scores),'scored_method_horizon_records':len(points) if all(v['present'] for v in logs.values()) else None,'prediction_references':origins,'scored_records':points}, points
