"""Extract an evidence ZIP to a fresh local folder and compare all scientific outputs."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from prepare import ROOT,digest,read,write


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--input-dir',type=Path,required=True)
    args=ap.parse_args()
    directory=Path(tempfile.mkdtemp(prefix='tto-slowstate-independent-',dir='/private/tmp'))
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        for n in z.namelist():assert not n.startswith('/') and '..' not in Path(n).parts
        z.extractall(directory)
    started=time.perf_counter()
    cmd=[sys.executable,str(directory/'rerun.py'),'--input-dir',str(args.input_dir.absolute())]
    with (directory/'independent-entry.log').open('w') as f:
        completed=subprocess.run(cmd,cwd=directory,stdout=f,stderr=subprocess.STDOUT)
    assert completed.returncode==0,(directory/'independent-entry.log').read_text()
    compared=[]
    for path in sorted((ROOT/'results').iterdir()):
        if path.name=='resources.json' or not path.is_file():continue
        baseline=digest(path.read_bytes());replayed=digest((directory/'results'/path.name).read_bytes())
        assert baseline==replayed,(path.name,baseline,replayed)
        compared.append(dict(file='results/'+path.name,sha256=baseline,identical=True))
    proof=dict(status='pass',tested_archive_sha256=digest(args.archive.read_bytes()),
        extracted_to=str(directory),archive_CRC='pass',entry_returncode=completed.returncode,
        wall_seconds=time.perf_counter()-started,scientific_output_files=compared,
        entry_receipt=read(directory/'replay-logs/receipt.json'),
        extracted_readback=read(directory/'readback-checks.json'),
        note='Resources, timestamps and report absolute local image links are environment-dependent; scientific files match byte for byte.',
        original_dynamic_refits=0,device_or_network_actions=False)
    write(ROOT/'independent-replay-proof.json',proof)
    print(json.dumps(dict(status='pass',directory=str(directory),identical_scientific_files=len(compared),
                         wall_seconds=proof['wall_seconds']),ensure_ascii=False))


if __name__=='__main__':main()
