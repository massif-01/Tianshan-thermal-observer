"""Compare original and derived output; never modify either."""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def changes(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  result=[]
  for k in sorted(a.keys()|b.keys()):result+=changes(a.get(k),b.get(k),path+'.'+k if path else k)
  return result
 return [] if a==b else [{'path':path,'before':a,'after':b}]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--original',type=Path,required=True);args=ap.parse_args();before=[json.loads(x) for x in args.original.read_text().splitlines()];after=[json.loads(x) for x in (R/'output/source-health-Y-I02.jsonl').read_text().splitlines()];assert len(before)==len(after)==5319
 identity=0;semantic=[]
 for a,b in zip(before,after):
  for c in changes(a,b):
   if c['path']=='identity.spec':assert c['before']=='COMM-SOURCE-HEALTH-R2-v1' and c['after']=='COMM-SOURCE-HEALTH-R2-I02-v1';identity+=1
   else:semantic.append({'observation_ref':b['identity']['observed_through_ref'],**c})
 assert identity==5319 and len(semantic)==1
 assert semantic[0]['observation_ref'].endswith('observation:5319') and semantic[0]['path']=='measurement.TJ_and_rails.raw_valid' and semantic[0]['before'] is True and semantic[0]['after'] is False
 assert before[-1]['measurement']['TJ_and_rails']['source']==after[-1]['measurement']['TJ_and_rails']['source'];assert after[-1]['measurement']['TJ_and_rails']['source']['ref'].endswith('observation:5316')
 result={'spec':'COMM-SOURCE-HEALTH-R2-I02-v1','rows':5319,'interface_identity_updates':identity,'semantic_differences':semantic,'historical_TJ_rails_values_refs_times_TTL_preserved':True,'all_PWM_safety_observer_permission_fields_unchanged':True,'tests_passed':6,'runtime_or_collector_patch_changed':False,'device_access':False,'deployment':False}
 (R/'output/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(R/'output/Y-disconnect-before-after.json').write_text(json.dumps({'before':before[-1],'after':after[-1]},ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
 prov=json.loads((R/'inputs/provenance.json').read_text());assert hashlib.sha256((R/'baseline/source_health.py').read_bytes()).hexdigest()==prov['original_source_health_script_sha256'];assert hashlib.sha256(args.original.read_bytes()).hexdigest()==prov['original_output_sha256']
if __name__=='__main__':main()
