"""Review-only local launcher: avoid inherited parent RSS high-water in Linux synthetic source.
No submitted module/budget is changed. This is not an SSH or target-machine test.
"""
import sys,asyncio,shlex,json
from pathlib import Path
R=Path('/mnt/data/tto_cpu2_independent_review_20261020')
sys.path.insert(0,str(R/'work/field/source/tests'))
import generate_joint_sample as g
orig=g.run
async def run(*args,**kwargs):
    binding=args[1]
    cmd=binding['sidecar']['argv']
    binding['sidecar']['argv']=['/bin/sh','-c',shlex.join(cmd)+'; code=$?; exit "$code"']
    binding['review_harness_note']='LOCAL shell fork avoids inherited max-RSS from NumPy parent. Same sender/receiver, original budgets. Not SSH/target.'
    return await orig(*args,**kwargs)
g.run=run
asyncio.run(g.main(R/'work/joint-isolated-source'))
