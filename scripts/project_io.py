"""OS-owned locks and crash-safe publication for local codex-ppt projects."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import errno
import hashlib
import json
import os
import shutil
import socket
import time

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def canonical(path):
    return os.path.normcase(str(Path(path).resolve()))

def sync_directory(path):
    if os.name=='nt': return
    descriptor=os.open(path,os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)

def atomic_write(path,content):
    path=Path(path)
    raw=content.encode('utf-8') if isinstance(content,str) else content
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file() and path.read_bytes()==raw: return
    temporary=None
    try:
        with NamedTemporaryFile(prefix='.codex-ppt-write-',suffix='.tmp',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
        sync_directory(path.parent)
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()

def atomic_json(path,value):
    atomic_write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def atomic_copy(source,target):
    source,target=Path(source),Path(target)
    if source.resolve()==target.resolve(): return
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with NamedTemporaryFile(prefix='.codex-ppt-copy-',suffix='.tmp',dir=target.parent,delete=False) as stream:
            temporary=Path(stream.name)
            with source.open('rb') as incoming: shutil.copyfileobj(incoming,stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,target)
        sync_directory(target.parent)
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()

class BusyProject(RuntimeError):
    pass

class ResourceLock:
    """A persistent lock file is diagnostic; the kernel owns the actual lock."""
    def __init__(self,path,kind='project',timeout=0):
        self.resource=Path(path).resolve()
        key=hashlib.sha256((kind+':'+canonical(path)).encode()).hexdigest()[:24]
        self.file=self.resource.parent/'.codex-ppt-locks'/(key+'.lock')
        self.kind,self.timeout,self.stream=kind,timeout,None

    def __enter__(self):
        self.file.parent.mkdir(parents=True,exist_ok=True)
        stream=self.file.open('a+b')
        if self.file.stat().st_size==0:
            stream.write(b'\0')
            stream.flush()
        deadline=time.monotonic()+self.timeout
        while True:
            try:
                stream.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in [errno.EACCES,errno.EAGAIN,errno.EDEADLK]:
                    stream.close()
                    raise
                if time.monotonic()>=deadline:
                    try:
                        stream.seek(1)
                        owner=json.loads(stream.read().decode('utf-8'))
                        note=f' (PID {owner.get("pid")}, {owner.get("host")})'
                    except (OSError,ValueError): note=''
                    stream.close()
                    raise BusyProject(f'{self.kind.capitalize()} busy: {self.resource}{note}; rerun after the other process exits') from None
                time.sleep(.05)
        self.stream=stream
        # a+b is append mode: truncate before writing ownership diagnostics.
        try:
            stream.seek(1)
            stream.truncate()
            stream.write(json.dumps({'pid':os.getpid(),'host':socket.gethostname(),'kind':self.kind,
                                     'resource':str(self.resource),'started':time.time()}).encode())
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self,*exc):
        if self.stream is not None:
            try:
                self.stream.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
            finally:
                self.stream.close()
                self.stream=None

@contextmanager
def project_staging(root):
    """Publish init/import as a whole directory; a killed process leaves no half-project."""
    root=Path(root).resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Project destination must be new or empty')
    root.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.codex-ppt-init-',dir=root.parent) as temporary:
        stage=Path(temporary).resolve()
        if stage.parent!=root.parent or stage==root or not stage.name.startswith('.codex-ppt-init-'):
            raise RuntimeError('Initialization staging path escaped its selected parent')
        yield stage
        if root.exists(): root.rmdir()  # Only an empty destination is accepted.
        os.replace(stage,root)
        sync_directory(root.parent)

def journal_path(root,out):
    key=hashlib.sha256(canonical(out).encode()).hexdigest()[:24]
    return Path(root)/'qa/publications'/(key+'.json')

def recover_publication(root,out,state_path,source_path):
    journal=journal_path(root,out)
    if not journal.exists(): return None
    record=json.loads(journal.read_text(encoding='utf-8'))
    marker=json.loads((Path(root)/'.codex-ppt-project.json').read_text(encoding='utf-8-sig'))
    if record.get('project_id')!=marker['project_id'] or canonical(record['target'])!=canonical(out):
        raise ValueError('Publication journal does not belong to this project/output')
    stage=Path(record['temporary']).resolve()
    if stage.parent!=Path(out).resolve().parent or not stage.name.startswith('.codex-ppt-') or stage.suffix!='.pptx':
        raise ValueError('Publication journal contains an invalid staging path')
    actual=digest(out) if Path(out).is_file() else None
    if actual==record['new_sha256']:
        try: existing=json.loads(Path(state_path).read_text(encoding='utf-8')) if Path(state_path).exists() else {}
        except (OSError,ValueError): existing={}
        if (existing.get('output_sha256')!=actual or existing.get('build_fingerprint')!=record['state'].get('build_fingerprint')
                or existing.get('output')!=record['state'].get('output')):
            atomic_json(state_path,record['state'])
        if stage.is_file() and digest(stage)==record['new_sha256']: stage.unlink()
        journal.unlink()
        return 'committed-state-recovered'
    if actual!=record['previous_sha256']:
        raise ValueError('Output changed after an interrupted publication; preserve/import the latest PPTX')
    if stage.is_file() and digest(stage)==record['new_sha256'] and digest(source_path)==record['source_sha256']:
        os.replace(stage,out)
        sync_directory(Path(out).parent)
        atomic_json(state_path,record['state'])
        journal.unlink()
        return 'staged-export-recovered'
    # Keep any stale staged file as evidence; never publish it over changed input.
    archive=journal.with_suffix('.aborted.json')
    os.replace(journal,archive)
    return 'stale-export-not-published'

def publish_pptx(root,stage,out,previous_hash,state_path,state,source_path,source_hash):
    if digest(source_path)!=source_hash:
        raise RuntimeError('deck.json changed during build; rerun using its latest saved version')
    if (digest(out) if Path(out).is_file() else None)!=previous_hash:
        raise RuntimeError('Target changed during export; the generated file was not published')
    with Path(stage).open('r+b') as stream: os.fsync(stream.fileno())
    marker=json.loads((Path(root)/'.codex-ppt-project.json').read_text(encoding='utf-8-sig'))
    record={'project_id':marker['project_id'],'target':str(Path(out).resolve()),
            'temporary':str(Path(stage).resolve()),'previous_sha256':previous_hash,
            'new_sha256':state['output_sha256'],'state':state,'source_sha256':source_hash}
    journal=journal_path(root,out)
    atomic_json(journal,record)
    os.replace(stage,out)
    sync_directory(Path(out).parent)
    atomic_json(state_path,state)
    journal.unlink()
