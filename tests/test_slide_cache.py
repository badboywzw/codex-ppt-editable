"""Per-page export invalidation and native-page visual dependency keys."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile,ZIP_DEFLATED
from unittest.mock import patch
import xml.etree.ElementTree as ET
import json,os,shutil,struct,subprocess,sys,unittest,zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from slide_cache import visual_page_keys,export_pages
from pptx_package import REL,xml_bytes

NODE=os.environ.get('CODEX_PPT_NODE') or shutil.which('node')
CLI=ROOT/'scripts/deck.py'

def png(rgb):
    def c(k,d): return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d))
    return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('!IIBBBBB',2,2,8,2,0,0,0))+c(b'IDAT',zlib.compress((b'\0'+bytes(rgb)*2)*2))+c(b'IEND',b'')

@unittest.skipUnless(NODE,'Node required')
class SlideCache(unittest.TestCase):
    def setUp(self):
        parent=os.environ.get('CODEX_PPT_TEST_DIR')
        if parent: Path(parent).mkdir(parents=True,exist_ok=True)
        self.temp=TemporaryDirectory(prefix='slide-cache-',dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.root=self.folder/'deck'
        result=self.cli('init',self.root)
        self.assertEqual(result.returncode,0,result.stderr)
        self.source={'schema_version':1,'title':'单页缓存测试','assets':{},'slides':[
            {'id':i,'layout':'bullets','title':f'第{i}页','bullets':[f'页面{i}的文字'],'page_number':False} for i in range(1,4)]}

    def cli(self,*args):
        return subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=45)

    def build(self,root=None,source=None):
        root=root or self.root
        (root/'deck.json').write_text(json.dumps(source or self.source,ensure_ascii=False),encoding='utf-8')
        result=self.cli('build',root/'deck.json','--node',NODE,'--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_wording_change_exports_only_changed_slide(self):
        first=self.build()
        self.assertEqual(first['exported_pages'],[1,2,3])
        output=Path(first['pptx'])
        with ZipFile(output) as z: before={p:z.read(f'ppt/slides/slide{p}.xml') for p in [1,3]}
        stamps={str(p):p.stat().st_mtime_ns for p in (self.root/'editable/page-cache').glob('*/slide.pptx')}
        keys=visual_page_keys(output)
        self.source['slides'][1]['bullets']=['只修改第二页']
        changed=self.build()
        self.assertEqual(changed['exported_pages'],[2])
        self.assertEqual(changed['export_cache_hits'],[1,3])
        for p,stamp in stamps.items(): self.assertEqual(Path(p).stat().st_mtime_ns,stamp)
        with ZipFile(output) as z:
            for p in before: self.assertEqual(z.read(f'ppt/slides/slide{p}.xml'),before[p])
        after=visual_page_keys(output)
        self.assertEqual([i+1 for i,(a,b) in enumerate(zip(keys,after)) if a!=b],[2])

    def test_shared_image_invalidates_only_dependent_pages(self):
        asset=self.root/'assets/shared.png'
        asset.parent.mkdir()
        asset.write_bytes(png([255,255,255]))
        self.source['assets']={'shared':{'file':'assets/shared.png'}}
        for i in [0,2]: self.source['slides'][i]['visuals']=[{'asset':'shared','position':[760,200,50,50]}]
        first=self.build()
        keys=visual_page_keys(first['pptx'])
        asset.write_bytes(png([80,150,255]))
        changed=self.build()
        self.assertEqual(changed['exported_pages'],[1,3])
        self.assertEqual(changed['export_cache_hits'],[2])
        after=visual_page_keys(changed['pptx'])
        self.assertEqual([i+1 for i,(a,b) in enumerate(zip(keys,after)) if a!=b],[1,3])

    def test_allocated_media_paths_do_not_invalidate_unrelated_page(self):
        assets=self.root/'assets'
        assets.mkdir()
        (assets/'one.png').write_bytes(png([255,255,255]))
        (assets/'two.png').write_bytes(png([255,0,0]))
        self.source['assets']={'one':{'file':'assets/one.png'},'two':{'file':'assets/two.png'}}
        self.source['slides'][2]['visuals']=[{'asset':'one','position':[760,200,50,50]}]
        first=self.build()
        original=visual_page_keys(first['pptx'])
        self.source['slides'][1]['visuals']=[{'asset':'two','position':[760,200,50,50]}]
        changed=self.build()
        after=visual_page_keys(changed['pptx'])
        self.assertEqual(after[2],original[2])
        self.assertEqual(changed['exported_pages'],[2])

    def test_imported_native_edit_changes_only_that_page_key(self):
        first=self.build()
        keys=visual_page_keys(first['pptx'])
        imported=self.folder/'imported'
        result=self.cli('import-pptx',first['pptx'],imported)
        self.assertEqual(result.returncode,0,result.stderr)
        source=json.loads((imported/'deck.json').read_text(encoding='utf-8'))
        target=next(t for t in source['base']['slides'][1]['texts'] if t['name']=='title')
        target['text']='修改原生第二页'
        changed=self.build(imported,source)
        after=visual_page_keys(changed['pptx'])
        self.assertEqual(changed['exported_pages'],[])
        self.assertEqual([i+1 for i,(a,b) in enumerate(zip(keys,after)) if a!=b],[2])

    def test_failed_later_page_reuses_already_checked_page_on_retry(self):
        from deck import project
        (self.root/'deck.json').write_text(json.dumps(self.source,ensure_ascii=False),encoding='utf-8')
        planned=self.cli('plan',self.root/'deck.json')
        self.assertEqual(planned.returncode,0,planned.stderr)
        _,_,compiled=project(self.root/'deck.json')
        original_run=subprocess.run
        calls=[]
        def fail_second(*args,**kwargs):
            calls.append(1)
            if len(calls)==2: return subprocess.CompletedProcess(args[0],1,'','simulated worker failure')
            return original_run(*args,**kwargs)
        with patch('slide_cache.subprocess.run',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'worker failure'):
                export_pages(self.root,compiled,NODE,10,30)
        checked=list((self.root/'editable/page-cache').glob('*/export.json'))
        self.assertEqual(len(checked),1)
        first_page=checked[0].parent/'slide.pptx'
        stamp=first_page.stat().st_mtime_ns
        resumed=self.build()
        self.assertEqual(resumed['exported_pages'],[2,3])
        self.assertEqual(resumed['export_cache_hits'],[1])
        self.assertEqual(first_page.stat().st_mtime_ns,stamp)

    def test_cyclic_resource_dependencies_are_complete_for_each_page(self):
        first=self.build()
        def modified(path,value):
            with ZipFile(first['pptx']) as source,ZipFile(path,'w',ZIP_DEFLATED) as output:
                for item in source.infolist():
                    raw=source.read(item.filename)
                    if item.filename in ['ppt/slides/_rels/slide1.xml.rels','ppt/slides/_rels/slide2.xml.rels']:
                        root=ET.fromstring(raw)
                        target='a.xml' if 'slide1.' in item.filename else 'b.xml'
                        ET.SubElement(root,'{'+REL+'}Relationship',{'Id':'rIdCacheProbe','Type':'urn:cache:resource','Target':'../../custom/'+target})
                        raw=xml_bytes(root,raw)
                    output.writestr(item,raw)
                for part in ['a','b']:
                    output.writestr(f'custom/{part}.xml','<probe/>')
                output.writestr('custom/d.xml',f'<probe value="{value}"/>')
                rels=lambda entries: ('<Relationships xmlns="'+REL+'">'+''.join(
                    f'<Relationship Id="rId{i}" Type="urn:cache:resource" Target="{target}"/>' for i,target in enumerate(entries,1))+'</Relationships>')
                output.writestr('custom/_rels/a.xml.rels',rels(['b.xml','d.xml']))
                output.writestr('custom/_rels/b.xml.rels',rels(['a.xml']))
        before=self.folder/'before.pptx'
        after=self.folder/'after.pptx'
        modified(before,'old')
        modified(after,'new')
        a,b=visual_page_keys(before),visual_page_keys(after)
        self.assertEqual([i+1 for i,(old,new) in enumerate(zip(a,b)) if old!=new],[1,2])

if __name__=='__main__': unittest.main(verbosity=2)
