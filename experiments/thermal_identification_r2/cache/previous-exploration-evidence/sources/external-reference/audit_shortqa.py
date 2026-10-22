"""Read-only audit of the short-QA evidence; writes only a new output file.
No device/network access. Inputs must be the supplied, extracted evidence folder.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, math
from pathlib import Path

def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def jsonl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists(): raise SystemExit('Output already exists; choose a new file.')
    runs=list(a.input.glob('run-*'))
    if len(runs)!=1: raise SystemExit('Expected exactly one extracted run directory.')
    r=runs[0]
    manifest=readj(r/'manifest.json'); index=readj(r/'files.json')
    hashes={name:hashlib.sha256((r/name).read_bytes()).hexdigest()==sha for name,sha in index.items()}
    if not all(hashes.values()): raise SystemExit('Run hash mismatch; do not evaluate altered data.')
    obs=jsonl(r/'observations-0001.jsonl'); events=jsonl(r/'events.jsonl'); predictions=jsonl(r/'predictions.jsonl'); scores=jsonl(r/'scores.jsonl')
    requests=readj(a.input/'normalized-requests.json')
    fs=[]
    for o in obs:
        if o['kind']=='fan' and isinstance(o.get('payload'),dict):
            f=next((f for f in o['payload'].get('data',{}).get('fans',[]) if f.get('id')==0),None)
            if f is not None: fs.append(dict(f,mono=o['mono_s'],utc=o['received_at_utc'],ref=o['ref']))
    fs.sort(key=lambda f:f['mono']); times=[f['mono'] for f in fs]
    def before(t):
        i=bisect.bisect_right(times,t)-1
        return fs[i] if i>=0 and 0<=t-fs[i]['mono']<=2.5 else None
    results=[]
    for q in requests:
        start,end=q['submit_mono_s'],q['end_mono_s']
        nxt=next((n for n in requests if n['phase']==q['phase'] and n['submit_mono_s']>start),None)
        stop=nxt['submit_mono_s'] if nxt else end+300
        ff=[f for f in fs if start<=f['mono']<stop and f.get('duty_valid') is True]
        if not ff: continue
        peak=max(ff,key=lambda f:f['duty']); pre=before(start)
        inside=[p for p in predictions if start<=p['origin']['t']<=end]
        row={'id':q['request_id'],'phase':q['phase'],'duration_s':end-start,
             'completion_tokens':(q.get('usage')or{}).get('completion_tokens'),
             'peak_pwm':peak['duty'],'first_observed_peak_after_client_end_s':peak['mono']-end,
             'peak_ref':peak['ref'],'pre':pre,'prediction_origins_during_request':len(inside),
             'ready_origins_during_request':sum(p['origin']['history_ready'] for p in inside)}
        if q['phase']=='sparse' and pre:
            near=[f for f in ff if f['mono']>=end and f['duty']>=peak['duty']-1]
            return_to=[f for f in ff if f['mono']>=peak['mono'] and f['duty']<=pre['duty']+1]
            row.update(last_near_peak_after_end_s=near[-1]['mono']-end if near else None,
                       first_return_pre_plus1_after_end_s=return_to[0]['mono']-end if return_to else None)
        results.append(row)
    transitions=[]; previous=None
    for f in fs:
        g=f.get('controller_gain')
        if g!=previous:
            transitions.append({'utc':f['utc'],'gain':g,'ratio':g/previous if previous else None,'slope':f.get('slope_c_per_min'),'cooling_response':f.get('cooling_response'),'ref':f['ref']})
            previous=g
    out={'scope':'recorded observation and normalized client-log audit; not thermal counterfactual or full software test',
         'run_hashes':hashes,'version':manifest['version'],'source_identity':manifest['source_identity'],
         'counts':{'observations':len(obs),'accepted':sum(e.get('accepted') is True for e in events),'origins':len(predictions),'history_ready':sum(p['origin']['history_ready'] for p in predictions)},
         'score_status':dict(collections.Counter(s['status'] for s in scores)),
         'requests':results,'gain_transitions':transitions,
         'limits':['normalized client logs were available; original SSE tail files were missing from the received truncated ZIP',
                   'timestamps are received API and client completion times, not exact hardware transition times',
                   'request windows are not independent experiments; no physical thermal constants identified']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out['counts'],ensure_ascii=False))
if __name__=='__main__':main()
