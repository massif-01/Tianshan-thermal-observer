"""Isolated single-thread bounded training; accepted six-start G2 fitter unchanged."""
import argparse
import sys
from pathlib import Path
from .offline_runtime import initialize
from .util import ROOT, read, write, create_bundle, legacy_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    runtime_job = read(a.out/'job-frozen.json')
    initialize(a.out, runtime_job['runtime_profile'])
    import numpy as np
    sys.path.insert(0, str(ROOT/'tool/legacy'))
    import greybox
    job, spec = read(a.out/'job-frozen.json'), read(a.out/'experiment-spec.json')
    legacy_identity()
    data = read(job['dataset'])
    segments = [s for s in data['segments'] if s['run'] in job['train_runs']]
    rows = [r for s in segments if s['eligible_for_fit'] for r in s['rows']]
    if not rows:
        write(a.out/'result.json', dict(status='insufficient_evidence', reason='no quality-eligible fitting segments', new_theta_fit=False))
        return
    powers = np.array([[r['values']['vdd_gpu'], r['values']['vdd_cpu_soc_mss']] for r in rows])
    pwm = np.array([r['values']['duty']/100 for r in rows])
    centered = np.c_[powers, pwm]-np.c_[powers, pwm].mean(axis=0)
    norms = np.linalg.norm(centered, axis=0)
    singular = np.linalg.svd(centered/np.where(norms > 0, norms, 1), compute_uv=False)
    diag = dict(fit_rows=len(rows), eligible_segments=sum(s['eligible_for_fit'] for s in segments),
                independent_runs=len(job['train_runs']), power_min=powers.min(axis=0), power_max=powers.max(axis=0),
                PWM_range=[pwm.min(), pwm.max()], normalized_input_singular_values=singular,
                independent_rail_correlation=float(np.corrcoef(powers.T)[0,1]) if np.all(powers.std(axis=0) > 0) else None,
                independent_thermal_contributions_identified=False, no_environment_temperature_fixed=True)
    write(a.out/'input-diagnostics.json', diag)
    if np.all(np.ptp(powers, axis=0) <= 1e-6) and np.ptp(pwm) <= 1e-6:
        write(a.out/'result.json', dict(status='insufficient_excitation', reason='only stationary powers/PWM; preserve previous model', new_theta_fit=False, diagnostics=diag))
        return
    greybox.build_kernel(a.out/'build')
    artifact, problem, attempts = greybox.fit('G2', segments, spec, a.out/'fits/G2')
    report = dict(status='candidate_generated' if artifact['converged'] else 'numerically_incomplete_candidate',
                  new_theta_fit=True, starts=len(attempts), parent_model_id=job['parent_model_id'],
                  selected_seed=artifact['selected_seed'], selection='training_objective_only',
                  finite_converged_attempts=sum(x['finite'] and x['converged'] for x in attempts),
                  boundary_parameters=next(x['boundary_parameters'] for x in attempts if x['seed'] == artifact['selected_seed']),
                  input_diagnostics=diag, development_only=True, future_confirmation_available=False,
                  automatic_activation=False, control_permission=False)
    manifest = create_bundle(artifact, job, a.out/'model-bundle', parent_id=job['parent_model_id'], fit_report=report)
    report['candidate_model_id'] = manifest['model_id']
    write(a.out/'result.json', report)


if __name__ == '__main__':
    main()
