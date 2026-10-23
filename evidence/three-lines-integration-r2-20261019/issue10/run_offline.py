"""Reproduce preparation with virtual time + only loopback HTTP. Never a live launcher."""
import argparse,datetime,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output.resolve()
 out.mkdir(parents=True,exist_ok=False);start=time.monotonic();calls=[]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
 def run(name,command):
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  calls.append({'name':name,'exit_code':r.returncode,'command':command})
  if r.returncode:raise RuntimeError(name+' failed; inspect local log')
 for profile in ['fixed-anchors','same-plan-other-model','irregular-confirm-after-freeze']:
  run('plan-'+profile,[sys.executable,str(ROOT/'mix.py'),'plan','--profile',profile,'--output',str(out/(profile+'-plan.json'))])
  run('virtual-'+profile,[sys.executable,str(ROOT/'mix.py'),'dry-run','--profile',profile,'--output',str(out/('virtual-'+profile)),'--run-id',profile,'--command-id',profile])
 for scenario in ['startup','short_gap','long_gap','http_timeout','mode_change','binding_change','unknown_safety','unavailable_observer']:
  run('scenario-'+scenario,[sys.executable,str(ROOT/'mix.py'),'dry-run','--scenario',scenario,'--output',str(out/('scenario-'+scenario)),'--run-id',scenario,'--command-id',scenario])
 for behavior in ['normal','incomplete']:
  run('HTTP-'+behavior,[sys.executable,str(ROOT/'mix.py'),'loopback','--behavior',behavior,'--output',str(out/('HTTP-'+behavior))])
 run('tests',[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'])
 result={'status':'offline_preparation_completed_not_field_test','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'python':sys.version,'python_executable':sys.executable,'host':platform.platform(),'elapsed_wall_s':time.monotonic()-start,
         'calls':calls,'network_scope':'fake HTTP/SSE loopback only; no device/API calls','field_authorized':False}
 (out/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 hashes={str(f.relative_to(out)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.rglob('*')) if f.is_file()}
 (out/'SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n');print(json.dumps({'status':result['status'],'calls':len(calls),'elapsed_s':result['elapsed_wall_s']}))
if __name__=='__main__':main()
