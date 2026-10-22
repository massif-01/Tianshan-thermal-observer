"""One bounded session journal; rotation changes files, never engine/model state."""
import json, os, shutil, threading, time
from pathlib import Path
from tto.storage import Journal, LimitReached
from tto.util import canonical, file_hash, write_json

class SessionStore:
    def __init__(self, root, *, budget=8*1024**3, segment_bytes=2*1024**3,
                 chunk_bytes=64*1024**2, segment_seconds=14400, min_free=1024**3,
                 clock=time.monotonic):
        self.root=Path(root); self.root.mkdir(mode=0o700)
        self.budget=budget; self.segment_bytes=segment_bytes; self.chunk_bytes=chunk_bytes
        self.segment_seconds=segment_seconds; self.min_free=min_free; self.clock=clock
        self.reserve=min(8*1024**2,budget//10); self.total=0; self.segment=1
        self.segment_start=clock(); self.segment_used=0; self.handles={}; self.counts={}
        self.files={}; self.streams={}; self.segments=[]; self.segment_files=set()
        self.lock=threading.RLock(); self.closed=False; self.finalizing=False; self.rotation_count=0
    def metadata(self, path, value, *, final=False):
        with self.lock:
            path=Path(path); b=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            old=path.stat().st_size if path.exists() else 0
            if self.total+len(b)-old>self.budget: raise LimitReached('session_metadata_budget')
            if shutil.disk_usage(self.root).free<len(b)+(0 if final or self.finalizing else self.min_free): raise LimitReached('min_free_bytes')
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.name not in ('status.json','input-profile.json'):
                raise FileExistsError('immutable metadata already exists: '+str(path))
            if path.name in ('status.json','input-profile.json'):
                temporary=path.with_name(path.name+'.next')
                fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
                os.replace(temporary,path)
            else:write_json(path,value)
            self.total+=len(b)-old
    def adopt(self, path):
        with self.lock:self.total+=Path(path).stat().st_size
    def _seal_segment(self):
        for handle,_ in self.handles.values(): handle.flush(); os.fsync(handle.fileno()); handle.close()
        self.handles.clear()
        paths=sorted(self.segment_files)
        record=dict(segment=self.segment,started_mono_s=self.segment_start,ended_mono_s=self.clock(),
                    byte_count=self.segment_used,files={p:dict(bytes=(self.root/p).stat().st_size,sha256=file_hash(self.root/p)) for p in paths},
                    continuity='same process/session/native UUID/thermal state; file rotation only')
        self.metadata(self.root/'segments'/f'{self.segment:04d}'/'index.json',record)
        self.segments.append(record);self.segment_files.clear()
    def append(self, base, stream, row):
        b=canonical(row)+b'\n'
        with self.lock:
            if self.closed: raise OSError('session store is closed')
            if len(b)>self.chunk_bytes: raise LimitReached('record_exceeds_chunk')
            if self.total+len(b)>self.budget-self.reserve: raise LimitReached('session_max_bytes')
            if shutil.disk_usage(self.root).free<self.min_free+len(b): raise LimitReached('min_free_bytes')
            if self.segment_used and (self.segment_used+len(b)>self.segment_bytes or self.clock()-self.segment_start>=self.segment_seconds):
                self._seal_segment(); self.segment+=1; self.rotation_count+=1
                self.segment_start=self.clock();self.segment_used=0
            key=(str(Path(base).relative_to(self.root)),stream)
            if key in self.handles and self.handles[key][1]+len(b)>self.chunk_bytes:
                self.handles[key][0].flush();os.fsync(self.handles[key][0].fileno());self.handles[key][0].close();del self.handles[key]
            if key not in self.handles:
                self.counts[key]=self.counts.get(key,0)+1;n=self.counts[key]
                name=f'{stream}-{n:04d}.jsonl' if stream=='observations' or n>1 else stream+'.jsonl'
                path=Path(base)/name;path.parent.mkdir(parents=True,exist_ok=True)
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                self.handles[key]=(os.fdopen(fd,'wb'),0)
                rel=str(path.relative_to(self.root));self.files[key]=rel
                self.streams.setdefault('/'.join(key),[]).append(rel)
            handle,size=self.handles[key];handle.write(b);handle.flush()
            self.handles[key]=(handle,size+len(b));self.segment_files.add(self.files[key])
            self.total+=len(b);self.segment_used+=len(b)
    def flush_prefix(self, base):
        with self.lock:
            prefix=str(Path(base).relative_to(self.root))
            for key,(handle,_) in self.handles.items():
                if key[0]==prefix: handle.flush();os.fsync(handle.fileno())
    def close(self):
        with self.lock:
            if self.closed:return
            self.finalizing=True;self._seal_segment();self.closed=True
            self.metadata(self.root/'stream-index.json',dict(contract='TTO-OBSERVE-SEGMENTS-v1',streams=self.streams,
                segments=len(self.segments),rotations=self.rotation_count,session_max_bytes=self.budget,
                segment_max_bytes=self.segment_bytes,file_chunk_max_bytes=self.chunk_bytes,
                segment_max_seconds=self.segment_seconds,heat_state_reset_by_rotation=False))
            self.metadata(self.root/'files.json',{str(p.relative_to(self.root)):dict(bytes=p.stat().st_size,sha256=file_hash(p))
                for p in sorted(self.root.rglob('*')) if p.is_file() and p!=self.root/'files.json'})

class ObserveJournal(Journal):
    """Native processor still writes raw before invoking its one consumer callback."""
    def __init__(self,*args,store,**kwargs):
        self.store=store;super().__init__(*args,**kwargs);store.adopt(self.path/'manifest.json')
    def append(self,name,row):
        self.store.append(self.path,name,row)
        if name=='observations':self.observation_count+=1
    def metadata(self,name,row):
        if name!='input-profile.json':raise ValueError('unsupported native metadata')
        self.store.metadata(self.path/name,row)
    def close(self,summary):
        from tto.util import utc_now
        self.store.flush_prefix(self.path)
        self.store.metadata(self.path/'summary.json',dict(summary,ended_at_utc=utc_now(),observations=self.observation_count,
            observation_session_version='TTO-OBSERVE-v1',native_legacy_max_s=14400,
            session_max_s=86400,session_max_bytes=self.store.budget),final=True)
        self.store.metadata(self.path/'files.json',{p.name:file_hash(p) for p in self.path.iterdir() if p.is_file() and p.name!='files.json'},final=True)
