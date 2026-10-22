"""Local identity and bounded private evidence. No network clients are created here."""
import datetime,hashlib,json,os,platform,socket,time,uuid,threading
from pathlib import Path

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

class Clock:
    def __init__(self):
        self.origin=time.monotonic();self.domain=f'{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}'
    def now(self):return time.monotonic()-self.origin
    def utc(self):return utc()
    def bracket(self):
        before=time.monotonic();u=utc();after=time.monotonic()
        return dict(domain=self.domain,mono_before_s=before,utc=u,mono_after_s=after,utc_clock_accuracy_s=None,
                    host=socket.gethostname(),platform=platform.platform(),pid=os.getpid())

class Evidence:
    def __init__(self,root,limit=256*1024**2):
        self.root=Path(root);self.handles={};self.bytes=0;self.limit=limit;self.lock=threading.Lock()
    def append(self,name,obj):
        with self.lock:
            raw=(json.dumps(obj,ensure_ascii=False,allow_nan=False)+'\n').encode()
            if self.bytes+len(raw)>self.limit:raise ValueError('field_evidence_budget')
            if name not in self.handles:
                fd=os.open(self.root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);self.handles[name]=os.fdopen(fd,'wb')
            f=self.handles[name];f.write(raw);f.flush();self.bytes+=len(raw)
    def close(self):
        for f in self.handles.values():f.flush();os.fsync(f.fileno());f.close()
        self.handles.clear()
