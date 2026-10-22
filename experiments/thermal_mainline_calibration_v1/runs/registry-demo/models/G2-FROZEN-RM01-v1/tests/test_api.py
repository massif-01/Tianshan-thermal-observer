import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from g2_runtime import Predictor


def samples():
    return json.loads((ROOT/'golden/cases.json').read_text())['cases']


def test_golden_and_same_clock_budget():
    p = Predictor()
    for case in samples():
        actual = p.predict(**case['input'])
        for a, b in zip(actual, case['expected']):
            assert a['method'] == b['method'] and a['horizon_s'] == b['horizon_s']
            assert a['unavailable_reasons'] == b['unavailable_reasons']
            if b['value_C'] is None:
                assert a['value_C'] is None
            else:
                assert abs(a['value_C']-b['value_C']) < 1e-8
            assert a['target_mono_s'] == case['input']['origin']['received_at_mono_s']+a['horizon_s']
            assert a['control_permission'] is False


def test_no_mutation_and_no_future_history_leak():
    p = Predictor()
    args = copy.deepcopy(samples()[0]['input'])
    before = copy.deepcopy(args)
    first = p.predict(**args)
    assert before == args
    future = dict(args['origin'], received_at_mono_s=args['origin']['received_at_mono_s']+1, value_C=999)
    args['history'].append(future)
    assert p.predict(**args) == first


def test_published_after_target_never_live_forecast():
    p = Predictor()
    args = copy.deepcopy(samples()[0]['input'])
    args['publication_mode'] = 'live'
    args['issued_at']['mono_s'] = args['origin']['received_at_mono_s']+46
    result = p.predict(**args)
    assert all(r['value_C'] is None and 'issued_at_or_after_target' in r['unavailable_reasons'] for r in result if r['horizon_s'] in (15, 45))
    assert all(r['late'] is False for r in result if r['horizon_s'] == 90)


def test_foreign_clock_run_and_future_state_rejected():
    p = Predictor()
    for change, reason in [('clock', 'clock_domain_unassociated'), ('run', 'state_model_run_or_epoch_mismatch'), ('future', 'state_not_at_TJ_origin')]:
        args = copy.deepcopy(samples()[0]['input'])
        if change == 'clock': args['issued_at']['clock_domain'] = 'FOREIGN'
        elif change == 'run': args['identity']['run_id'] = 'FOREIGN'
        else: args['observed_through']['mono_s'] += 1
        assert all(r['value_C'] is None and reason in r['unavailable_reasons'] for r in p.predict(**args))


def test_observer_unavailable_preserves_B0_and_risk():
    p = Predictor();args = copy.deepcopy(samples()[0]['input'])
    args['state']['observer'].update(available=False, phase='unavailable', reasons=['long_missing_last_successful_pwm'])
    args['state']['safety']['guard'] = True
    result = p.predict(**args)
    assert all(r['value_C'] is None for r in result if r['method'] == 'G2-HOLD')
    assert all(r['value_C'] == args['origin']['value_C'] for r in result if r['method'] == 'B0')
    assert all(r['original_safety']['guard'] is True for r in result)
