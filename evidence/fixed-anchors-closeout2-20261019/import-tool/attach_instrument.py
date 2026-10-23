"""Attach original YET CSV using the existing reviewed importer, in a NEW sidecar only."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--file',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--probe-description',type=Path,required=True);p.add_argument('--end-clock-record',type=Path,required=True);a=p.parse_args()
summary=json.loads((a.run_dir/'summary.json').read_text());run=summary['native_run_id']
if not run or summary['mode']!='execute':raise SystemExit('This attachment is for a completed mixed-run identity, not diagnostic or another historical run')
clock=json.loads(a.end_clock_record.read_text());photo=Path(clock['path'])
if hashlib.sha256(photo.read_bytes()).hexdigest()!=clock['sha256'] or not clock.get('timezone') or not clock.get('display_resolution_s') or 'uncertainty_s' not in clock:raise SystemExit('End clock original/metadata must match; unknown error must be explicit')
if a.output.exists():raise SystemExit('Fresh sidecar directory required; original indexed run will not be changed')
a.output.mkdir();root=Path(__file__).resolve().parent/'yet_import'
subprocess.run([sys.executable,str(root/'mapping/import_yet610l.py'),'--file',str(a.file),'--output',str(a.output/'imported'),
                '--trial-id',run,'--probe-description',str(a.probe_description),'--tool',str(root/'import-tool/ref.py')],check=True)
(a.output/'end-clock-photo.original').write_bytes(photo.read_bytes())
(a.output/'end-clock-record.original.json').write_bytes(a.end_clock_record.read_bytes())
link=dict(native_run_id=run,command_id=summary['command_id'],original_csv_sha256=hashlib.sha256(a.file.read_bytes()).hexdigest(),
          native_files_index_sha256=hashlib.sha256((a.run_dir/'files.json').read_bytes()).hexdigest(),
          end_clock_photo_sha256=clock['sha256'],end_clock_record_sha256=hashlib.sha256(a.end_clock_record.read_bytes()).hexdigest(),
          imported_run_id=run,legacy_importer_session_alias='yet610l-ch1-trial',clock_offset_applied=False,
          note='Explicit same-run link; imported local instrument time is unchanged, no curve alignment or state correction')
(a.output/'run-link.json').write_text(json.dumps(link,ensure_ascii=False,indent=2)+'\n')
(a.output/'files.json').write_text(json.dumps({str(f.relative_to(a.output)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(a.output.rglob('*')) if f.is_file() and f!=a.output/'files.json'},ensure_ascii=False,indent=2)+'\n')
