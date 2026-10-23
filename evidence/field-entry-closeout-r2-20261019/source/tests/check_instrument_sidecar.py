"""SYNTHETIC CSV attachment identity only. No physical comparison or old data pairing."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);root.mkdir();run=Path(sys.argv[2]);tools=Path(__file__).resolve().parents[1]/'tools'
original_index=(run/'files.json').read_bytes();summary=json.loads((run/'summary.json').read_text())
csv=root/'SYNTHETIC.csv';csv.write_text('Logging Summary\nSerial Number: SYNTHETIC\nFirmware Version: TEST\nSample Points: 3\nCH1,Temp,Celsius\nDate,Time,CH1\n2026/01/01,01:00:00,40.0\n2026/01/01,01:00:01,40.0\n2026/01/01,01:00:02,40.1\n')
probe=root/'probe.json';probe.write_text(json.dumps(dict(site_description='SYNTHETIC no physical probe',attachment_method='SYNTHETIC')))
photo=root/'SYNTHETIC-photo.txt';photo.write_text('SYNTHETIC ONLY; not real clock evidence')
clock=root/'clock.json';clock.write_text(json.dumps(dict(path=str(photo),sha256=hashlib.sha256(photo.read_bytes()).hexdigest(),timezone='UTC',display_resolution_s=1,uncertainty_s=None)))
r=subprocess.run([sys.executable,str(tools/'attach_instrument.py'),'--run-dir',str(run),'--file',str(csv),'--output',str(root/'sidecar'),'--probe-description',str(probe),'--end-clock-record',str(clock)],text=True,capture_output=True)
(root/'import.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
records=[json.loads(x) for x in (root/'sidecar/imported/normalized/records.jsonl').read_text().splitlines()]
assert len(records)==3 and all(x['run_id']==summary['native_run_id'] for x in records)
assert (run/'files.json').read_bytes()==original_index
link=json.loads((root/'sidecar/run-link.json').read_text());assert link['end_clock_photo_sha256']==hashlib.sha256(photo.read_bytes()).hexdigest()
(root/'verification.json').write_text(json.dumps(dict(SYNTHETIC=True,records=3,equal_adjacent_rows_preserved=True,native_UUID_linked=True,original_run_index_unchanged=True,end_clock_original_SHA_verified=True,clock_offset_applied=False),indent=2)+'\n')
print('Synthetic sidecar identity passed; original run unchanged; no model fitting')
