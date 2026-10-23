"""Original fixed-dynamics initialization/propagation on the new run. No training calls."""
from pathlib import Path
import bisect,collections,math,sys
import numpy as np
ROOT=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'vendor'))
from common import read,write,sha
import greybox
from initialize import estimate,rolling_state,path_between
from slowstate_core import filters_at_origins,BRANCHES,error_metrics

PARAMS=['a','c','d0','d1','b_g','b_c']

def jsonl(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def cast(x):return x.tolist() if isinstance(x,np.ndarray) else x.item() if isinstance(x,np.generic) else str(x)
    with path.open('w') as f:
        for r in rows:f.write(__import__('json').dumps(r,ensure_ascii=False,allow_nan=False,default=cast)+'\n')


def qualified_support(nodes):
    """Union of actual native-qualified intervals; expiry and abnormal nodes terminate support."""
    intervals=[]
    for i,n in enumerate(nodes):
        end=min(n['valid_until'],nodes[i+1]['t'] if i+1<len(nodes) else n['t'])
        if not n['complete'] or end<=n['t']:continue
        key=(n['source_epoch'],n['segment'])
        if intervals and intervals[-1]['key']==key and abs(intervals[-1]['end']-n['t'])<1e-9:
            intervals[-1]['end']=end;intervals[-1]['refs'].append(n['ref'])
        else:intervals.append(dict(start=n['t'],end=end,key=key,refs=[n['ref']]))
    return intervals


def generate(data,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);greybox.build_kernel(out/'build')
    supports=qualified_support(data['nodes']);support_times=[x['start'] for x in supports]
    calibrations={};longs=[];states=[];primary_by_ref={};model_by_name={}
    for name in ['primary','old_LS','A24']:
        model=read(ROOT/'models'/(name+'.json'));p=[model['dynamic'][k] for k in PARAMS];model_by_name[name]=model
        boundary=None;fallback=float(np.median([v for k,v in model['parameters'].items() if k.startswith('E_')]))
        calibrations[name]={};local=[]
        for segment in data['segments']:
            if segment['span_s']<60:continue
            end=segment['rows'][0]['t']+60
            cal=estimate('G2',p,segment,end,60,E=boundary,E_fallback=fallback)
            if boundary is None:boundary=cal['E']
            assert cal['end']==end and cal['last_ref'] in {a['ref'] for a in segment['rows'] if a['t']<=end+1e-9}
            calibrations[name][segment['id']]=dict(cal,boundary_policy='once_per_run_then_fixed',model_sha256=sha(ROOT/'models'/(name+'.json')))
            arrays=greybox.arrays(segment);all_z=greybox.propagate('G2',p,boundary,arrays['dt'],arrays['u'],[arrays['y'][0],cal['Ts_initial']])
            filters=filters_at_origins(segment,boundary,p) if name=='primary' else None
            for i,row in enumerate(segment['rows']):
                if row['t']<end:continue
                z=all_z[row['timeline_index']]
                common=dict(model=name,model_sha256=sha(ROOT/'models'/(name+'.json')),run_id=data['run_id'],ref=row['ref'],
                    segment=segment['id'],source_epoch=row['source_epoch'],t=row['t'],utc=row['utc'],wall=row['wall'],
                    phase=row['phase'],E=boundary,measured_TJ=row['values']['tj'],
                    input_rails_W_PWM=segment['timeline'][row['timeline_index']]['inputs'],
                    external_temperature_used=False,parameter_learning=False)
                longs.append(dict(common,Tf=float(z[0]),Ts=float(z[1]),initialization_end=end,no_TJ_feedback_after_prefix=True))
                state,ev=rolling_state('G2',p,boundary,segment,i,60)
                record=dict(common,Tf_observation_anchor=float(state[0]),Ts=float(state[1]),initialization=ev,input_cutoff=row['t'],
                    source_TJ_valid_until=row['source_valid_until'],Tf_A_long=float(z[0]),Ts_A_long=float(z[1]),
                    branches=dict(filters[row['ref']],**{'STATE-G2':float(state[1])}) if filters else None)
                assert ev['end']<=row['t'] and state[0]==row['values']['tj']
                local.append(record)
                if name=='primary':primary_by_ref[row['ref']]=record
        for i,s in enumerate(local):
            j=bisect.bisect_right(support_times,s['t'])-1
            assert j>=0 and supports[j]['start']<=s['t']<supports[j]['end']
            deadline=supports[j]['end']
            if i+1<len(local):deadline=min(deadline,local[i+1]['t'])
            s['valid_until']=deadline;s['qualification_support_ref']=j
        states+=local
        print('Generated',name,len(local),'causal states',len(calibrations[name]),'initialized segments, E',boundary,flush=True)
    write(out/'calibrations.json',calibrations);write(out/'qualified-support.json',supports)
    jsonl(out/'states-causal60.jsonl',states);jsonl(out/'states-A-long.jsonl',longs)
    # Secondary TJ check, inherited A/B and per-horizon label contract; all four branches share origin/label.
    segmap={s['id']:s for s in data['segments']};points=[]
    model=model_by_name['primary'];p=[model['dynamic'][k] for k in PARAMS]
    for row in data['examples']:
        state=primary_by_ref.get(row['ref']);seg=segmap.get(row['segment'])
        for h in [15,45,90]:
            pred=dict(ref=row['ref'],t=row['t'],utc=row['utc'],phase=row['phase'],h=h,label=row['labels'][str(h)],
                context=row['contexts'][str(h)],label_rejection=row['label_rejections'][str(h)],
                B_HOLD={},A_roll={},baselines={},current=row['current'],input_cutoff=row['t'])
            if row['source_valid']:pred['baselines']['B0']=row['current']
            if row['source_valid'] and row['slope'] is not None:pred['baselines']['B1']=row['current']+h*row['slope']
            if state is not None:
                current=np.asarray(state['input_rails_W_PWM']);pred['state_ref']=state['ref']
                future_ok=row['A_eligible'][str(h)] and row['t']+h<=seg['rows'][-1]['t']
                if future_ok:dts,inputs=path_between(seg,row['t'],row['t']+h)
                for branch in BRANCHES:
                    initial=[row['current'],state['branches'][branch]]
                    pred['B_HOLD'][branch]=float(greybox.forecast('G2',p,state['E'],initial,current,h,'HOLD',model['P10_fit']))
                    if future_ok:pred['A_roll'][branch]=float(greybox.propagate('G2',p,state['E'],dts,inputs,initial)[-1,0])
            points.append(pred)
    jsonl(out/'TJ-predictions.jsonl',points)
    metrics=[]
    for kind in ['A_roll','B_HOLD']:
        for h in [15,45,90]:
            base=[r for r in points if r['h']==h and r['label'] is not None and len(r[kind])==4 and 'B1' in r['baselines']]
            for phase in ['all']+sorted({r['phase'] for r in points}):
                for context in ['all','confirmed_normal','aux_observation_gap','observed_abnormal_or_changed','unclassified_gap']:
                    cohort=[r for r in base if (phase=='all' or r['phase']==phase) and (context=='all' or r['context']==context)]
                    if not cohort:continue
                    error={b:error_metrics([r[kind][b]-r['label']['value'] for r in cohort]) for b in BRANCHES}
                    baseline={b:error_metrics([r['baselines'][b]-r['label']['value'] for r in cohort]) for b in ['B0','B1']}
                    metrics.append(dict(kind=kind,h=h,phase=phase,context=context,n=len(cohort),metrics=error,baselines=baseline,
                        primary_TJ_target_not_surface_truth=True))
    write(out/'TJ-metrics.json',metrics)
    coverage=[]
    for phase in ['all']+sorted({a['phase'] for a in data['samples']}):
        rows=[a for a in data['samples'] if phase=='all' or a['phase']==phase]
        eligible=[s for s in states if s['model']=='primary' and (phase=='all' or s['phase']==phase)]
        coverage.append(dict(phase=phase,accepted_TJ=len(rows),source_valid_TJ=sum(a['target_valid'] for a in rows),
            model_state_origins=len(eligible),model_held_support_s=sum(s['valid_until']-s['t'] for s in eligible),
            point_fraction=len(eligible)/len(rows) if rows else None))
    write(out/'model-coverage.json',coverage)
    return states,longs,points
