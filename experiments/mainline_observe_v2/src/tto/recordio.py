"""Plain historical logs and directly compressed observe logs."""
import gzip
import json
import re
import zlib
from pathlib import Path


def log_paths(root, stream):
    pattern=re.compile(re.escape(stream)+r'(?:-(\d+))?\.jsonl(?:\.gz)?')
    fragments=[(int(m.group(1) or 1),p) for p in Path(root).glob(stream+'*.jsonl*')
               if (m:=pattern.fullmatch(p.name))]
    return [p for _,p in sorted(fragments)]


def open_log(path):
    return gzip.open(path,'rt',encoding='utf-8') if Path(path).suffix=='.gz' else Path(path).open(encoding='utf-8')


def read_records(path, *, live=False):
    if not live or Path(path).suffix!='.gz':
        with open_log(path) as stream:
            for line in stream: yield json.loads(line)
        return
    # A running gzip stream has sync-flushed records but no final trailer yet.
    decoder=zlib.decompressobj(31);pending=b''
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):
            pending+=decoder.decompress(block)
            lines=pending.split(b'\n');pending=lines.pop()
            for line in lines: yield json.loads(line)
