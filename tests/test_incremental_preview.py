"""Real LibreOffice selective export and unchanged-page preview reuse."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util,json,os,shutil,subprocess,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('CODEX_PPT_NODE') or shutil.which('node')
READY=bool(NODE and importlib.util.find_spec('pypdf') and shutil.which('pdftoppm') and
           (shutil.which('soffice') or Path('F:/codex/tools/LibreOffice/program/soffice.exe').exists()))

@unittest.skipUnless(READY,'Node, pypdf, LibreOffice and Poppler required')
class IncrementalPreview(unittest.TestCase):
    def test_only_changed_or_corrupt_page_is_rendered(self):
        from pypdf import PdfReader
        parent=os.environ.get('CODEX_PPT_TEST_DIR')
        if parent: Path(parent).mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix='incremental-preview-',dir=parent) as temporary:
            project=Path(temporary)/'deck'
            def cli(*args):
                return subprocess.run([sys.executable,str(ROOT/'scripts/deck.py'),*map(str,args)],
                                      capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
            result=cli('init',project)
            self.assertEqual(result.returncode,0,result.stderr)
            source={'schema_version':1,'title':'单页预览验证','assets':{},'slides':[
                {'id':n,'layout':'bullets','title':f'第{n}页','bullets':[f'内容{n}'],'page_number':False} for n in range(1,4)]}
            def build():
                (project/'deck.json').write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')
                result=cli('build',project/'deck.json','--node',NODE,'--scale','800','--timeout','40')
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            first=build()
            self.assertEqual(first['preview']['rendered_pages'],[1,2,3])
            paths=first['preview']['pages']
            unchanged={i:Path(paths[i]).stat().st_mtime_ns for i in [0,2]}
            source['slides'][1]['bullets']=['只有第二页更新']
            second=build()
            self.assertEqual(second['exported_pages'],[2])
            self.assertEqual(second['preview']['rendered_pages'],[2])
            self.assertEqual(second['preview']['preview_cache_hits'],[1,3])
            for i,stamp in unchanged.items():
                self.assertEqual(second['preview']['pages'][i],paths[i])
                self.assertEqual(Path(paths[i]).stat().st_mtime_ns,stamp)
            pdf=PdfReader(second['preview']['pdf'])
            self.assertEqual(len(pdf.pages),3)
            self.assertIn('只有第二页更新',''.join(pdf.pages[1].extract_text().split()))
            self.assertNotIn('只有第二页更新',''.join(pdf.pages[0].extract_text().split()))
            third=build()
            self.assertTrue(third['build_cached'])
            self.assertTrue(third['preview']['cached'])
            self.assertEqual(third['preview']['rendered_pages'],[])
            Path(third['preview']['pages'][2]).write_bytes(b'corrupt cached image')
            repaired=build()
            self.assertTrue(repaired['build_cached'])
            self.assertEqual(repaired['exported_pages'],[])
            self.assertEqual(repaired['preview']['rendered_pages'],[3])
            self.assertTrue(Path(repaired['preview']['pages'][2]).read_bytes().startswith(b'\xff\xd8'))

if __name__=='__main__': unittest.main(verbosity=2)
