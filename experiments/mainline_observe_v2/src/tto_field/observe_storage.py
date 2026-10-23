"""One bounded session journal; rotation changes files, never engine/model state."""
import json, os, shutil, threading, time, zlib
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from tto.storage import Journal, LimitReached
from tto.util import canonical, file_hash, write_json

# After Z_SYNC_FLUSH: empty final deflate block (2) plus gzip CRC/size (8).
GZIP_FINISH_BYTES=10

def replace_json(path, raw):
    temporary=path.with_name(path.name+'.next')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

class SessionStore:
    def __init__(self, root, *, budget=8*1024**3, segment_bytes=2*1024**3,
                 chunk_bytes=64*1024**2, segment_seconds=14400, min_free=1024**3,
                 clock=time.monotonic):
        self.root=Path(root); self.root.mkdir(mode=0o700)
        self.budget=budget; self.segment_bytes=segment_bytes; self.chunk_bytes=chunk_bytes
        self.segment_seconds=segment_seconds; self.min_free=min_free; self.clock=clock
        self.reserve=8*1024**2 if budget is None else min(8*1024**2,budget//10); self.total=0; self.segment=1
        self.segment_start=clock(); self.segment_used=0; self.handles={}; self.counts={}
        self.files={}; self.streams={}; self.segments=[]; self.segment_files=set()
        self.lock=threading.RLock(); self.closed=False; self.finalizing=False; self.rotation_count=0
    def metadata(self, path, value, *, final=False):
        with self.lock:
            path=Path(path); b=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            old=path.stat().st_size if path.exists() else 0
            if self.budget is not None and self.total+len(b)-old>self.budget: raise LimitReached('session_metadata_budget')
            if shutil.disk_usage(self.root).free<len(b)+(0 if final or self.finalizing else self.min_free): raise LimitReached('min_free_bytes')
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.name not in ('status.json','input-profile.json'):
                raise FileExistsError('immutable metadata already exists: '+str(path))
            if path.name in ('status.json','input-profile.json'):
                replace_json(path,b)
            else:write_json(path,value)
            self.total+=len(b)-old
    def adopt(self, path):
        with self.lock:self.total+=Path(path).stat().st_size
    def _finish_file(self, key):
        handle, compressor, _ = self.handles.pop(key)
        tail = compressor.flush(zlib.Z_FINISH)
        handle.write(tail); handle.flush(); os.fsync(handle.fileno()); handle.close()
        self.total += len(tail); self.segment_used += len(tail)
    def _seal_segment(self):
        for key in list(self.handles): self._finish_file(key)
        paths=sorted(self.segment_files)
        record=dict(segment=self.segment,started_mono_s=self.segment_start,ended_mono_s=self.clock(),
                    byte_count=self.segment_used,files={p:dict(bytes=(self.root/p).stat().st_size,sha256=file_hash(self.root/p)) for p in paths},
                    continuity='same process/session/native UUID/thermal state; file rotation only')
        self.metadata(self.root/'segments'/f'{self.segment:04d}'/'index.json',record)
        self.segments.append(record);self.segment_files.clear()
    def append(self, base, stream, row):
        raw=canonical(row)+b'\n'
        with self.lock:
            if self.closed: raise OSError('session store is closed')
            if len(raw)>self.chunk_bytes: raise LimitReached('record_exceeds_chunk')
            key=(str(Path(base).relative_to(self.root)),stream)
            def encode():
                # Stage compression so a rejected write cannot advance the file's dictionary/CRC.
                compressor=self.handles[key][1].copy() if key in self.handles else zlib.compressobj(1,wbits=31)
                return compressor, compressor.compress(raw)+compressor.flush(zlib.Z_SYNC_FLUSH)
            compressor, b=encode()
            if key in self.handles and self.handles[key][2]+len(b)+GZIP_FINISH_BYTES>self.chunk_bytes:
                self._finish_file(key);compressor,b=encode()
            # Segment limits include every open file's eventual footer. A new
            # chunk uses a fresh dictionary, so decide this after chunk rotation.
            footers=GZIP_FINISH_BYTES*(len(self.handles)+(key not in self.handles))
            if self.segment_used and (self.segment_used+len(b)+footers>self.segment_bytes or self.clock()-self.segment_start>=self.segment_seconds):
                self._seal_segment(); self.segment+=1; self.rotation_count+=1
                self.segment_start=self.clock();self.segment_used=0
                compressor,b=encode()
            if len(b)+GZIP_FINISH_BYTES>self.chunk_bytes: raise LimitReached('record_exceeds_chunk')
            if self.budget is not None and self.total+len(b)>self.budget-self.reserve: raise LimitReached('session_max_bytes')
            if shutil.disk_usage(self.root).free<self.min_free+len(b): raise LimitReached('min_free_bytes')
            if key not in self.handles:
                self.counts[key]=self.counts.get(key,0)+1;n=self.counts[key]
                name=(f'{stream}-{n:04d}' if stream=='observations' or n>1 else stream)+'.jsonl.gz'
                path=Path(base)/name;path.parent.mkdir(parents=True,exist_ok=True)
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                self.handles[key]=(os.fdopen(fd,'wb'),compressor,0)
                rel=str(path.relative_to(self.root));self.files[key]=rel
                self.streams.setdefault('/'.join(key),[]).append(rel)
            handle,_,size=self.handles[key];handle.write(b);handle.flush()
            self.handles[key]=(handle,compressor,size+len(b));self.segment_files.add(self.files[key])
            self.total+=len(b);self.segment_used+=len(b)
    def close_prefix(self, base):
        with self.lock:
            prefix=str(Path(base).relative_to(self.root))
            for key in list(self.handles):
                if key[0]==prefix: self._finish_file(key)
    def close(self):
        with self.lock:
            if self.closed:return
            self.finalizing=True;self._seal_segment();self.closed=True
            self.metadata(self.root/'stream-index.json',dict(contract='TTO-OBSERVE-SEGMENTS-v2',encoding='gzip-jsonl-level1-sync-flush',streams=self.streams,
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
        self.store.close_prefix(self.path)
        self.store.metadata(self.path/'summary.json',dict(summary,ended_at_utc=utc_now(),observations=self.observation_count,
            observation_session_version='TTO-OBSERVE-v1',native_legacy_max_s=14400,
            session_max_s=None if isinstance(self.store,DailyStore) else 86400,session_max_bytes=self.store.budget),final=True)
        self.store.metadata(self.path/'files.json',{p.name:file_hash(p) for p in self.path.iterdir() if p.is_file() and p.name!='files.json'},final=True)


class DailyStore(SessionStore):
    """One process identity, independently sealed UTC-day journals."""
    def __init__(self,root,*,today=lambda:datetime.now(timezone.utc).date(),**options):
        options=dict(options,budget=None)
        super().__init__(root,**options)
        self.today=today;self.days={};self.recorded_days={};self.options=options;self.current_day=today().isoformat()
    def recording_day(self):
        # A wall-clock correction never reopens an immutable, already sealed day.
        with self.lock:
            self.current_day=max(self.current_day,self.today().isoformat())
            return self.current_day
    def _day(self,day):
        if day not in self.days:
            path=self.root/'days'/day
            path.parent.mkdir(exist_ok=True)
            self.days[day]=SessionStore(path,**self.options)
            self.recorded_days[day]=None
        return self.days[day]
    def append(self,base,stream,row):
        with self.lock:
            if self.closed:raise OSError('session store is closed')
            day=row['origin_day'] if Path(base)==self.root and stream in ('scores','predictions','daily-summary') else self.recording_day()
            store=self._day(day)
            if stream=='daily-summary':store.metadata(store.root/'scoring.json',row)
            else:store.append(store.root/Path(base).relative_to(self.root),stream,row)
    def seal_days(self,ready_days):
        with self.lock:
            sealed=[self.days.pop(day) for day in list(self.days) if day in ready_days]
        # Detached journals are immutable. Hash/fsync them off the model and writer threads.
        for store in sealed:self._seal_day(store)
    def _seal_day(self,store):
        store.close()
        path=store.root/'files.json'
        receipt=dict(bytes=path.stat().st_size,sha256=file_hash(path))
        with self.lock:self.recorded_days[store.root.name]=receipt
    def close_prefix(self,base):
        with self.lock:
            relative=Path(base).relative_to(self.root)
            for store in self.days.values():store.close_prefix(store.root/relative)
    def close(self):
        with self.lock:
            if self.closed:return
            self.finalizing=True
            for store in self.days.values():self._seal_day(store)
            self.days.clear();self.closed=True
            self.metadata(self.root/'stream-index.json',dict(contract='TTO-OBSERVE-DAYS-v2',layout='utc-days',
                retention_days=30,heat_state_reset_by_rotation=False))
            # Daily indexes already seal their data; never re-hash 30 days on exit.
            paths=[p for p in self.root.rglob('*') if p.is_file() and 'days' not in p.relative_to(self.root).parts and p!=self.root/'files.json']
            inventory={str(p.relative_to(self.root)):dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in sorted(paths)}
            for day,receipt in sorted(self.recorded_days.items()):
                path=self.root/'days'/day/'files.json'
                if receipt is None:raise OSError('daily index not sealed:'+day)
                if path.stat().st_size!=receipt['bytes'] or file_hash(path)!=receipt['sha256']:
                    raise ValueError('daily index SHA mismatch:'+day)
                inventory[str(path.relative_to(self.root))]=receipt
            self.metadata(self.root/'files.json',inventory)


def history_files(root,stream):
    """Yield (path, live) for retained daily records or a historical session."""
    from tto.recordio import log_paths
    root=Path(root);root_index_path=root/'stream-index.json'
    root_index=json.loads(root_index_path.read_text()) if root_index_path.exists() else None
    daily=(root/'days').is_dir() or root_index is not None and root_index.get('layout')=='utc-days'
    indexed_daily=root_index is not None and root_index.get('contract')=='TTO-OBSERVE-DAYS-v2'
    if indexed_daily:
        directories=[root/Path(name).parent for name in sorted(json.loads((root/'files.json').read_text())) if name.startswith('days/')]
    else:directories=sorted((root/'days').glob('*')) if daily else [root]
    for directory in directories:
        index_path=directory/'stream-index.json'
        index=root_index if directory==root else json.loads(index_path.read_text()) if indexed_daily or index_path.exists() else None
        if index is not None:
            for name in index['streams'].get('./'+stream,[]):yield directory/name,False
        else:
            for path in log_paths(directory,stream):yield path,True

def expire_history(root, device_id, host, today, *, active_store=None):
    """Commit the retained-day inventory, then remove expired files in this scope."""
    root=Path(root);cutoff=today-timedelta(days=29);expired=[];daily_sessions=[]
    for marker in root.parent.glob('*/history-retention.json'):
        item=json.loads(marker.read_text())
        if item['device_id']!=device_id or item['host']!=host:continue
        session=marker.parent
        if item.get('layout')=='utc-days':
            inventory_path=session/'files.json'
            inventory=json.loads(inventory_path.read_text()) if inventory_path.exists() else None
            active=active_store is not None and session==root
            if active:
                with active_store.lock:sealed_days={day for day,receipt in active_store.recorded_days.items() if receipt is not None}
            else:sealed_days={Path(name).parts[1] for name in inventory or {} if name.startswith('days/')}
            directories=set((session/'days').glob('*')) | {session/'days'/day for day in sealed_days}
            expired_days={p.name for p in directories if date.fromisoformat(p.name)<cutoff and
                (session!=root or p.name in sealed_days or not active and (p/'files.json').exists())}
            # The inventory is authoritative even if a day has already disappeared.
            # Commit legitimate expiry before deletion; interrupted deletes leave
            # only expired extras, which queries and archives must not include.
            if active:
                with active_store.lock:
                    active_store.recorded_days={day:receipt for day,receipt in active_store.recorded_days.items() if day not in expired_days}
            elif inventory is not None:
                retained={name:value for name,value in inventory.items() if not
                    (name.startswith('days/') and Path(name).parts[1] in expired_days)}
                if retained!=inventory:
                    replace_json(inventory_path,(json.dumps(retained,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
                inventory=retained
            expired.extend((p.name,p) for p in directories if p.name in expired_days)
            if session!=root and date.fromisoformat(item['day'])<cutoff:daily_sessions.append((session,inventory))
        elif session!=root and date.fromisoformat(item['day'])<cutoff:
            expired.append((item['day'],session))
    for day,path in sorted(expired):
        # Inventory entries can name already-missing days outside the retained window.
        if path.exists():shutil.rmtree(path)
    for session,inventory in daily_sessions:
        empty=(not any(name.startswith('days/') for name in inventory)
            if inventory is not None else not (session/'summary.json').exists())
        if not any((session/'days').glob('*')) and empty:shutil.rmtree(session)
    return sorted({day for day,_ in expired})
