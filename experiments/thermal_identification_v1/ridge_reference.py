"""Frozen 9/15-column compact Ridge and independent horizon eligibility."""
import numpy as np
from sklearn.linear_model import Ridge
from common import balanced_weights,write

TJ_COLUMNS=['tj']+[f'lag_{h}_minus_current' for h in (5,15,30,60)]+[f'mean_{h}_minus_current' for h in (10,30)]+['slope_10','slope_30']
IO_COLUMNS=TJ_COLUMNS+['u','u_mean30','Pg','Pg_mean30','Pc','Pc_mean30']


def label_index(times,i,h,tolerance=2.):
    j=np.searchsorted(times,times[i]+h)
    return int(j) if j<len(times) and times[j]<=times[i]+h+tolerance else None


def held_mean(times,values,start,end):
    lo=np.searchsorted(times,start,side='right')-1
    hi=np.searchsorted(times,end,side='left')
    if lo<0:return None
    durations=np.diff(np.r_[start,times[lo+1:hi],end])
    return np.dot(durations,values[lo:hi])/(end-start)


def features(segment,i):
    # Slice the observation prefix: no future measurement enters even the helper.
    rows=segment['rows'][:i+1]
    t=np.array([a['mono_s'] for a in rows]);y=np.array([a['values']['tj'] for a in rows]);now=t[-1]
    slope={}
    for h in (10,30):
        j=np.searchsorted(t,now-h)
        slope[h]=(y[-1]-y[j])/(now-t[j]) if now-t[j]>=min(10,h-2) else None
    if now-t[0]<60:return None,None,slope[30]
    vals=[y[-1]]
    for h in (5,15,30,60):
        j=np.searchsorted(t,now-h,side='right')-1
        if j<0 or now-h-t[j]>2:return None,None,slope[30]
        vals.append(y[j]-y[-1])
    vals += [held_mean(t,y,now-h,now)-y[-1] for h in (10,30)]
    vals += [slope[10],slope[30]]
    nodes=[n for n in segment['timeline'] if n['t']<=now]
    nt=np.array([n['t'] for n in nodes]);u=np.array([n['inputs'] for n in nodes])
    io=[]
    for k in (2,0,1):io.extend([u[-1,k],held_mean(nt,u[:,k],now-30,now)])
    return np.array(vals),np.r_[vals,io],slope[30]


def examples(data):
    out=[]
    for segment in data['segments']:
        times=np.array([r['mono_s'] for r in segment['rows']])
        for i,a in enumerate(segment['rows']):
            tj,io,slope=features(segment,i)
            row=dict(run=segment['run'],segment=segment['id'],i=i,t=times[i],ref=a['ref'],utc=a['utc'],wall=a['wall'],
                     macro=a['macro'],phase=a['phase'],regime=a['regime'],duration=a['duration'],current=a['values']['tj'],
                     R_TJ=tj,R_IO=io,slope=slope,labels={})
            for h in (15,45,90):
                j=label_index(times,i,h)
                if j is not None:
                    label=segment['rows'][j]
                    row['labels'][str(h)]=dict(value=label['values']['tj'],ref=label['ref'],t=times[j],offset_s=times[j]-times[i]-h)
            out.append(row)
    return out


def fit_one(rows,name,h,lam):
    X=np.array([r[name] for r in rows]);y=np.array([r['labels'][str(h)]['value']-r['current'] for r in rows])
    w=balanced_weights(rows);mean=np.average(X,axis=0,weights=w);scale=np.sqrt(np.average((X-mean)**2,axis=0,weights=w));scale[scale<1e-12]=1
    fit=Ridge(alpha=lam*w.sum(),fit_intercept=True,solver='svd').fit((X-mean)/scale,y,sample_weight=w)
    return dict(lambda_=lam,alpha=lam*w.sum(),mean=mean,scale=scale,coef=fit.coef_,intercept=float(fit.intercept_),n=len(rows),
                min=X.min(axis=0),max=X.max(axis=0),weight_sum=float(w.sum()),groups=sorted({r['segment'] for r in rows}))


def predict(model,vector,current):
    return float(current+np.dot((vector-np.array(model['mean']))/model['scale'],model['coef'])+model['intercept'])


def fit_ridges(rows,runs,spec,out):
    result=dict(schema='TTO-COMPACT-RIDGE-EXPERIMENT-v1',deployable=False,fit_runs=runs,methods={})
    for name in ('R_TJ','R_IO'):
        result['methods'][name]={}
        for h in (15,45,90):
            eligible=[r for r in rows if r['run'] in runs and r[name] is not None and str(h) in r['labels']]
            groups=sorted({r['segment'] for r in eligible});nfold=min(3,len(groups));cv=[]
            fold={g:i%nfold for i,g in enumerate(groups)} if nfold else {}
            if nfold>=2:
                for lam in spec['ridge']['lambda_grid']:
                    fold_scores=[]
                    for k in range(nfold):
                        train=[r for r in eligible if fold[r['segment']]!=k];validation=[r for r in eligible if fold[r['segment']]==k]
                        candidate=fit_one(train,name,h,lam)
                        errors=np.array([abs(predict(candidate,r[name],r['current'])-r['labels'][str(h)]['value']) for r in validation])
                        fold_scores.append(dict(fold=k,score=float(np.dot(balanced_weights(validation),errors)),train_groups=candidate['groups'],validation_groups=sorted({r['segment'] for r in validation}),n_train=len(train),n_validation=len(validation)))
                    cv.append(dict(lambda_=lam,score=float(np.mean([v['score'] for v in fold_scores])),folds=fold_scores))
                best=min(v['score'] for v in cv);selected=max(v['lambda_'] for v in cv if v['score']<=best+spec['ridge']['near_tie_C'])
            else:selected=spec['ridge']['CV_fallback_lambda']
            head=fit_one(eligible,name,h,selected)
            head.update(cv=cv,selection='whole_segment_fit_side_CV' if nfold>=2 else 'insufficient_groups_fixed_lambda_1',fold_assignment=fold,
                        columns=TJ_COLUMNS if name=='R_TJ' else IO_COLUMNS,training_refs=[r['ref'] for r in eligible])
            result['methods'][name][str(h)]=head
    write(out,result)
    return result
