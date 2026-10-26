"""Real-process lock release and deterministic interrupted-publication checks."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,os,subprocess,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from project_io import ResourceLock,atomic_json,digest,publish_pptx,recover_publication,journal_path,project_staging

class ProjectSafety(unittest.TestCase):
    def setUp(self):
        parent=os.environ.get('CODEX_PPT_TEST_DIR')
        if parent: Path(parent).mkdir(parents=True,exist_ok=True)
        self.temp=TemporaryDirectory(prefix='safety-',dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.project=self.folder/'project'
        self.project.mkdir()
        self.source=self.project/'deck.json'
        atomic_json(self.source,{'title':'original'})
        atomic_json(self.project/'.codex-ppt-project.json',{'tool':'codex-ppt','project_id':'test-owned-project'})
        self.out=self.project/'final/deck.pptx'
        self.out.parent.mkdir()
        self.out.write_bytes(b'previous checked PPTX')
        self.stage=self.out.parent/'.codex-ppt-test-staged.pptx'
        self.stage.write_bytes(b'new checked PPTX')
        self.state=self.project/'qa/pipeline-state.json'
        atomic_json(self.state,{'output':str(self.out),'output_sha256':digest(self.out),'stage':'checked'})

    def child(self,script,*args):
        # Avoid treating a Windows venv launcher PID as the actual lock owner.
        executable=getattr(sys,'_base_executable',sys.executable)
        return subprocess.Popen([executable,'-u','-c',
            'import sys; sys.path.insert(0,'+repr(str(ROOT/'scripts'))+'); '+script,*map(str,args)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)

    def test_project_lock_blocks_writer_then_releases_after_hard_kill(self):
        script="from project_io import ResourceLock; from pathlib import Path; import time; lock=ResourceLock(Path(sys.argv[1])); lock.__enter__(); print('LOCKED',flush=True); time.sleep(30)"
        process=self.child(script,self.project)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        self.assertEqual(process.stdout.readline().strip(),'LOCKED')
        with self.assertRaisesRegex(RuntimeError,'busy'):
            with ResourceLock(self.project): pass
        denied=subprocess.run([sys.executable,str(ROOT/'scripts/deck.py'),'plan',str(self.source)],
                              capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertNotEqual(denied.returncode,0)
        self.assertIn('Project busy',denied.stderr)
        self.assertFalse((self.project/'brief.md').exists())
        process.kill()
        process.communicate(timeout=10)
        with ResourceLock(self.project) as recovered:
            self.assertTrue(recovered.file.exists())  # Presence is not a stale lock.

    def test_output_lock_is_shared_by_different_projects(self):
        with ResourceLock(self.out,'output'):
            with self.assertRaisesRegex(RuntimeError,'busy'):
                with ResourceLock(self.out,'output'): pass

    def test_atomic_json_preserves_previous_file_if_replace_fails(self):
        previous=self.state.read_bytes()
        with patch('project_io.os.replace',side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError): atomic_json(self.state,{'new':'not committed'})
        self.assertEqual(self.state.read_bytes(),previous)
        self.assertEqual(list(self.state.parent.glob('.codex-ppt-write-*.tmp')),[])

    def interrupt_publish(self,after_replace):
        script='''
from pathlib import Path
import os,project_io
root,stage,out,state,source=map(Path,sys.argv[1:])
new={'output':str(out),'output_sha256':project_io.digest(stage),'build_fingerprint':'new-fingerprint','stage':'checked'}
if sys.argv[0] is None: pass
'''
        # Inject only at the durability boundary, not into normal production code.
        if after_replace:
            script+='''
original=project_io.atomic_json
def interrupted(path,value):
    if Path(path)==state: os._exit(73)
    return original(path,value)
project_io.atomic_json=interrupted
'''
        else:
            script+='''
original=project_io.os.replace
def interrupted(src,dest):
    if Path(dest)==out: os._exit(74)
    return original(src,dest)
project_io.os.replace=interrupted
'''
        script+='''
with project_io.ResourceLock(root),project_io.ResourceLock(out,'output'):
    project_io.publish_pptx(root,stage,out,project_io.digest(out),state,new,source,project_io.digest(source))
'''
        process=self.child(script,self.project,self.stage,self.out,self.state,self.source)
        stdout,stderr=process.communicate(timeout=10)
        self.assertEqual(process.returncode,73 if after_replace else 74,stderr)

    def test_recovers_checked_output_if_killed_before_state_commit(self):
        expected=self.stage.read_bytes()
        self.interrupt_publish(True)
        self.assertEqual(self.out.read_bytes(),expected)
        self.state.write_text('{old torn state',encoding='utf-8')
        with ResourceLock(self.project),ResourceLock(self.out,'output'):
            result=recover_publication(self.project,self.out,self.state,self.source)
        self.assertEqual(result,'committed-state-recovered')
        self.assertEqual(json.loads(self.state.read_text())['output_sha256'],digest(self.out))
        self.assertFalse(journal_path(self.project,self.out).exists())

    def test_recovers_staged_export_if_killed_before_rename(self):
        expected=self.stage.read_bytes()
        self.interrupt_publish(False)
        with ResourceLock(self.project),ResourceLock(self.out,'output'):
            result=recover_publication(self.project,self.out,self.state,self.source)
        self.assertEqual(result,'staged-export-recovered')
        self.assertEqual(self.out.read_bytes(),expected)

    def test_does_not_publish_old_stage_after_source_changes(self):
        previous=self.out.read_bytes()
        self.interrupt_publish(False)
        atomic_json(self.source,{'title':'new source edit'})
        result=recover_publication(self.project,self.out,self.state,self.source)
        self.assertEqual(result,'stale-export-not-published')
        self.assertEqual(self.out.read_bytes(),previous)

    def test_does_not_overwrite_manual_changes_after_interruption(self):
        self.interrupt_publish(False)
        self.out.write_bytes(b'manual edit after interruption')
        with self.assertRaisesRegex(ValueError,'Output changed'):
            recover_publication(self.project,self.out,self.state,self.source)
        self.assertEqual(self.out.read_bytes(),b'manual edit after interruption')

    def test_new_project_directory_is_not_published_half_complete(self):
        target=self.folder/'new-project'
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            with project_staging(target) as stage:
                atomic_json(stage/'deck.json',{'partial':'draft'})
                raise RuntimeError('interrupted')
        self.assertFalse(target.exists())
        with project_staging(target) as stage:
            atomic_json(stage/'deck.json',{'complete':True})
        self.assertEqual(json.loads((target/'deck.json').read_text()),{'complete':True})

if __name__=='__main__': unittest.main(verbosity=2)
