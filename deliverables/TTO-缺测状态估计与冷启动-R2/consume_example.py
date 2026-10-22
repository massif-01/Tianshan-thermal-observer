"""#10 read-only offline consumption example. No request, scheduling, polling or device API."""
from pathlib import Path
import argparse, json


def summarize(snapshot):
    assert snapshot['schema']=='TTO-STATE-READONLY-R2-v1'
    ob=snapshot['observer'];safety=snapshot['safety'];permission=snapshot['permission']
    return dict(run_id=snapshot['identity']['run_id'],phase=ob['phase'],
                conditional_state_available=ob['available'], model_evidence_tracking=ob['phase']=='tracking',
                current_measurement_context_confirmed_normal=safety['confirmed_normal_now'],
                field_authorization_present=permission['formal_field_authorized'],
                formal_comparison_allowed=False,
                reason='This consumer only displays model evidence; #10 must combine measurement/safety/instrument/clock/explicit authorization. No launch action exists.',
                values=dict(Tf_C=ob['Tf_C'],Ts_C=ob['Ts_C'],E_C=ob['E_C']),
                reasons=ob['reasons'],last_observed_ref=snapshot['observed_through_ref'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('state_jsonl',type=Path);a=p.parse_args()
    with a.state_jsonl.open() as f:
        for line in f:
            if line.strip():print(json.dumps(summarize(json.loads(line)),ensure_ascii=False))


if __name__=='__main__':main()
