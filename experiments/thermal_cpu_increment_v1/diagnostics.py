"""Additional descriptive metrics; no threshold/fit/lag search."""
import argparse
import bisect
from pathlib import Path
from common import ROOT, read, lines, write
from analyse import seconds


def diagnostics(result,out):
    c=read(ROOT/'candidate.json')
    frames=list(lines(result/'feature-frames.jsonl'))
    outputs=list(lines(result/'activity-and-candidate-predictions.jsonl'))
    requests=list(lines(result/'actual-client-events.jsonl'))
    thresholds={name:{side:c['levels']['idle'][name]+c[side]*(c['levels']['active'][name]-c['levels']['idle'][name])
                      for side in ('on','off')} for name in c['variants']['INPUT-CORE']}
    total={n:dict(common_known_s=0.,common_background_s=0.,common_background_ACTIVE_s=0.,common_background_ACTIVE_events=0)
           for n in c['variants']}
    previous={n:False for n in c['variants']}
    cpu_only=[]
    for i,(f,r) in enumerate(zip(frames,outputs)):
        wall=seconds(f['arrived_at_utc'])
        if (r['variants']['INPUT-MEAN']['activity']['state']=='ACTIVE'
                and r['variants']['INPUT-BASE']['activity']['state']!='ACTIVE'):
            cpu_only.append(dict(ref=f['native_ref'],cpu_mean_pct=f['features']['cpu_mean_pct']['value'],
                cpu_max_pct=f['features']['cpu_max_pct']['value'],
                CPU_mean_score=r['variants']['INPUT-MEAN']['activity']['feature_scores'].get('cpu_mean_pct'),
                BASE_score=r['variants']['INPUT-BASE']['activity']['score']))
        if i+1==len(frames):continue
        end=seconds(frames[i+1]['arrived_at_utc'])
        cuts={wall,end}
        for v in r['variants'].values():
            until=v['activity']['supported_until_mono_s']
            if until is not None:
                bound=wall+until-f['arrival_mono_s']
                if wall<bound<end:cuts.add(bound)
        for q in requests:
            for t in (q['submit_wall'],q['done_wall']):
                if t is not None and wall<t<end:cuts.add(t)
        cuts=sorted(cuts)
        for left,right in zip(cuts,cuts[1:]):
            all_known=all(v['activity']['state']!='UNKNOWN' and v['activity']['supported_until_mono_s'] is not None
                and (left-wall)<v['activity']['supported_until_mono_s']-f['arrival_mono_s'] for v in r['variants'].values())
            bg=not any(q['submit_wall']<=(left+right)/2<(q['done_wall'] if q['done_wall'] is not None else end) for q in requests)
            for n in c['variants']:
                a=total[n];a['common_known_s']+=(right-left)*all_known
                a['common_background_s']+=(right-left)*(all_known and bg)
                active=all_known and bg and r['variants'][n]['activity']['state']=='ACTIVE'
                a['common_background_ACTIVE_s']+=(right-left)*active
                if active and not previous[n]:a['common_background_ACTIVE_events']+=1
                previous[n]=active
    write(out,dict(role='posthoc root-cause and common-availability accounting; no candidate selection',
        fixed_thresholds_in_original_units=thresholds,common_activity=total,
        CPU_mean_active_while_BASE_not_active_frames=len(cpu_only),CPU_only_examples=cpu_only,
        cause='Generic CPU bursts are not specific inference activity. OR plus hysteresis can keep a resident-model active power floor through background CPU activity. No new heat term, numerical retuning or causal-lag search.',
        CORE_vs_MEAN_incremental_states=0,real_high_frequency_data=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();diagnostics(a.result,a.output)
