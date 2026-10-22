"""Extract reference C functions into host-only experiment, instrument, compile, run.
No editing firmware, no model of temperature response, no parameter fitting."""
import csv
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
SCRIPTS=OUT/'scripts'


def main():
    source=(OUT/'sources/ts_fan.reference.c').read_text()
    def function(name):
        m=re.search(r'^(?:static )?(?:float|void|bool|uint8_t|esp_err_t) '+name+r'\([^;]*?\)\n\{',source,re.M)
        assert m,name
        return source[m.start():source.index('\n}',m.start())+2]
    names=['calc_duty_from_curve','clamp_float','apply_duty_limits',
           'is_temp_data_basic_valid','is_auto_temp_data_usable','reset_adaptive_auto_state',
           'get_adaptive_temperatures','record_auto_temp_sample','calculate_auto_slope',
           'apply_auto_rate_limit','update_response_learning','update_guard_observation',
           'apply_adaptive_auto','update_pwm']
    core='\n\n'.join(function(n) for n in names)
    # Only instrument intermediates plus the proposed additional permission.
    needle='    bool allow_down = (guard_temp <= FAN_AUTO_GUARD_RELEASE_TEMP) &&\n                      (!slope_valid || fan->slope_c_per_min <= 0.0f);'
    assert core.count(needle)==1
    replacement=needle+'''\n    observed_baseline = baseline;
    observed_demand = target;
    observed_original_permission = allow_down;
    if (use_release && !allow_down) {
        observed_extra_permission = extra_release(fan, temp_data, target, baseline, now_ms);
        allow_down = allow_down || observed_extra_permission;
    } else {
        release_state.open = false;
    }'''
    core=core.replace(needle,replacement)
    stale='        fan->temp_stale = true;'
    core=core.replace(stale,stale+'\n        reset_extra_release();',1)
    guard='    if (fan->guard_active) {\n        fan->auto_state = TS_FAN_AUTO_STATE_GUARD;'
    assert core.count(guard)==1
    core=core.replace(guard,'    if (fan->guard_active) {\n        reset_extra_release();\n        fan->auto_state = TS_FAN_AUTO_STATE_GUARD;',1)
    # Helper must be declared after basic validity functions and before adaptive control.
    marker='static esp_err_t apply_adaptive_auto('
    core=core.replace(marker,(SCRIPTS/'release_gate.inc').read_text()+'\n'+marker,1)
    definitions=source[source.index('#define FAN_AUTO_GUARD_TEMP '):source.index('/*===========================================================================*/',source.index('typedef struct {'))]
    (OUT/'sources/fan_types.inc').write_text(definitions)
    (OUT/'sources/fan_core.instrumented.inc').write_text(core)
    # Snapshot reconstruction: observer arrival as tick, each valid fan snapshot as a fresh report.
    # It is not a firmware trace. Long-window history starts empty; actual hidden learning state unknown.
    run=next((ROOT/'evidence/short-qa-20261013').glob('run-*'))
    snapshots=[]
    for line in (run/'observations-0001.jsonl').open():
        r=json.loads(line)
        if r['kind']!='fan':continue
        fans=r['payload'].get('data',{}).get('fans',[])
        if not fans:continue
        f=fans[0]
        snapshots.append((r,f))
    first=snapshots[0][0]['mono_s']
    replay=OUT/'results/replay-input.csv'
    with replay.open('w') as out:
        w=csv.writer(out);w.writerow(['second','temperature_tenths','valid','observed_pwm','observed_gain'])
        for r,f in snapshots:
            w.writerow([r['mono_s']-first,round(f['control_temperature']*10),int(not f['temp_stale']),f['duty'],f['controller_gain']])
    commands=[]
    with tempfile.TemporaryDirectory(prefix='tto-offline-control-') as tmp:
        p=Path(tmp)
        (p/'fan_types.inc').write_text(definitions)
        (p/'fan_core.inc').write_text(core)
        exe=p/'controller'
        includes=OUT/'sources/fan_harness'
        cmd=['cc','-std=c11','-g','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-parameter',
             '-fsanitize=address,undefined','-I'+str(includes/'tests/fan_monitor/stubs'),
             '-I'+str(includes/'components/ts_drivers/include'),'-I'+tmp,
             str(SCRIPTS/'control_harness.c'),'-lm','-o',str(exe)]
        cp=subprocess.run(cmd,text=True,capture_output=True)
        (OUT/'results/control-build.log').write_text(cp.stdout+cp.stderr)
        cp.check_returncode();commands.append(cmd)
        variants=[('reference-native-gain',0,0,0),('release-native-gain',1,0,0),('reference-fixed-gain',0,1,0),
                  ('user-curve-reference-sensitivity',0,0,1)]
        for label,release,fixed,user in variants:
            cmd=[str(exe),str(release),str(replay),str(fixed),str(user),label]
            with (OUT/'results'/f'control-{label}.csv').open('w') as f:
                subprocess.run(cmd,stdout=f,check=True)
            commands.append(cmd)
        for release in (0,1):
            cmd=[str(exe),str(release),'fixtures']
            with (OUT/'results'/f'fixtures-release-{release}.csv').open('w') as f:
                subprocess.run(cmd,stdout=f,check=True)
            commands.append(cmd)
    result=dict(reference_source_sha256=hashlib.sha256(source.encode()).hexdigest(), commands=commands,
                firmware_commit='88dd98079ce14d2180afef8efc41d742735568da',
                input='1261 raw fan snapshots; observer receive monotonic time; no temperature plant',
                curve='current read-back assumed; separate user-curve sensitivity, never historical proof',
                initial_state='observed first PWM and gain, empty temperature history, no pending learning observation',
                fresh_report_assumption='every valid snapshot is a new report; source report identity/timestamp missing from fan API',
                fixed_gain='1.8686946630477905 held only in isolated reference-fixed-gain comparator',
                evidence_limit='Counterfactual PWM on the same temperature sequence does not show that lower airflow would maintain measured temperatures.',
                assertions='short/dense pulse, warming, reheat, jitter, guard, stale/recovery; original limits/demand floor, successful PWM; ASAN/UBSAN',
                status='passed')
    (OUT/'results/control-prototype-identity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASS source-extracted control experiment; four replay variants and eight narrow fixtures; no device I/O')


if __name__=='__main__':main()
