import sys,json,hashlib,math
from pathlib import Path
from itertools import zip_longest
root=Path(__file__).resolve().parents[1]
a=root/'original/evidence/modeling/results';b=root/'frozen-rerun'
def compare(x,y,p='',acc=None):
 if acc is None:acc={'floats':0,'max_abs':0.,'path':''}
 if isinstance(x,dict):
  assert isinstance(y,dict) and set(x)==set(y),(p,'keys')
  for k in x:compare(x[k],y[k],p+'/'+k,acc)
 elif isinstance(x,list):
  assert isinstance(y,list) and len(x)==len(y),(p,'length')
  for i,(u,v) in enumerate(zip(x,y)):compare(u,v,p+'/'+str(i),acc)
 elif isinstance(x,float):
  assert isinstance(y,(float,int)) and math.isfinite(y),p
  d=abs(x-y);acc['floats']+=1
  if d>acc['max_abs']:acc['max_abs']=d;acc['path']=p
  assert d<=1e-8,(p,x,y,d)
 else:assert x==y,(p,x,y)
 return acc
res=[]
for p in sorted(b.glob('*')):
 q=a/p.name
 if not q.exists() or p.name in ['environment-resource.json','state-replay-verification.json']:continue
 if p.suffix=='.json':rec=compare(json.loads(q.read_text()),json.loads(p.read_text()))
 elif p.suffix=='.jsonl':
  rec={'floats':0,'max_abs':0.,'path':''}
  count=0
  with q.open() as qf, p.open() as pf:
   for i,(l,r) in enumerate(zip_longest(qf,pf)):
    assert l is not None and r is not None,p.name
    compare(json.loads(l),json.loads(r),str(i),rec);count+=1
  rec['rows']=count
 else:continue
 res.append({'name':p.name,**rec})
supp=[]
for p in sorted((root/'supplement-rerun').iterdir()):
 q=root/'original/analysis'/p.name
 supp.append({'name':p.name,'byte_equal':p.read_bytes()==q.read_bytes()})
rec={'files_compared':len(res),'max_abs_difference':max(r['max_abs'] for r in res),'results':res,'supplement':supp,'runtime':sys.version,
 'rerun_state_replay':json.loads((b/'state-replay-verification.json').read_text()),'environment':json.loads((b/'environment-resource.json').read_text())}
(root/'results/replay-comparison.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in rec.items() if k not in ['results','rerun_state_replay']},ensure_ascii=False,indent=2))
