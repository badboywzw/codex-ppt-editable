"""Observable project-pipeline regressions; no AI calls or network access."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import os
import shutil
import struct
import subprocess
import sys
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from deck_layouts import compile_deck

CLI=ROOT/'scripts/deck.py'
NODE=os.environ.get('CODEX_PPT_NODE') or shutil.which('node')

def png():
    def chunk(kind,data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff'*6)*2))+chunk(b'IEND',b'')

class DeckProject(unittest.TestCase):
    def setUp(self):
        parent=os.environ.get('CODEX_PPT_TEST_DIR')
        if parent: Path(parent).mkdir(parents=True,exist_ok=True)
        self.tmp=TemporaryDirectory(prefix='project-',dir=parent)
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.project=self.folder/'deck'
        self.source=self.project/'deck.json'

    def cli(self,*args):
        return subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,
                              encoding='utf-8',errors='replace',timeout=35)

    def init(self):
        result=self.cli('init',self.project)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(self.source.read_text(encoding='utf-8'))

    def save(self,source):
        self.source.write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')

    def export(self,*args):
        result=self.cli('build',self.source,'--node',NODE,*args)
        return result,json.loads(result.stdout) if result.returncode==0 else None

    def test_init_refuses_to_overwrite_existing_files(self):
        self.project.mkdir()
        existing=self.project/'keep.txt'
        existing.write_text('manual content',encoding='utf-8')
        result=self.cli('init',self.project)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(existing.read_text(encoding='utf-8'),'manual content')
        self.assertFalse(self.source.exists())

    def test_every_layout_compiles_to_native_text_and_textless_svg(self):
        source=self.init()
        source['slides'] += [
            {'id':7,'layout':'timeline','title':'复习节奏','events':[{'value':'今天','title':'学习'},{'value':'明天','title':'复习'}]},
            {'id':8,'layout':'custom','title':'精确标注','page_number':False,
             'texts':[{'name':'diagram-label','text':'这段文字可编辑','x':48,'y':48,'w':600,'h':80,'size':28}]}]
        result=compile_deck(source,self.project)
        self.assertEqual(len(result['pages']),8)
        for page in result['pages']:
            self.assertTrue(page['texts'])
            self.assertNotIn('<text',page['svg'])
            self.assertTrue(all('fill' not in t for t in page['texts']))
        self.assertEqual(result['pages'][-1]['texts'][0]['name'],'diagram-label')

    def test_pending_artwork_is_reported_without_generation(self):
        source=self.init()
        source['assets']={'hero':{'file':'assets/hero.png','prompt':'A white and blue sculptural object on the right half'}}
        source['slides'][0]['artwork']='hero'
        self.save(source)
        result=self.cli('plan',self.source)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['pending_assets'][0]['asset'],'hero')
        self.assertIn('No words',(self.project/'prompts/hero.txt').read_text(encoding='utf-8'))
        self.assertFalse((self.project/'assets/hero.png').exists())
        self.assertFalse((self.project/'final').exists())

    def test_invalid_layout_and_frames_fail_early(self):
        source=self.init()
        source['slides'][0]['layout']='nonexistent'
        with self.assertRaisesRegex(ValueError,'unknown layout'): compile_deck(source,self.project)
        source['slides'][0]={'id':1,'layout':'custom','title':'坏坐标','texts':[
            {'name':'outside','text':'不应导出','x':950,'y':30,'w':200,'h':40,'size':20}]}
        with self.assertRaisesRegex(ValueError,'outside canvas'): compile_deck(source,self.project)

    @unittest.skipUnless(NODE,'Node required')
    def test_build_roundtrip_cache_and_wording_change_reuse_artwork(self):
        source=self.init()
        artwork=self.project/'assets/hero.png'
        artwork.parent.mkdir()
        artwork.write_bytes(png())
        source['assets']={'hero':{'file':'assets/hero.png'},'unused':{'file':'assets/not-needed.png'}}
        source['slides'][0]['artwork']='hero'
        self.save(source)
        result,first=self.export('--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(first['build_cached'])
        output=Path(first['pptx'])
        original=output.read_bytes()
        review=self.project/'qa/qa.md'
        review.write_text('Manual review notes must be preserved.',encoding='utf-8')
        copied=self.project/'editable/visual-layers/slide-01/asset-hero.png'
        art_stamp=copied.stat().st_mtime_ns
        self.assertEqual(copied.read_bytes(),png())
        result,second=self.export('--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(second['build_cached'])
        self.assertEqual(output.read_bytes(),original)
        self.assertEqual(review.read_text(encoding='utf-8'),'Manual review notes must be preserved.')
        source['slides'][0]['title']='新的演示标题'
        self.save(source)
        result,third=self.export('--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(third['build_cached'])
        self.assertEqual(copied.stat().st_mtime_ns,art_stamp)
        with ZipFile(output) as pptx:
            xml=pptx.read('ppt/slides/slide1.xml').decode()
            self.assertIn('新的演示标题',xml)
        self.assertTrue(json.loads((self.project/'qa/editability.json').read_text(encoding='utf-8'))['passed'])

    @unittest.skipUnless(NODE,'Node required')
    def test_preserves_manual_edits_and_allows_a_new_output(self):
        self.init()
        result,built=self.export('--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        output=Path(built['pptx'])
        modified=output.read_bytes()+b' manual-edit-marker'
        output.write_bytes(modified)
        result,_=self.export('--no-preview')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('changed manually',result.stderr)
        self.assertEqual(output.read_bytes(),modified)
        result,version=self.export('--no-preview','--out',self.project/'final/version2.pptx')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(Path(version['pptx']).exists())
        self.assertEqual(output.read_bytes(),modified)

    @unittest.skipUnless(NODE,'Node required')
    def test_resume_after_preview_failure_keeps_successful_export(self):
        self.init()
        result,_=self.export('--soffice',self.folder/'missing-soffice.exe')
        self.assertNotEqual(result.returncode,0)
        state=json.loads((self.project/'qa/pipeline-state.json').read_text(encoding='utf-8'))
        self.assertEqual(state['stage'],'preview-failed')
        output=Path(state['output'])
        original=output.read_bytes()
        result,resumed=self.export('--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(resumed['build_cached'])
        self.assertEqual(output.read_bytes(),original)

if __name__=='__main__':
    unittest.main(verbosity=2)
