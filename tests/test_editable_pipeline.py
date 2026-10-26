"""Regression checks for editable export; no AI calls or extra Python packages."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import json
import os
import shutil
import struct
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'scripts/build_editable_ppt_from_layers.mjs'
NODE = os.environ.get('CODEX_PPT_NODE') or shutil.which('node')
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

def png():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff' * 6) * 2)) + chunk(b'IEND', b''))

@unittest.skipUnless(NODE, 'Node.js is required')
class EditablePipeline(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get('CODEX_PPT_TEST_DIR')
        if parent:
            Path(parent).mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(prefix='editable-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.layers = self.folder / 'layers'
        page = self.layers / 'slide-01'
        page.mkdir(parents=True)
        (page / 'background.png').write_bytes(png())
        self.manifest = page / 'manifest.json'
        self.manifest.write_text(json.dumps({'assets':[{'file':'background.png'}]}), encoding='utf-8')
        self.spec = {'background':'#FFFFFF','slides':[{'slide':1,'texts':[
            {'name':'lesson-title','text':'可编辑标题','x':56,'y':48,'w':700,'h':70,'size':32},
            {'name':'practice-time','text':'20分钟练习','x':56,'y':160,'w':700,'h':70,'size':24}]}]}
        self.source = self.folder / 'text.json'
        self.output = self.folder / 'editable.pptx'

    def source_file(self):
        self.source.write_text(json.dumps(self.spec, ensure_ascii=False), encoding='utf-8')

    def build(self, *extra):
        self.source_file()
        return subprocess.run([NODE, str(BUILDER), '--backend','pptxgenjs', '--layers-root',str(self.layers),
                               '--text-json',str(self.source),'--out',str(self.output),*extra],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)

    def verify(self, input_file=None):
        return subprocess.run([sys.executable,str(ROOT/'scripts/check_editable_pptx.py'),
                               '--input',str(input_file or self.output),'--text-json',str(self.source)],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)

    def test_check_only_does_not_export(self):
        result = self.build('--check-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(json.loads(result.stdout)['textCount'], 2)

    def test_export_preserves_names_text_and_platform_font(self):
        result = self.build('--fail-on-text-fill')
        self.assertEqual(result.returncode, 0, result.stderr)
        with ZipFile(self.output) as package:
            slide = ET.fromstring(package.read('ppt/slides/slide1.xml'))
            names = [s.find('p:nvSpPr/p:cNvPr',NS).get('name') for s in slide.findall('.//p:sp',NS)]
            self.assertEqual(names, ['lesson-title','practice-time'])
            theme = package.read('ppt/theme/theme1.xml').decode()
            expected = 'Microsoft YaHei' if os.name == 'nt' else 'PingFang SC' if sys.platform == 'darwin' else 'Arial'
            self.assertIn(expected, theme)
        self.assertEqual(self.verify().returncode, 0)

    def test_rejects_missing_asset(self):
        self.manifest.write_text(json.dumps({'assets':[{'file':'missing.png'}]}),encoding='utf-8')
        result = self.build('--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing.png', result.stderr)
        self.assertFalse(self.output.exists())

    def test_rejects_duplicate_slide_ids(self):
        self.spec['slides'].append(self.spec['slides'][0])
        result = self.build('--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate slide ID', result.stderr)

    def test_rejects_outside_frame_and_bad_size(self):
        self.spec['slides'][0]['texts'][0].update(x=950,w=100,size='not-a-number')
        result = self.build('--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('beyond the canvas', result.stderr)
        self.assertIn('font size', result.stderr)

    def test_postflight_detects_changed_words_and_opaque_fills(self):
        self.assertEqual(self.build().returncode, 0)
        opaque = self.folder / 'opaque.pptx'
        with ZipFile(self.output) as original, ZipFile(opaque,'w',ZIP_DEFLATED) as patched:
            for item in original.infolist():
                data = original.read(item.filename)
                if item.filename == 'ppt/slides/slide1.xml':
                    root = ET.fromstring(data)
                    shape = root.find('.//p:sp',NS)
                    prop = shape.find('p:spPr',NS)
                    fill = ET.SubElement(prop,'{'+NS['a']+'}solidFill')
                    ET.SubElement(fill,'{'+NS['a']+'}srgbClr',{'val':'FFFFFF'})
                    data = ET.tostring(root,encoding='utf-8',xml_declaration=True)
                patched.writestr(item,data)
        result = self.verify(opaque)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('opaque',result.stdout)
        self.spec['slides'][0]['texts'][0]['text']='错误的标题'
        self.source_file()
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing or changed',result.stdout)

    @unittest.skipUnless((shutil.which('soffice') or Path('F:/codex/tools/LibreOffice/program/soffice.exe').exists())
                         and shutil.which('pdftoppm'), 'LibreOffice and Poppler required')
    def test_preview_is_cached_and_source_sensitive(self):
        self.assertEqual(self.build().returncode, 0)
        long_folder=self.folder/('中文路径测试'*8)
        long_folder.mkdir()
        staged_source=long_folder/'文字可编辑试做.pptx'
        shutil.copy2(self.output,staged_source)
        command=[sys.executable,str(ROOT/'scripts/render_editable_preview.py'),'--input',str(staged_source),
                 '--output-dir',str(self.folder/'preview'),'--scale','800']
        # The helper budgets 45s for each of two subprocesses, plus cleanup.
        first=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=105)
        self.assertEqual(first.returncode,0,first.stderr)
        initial=json.loads(first.stdout)
        self.assertFalse(initial['cached'])
        self.assertEqual(len(initial['pages']),1)
        second=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
        self.assertEqual(second.returncode,0,second.stderr)
        self.assertTrue(json.loads(second.stdout)['cached'])
        self.assertEqual(initial['pages'],json.loads(second.stdout)['pages'])
        self.spec['slides'][0]['texts'][1]['text']='30分钟练习'
        self.assertEqual(self.build().returncode, 0)
        shutil.copy2(self.output,staged_source)
        third=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=105)
        self.assertEqual(third.returncode,0,third.stderr)
        changed=json.loads(third.stdout)
        self.assertFalse(changed['cached'])
        self.assertNotEqual(initial['pages'],changed['pages'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
