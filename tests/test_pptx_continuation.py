"""Native PPTX readback/continuation invariants; no AI calls or user-file edits."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
import json,os,shutil,struct,subprocess,sys,unittest,zlib
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pptx_edit import inspect_pptx
from pptx_package import A,P,R,NS,ordered_slide_parts,read_package,validate_relationships

NODE=os.environ.get('CODEX_PPT_NODE') or shutil.which('node')
CLI=ROOT/'scripts/deck.py'

def png():
    def c(k,d): return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d))
    return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('!IIBBBBB',2,2,8,2,0,0,0))+c(b'IDAT',zlib.compress((b'\0'+b'\xff'*6)*2))+c(b'IEND',b'')

def cli(*args):
    return subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,
                          encoding='utf-8',errors='replace',timeout=45)

def rewrite(source,target,mutate):
    with ZipFile(source) as original,ZipFile(target,'w',ZIP_DEFLATED) as out:
        for item in original.infolist():
            out.writestr(item,mutate(item.filename,original.read(item.filename)))

@unittest.skipUnless(NODE,'Node required')
class NativeContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent=os.environ.get('CODEX_PPT_TEST_DIR')
        if parent: Path(parent).mkdir(parents=True,exist_ok=True)
        cls.shared=TemporaryDirectory(prefix='native-fixture-',dir=parent)
        folder=Path(cls.shared.name)
        project=folder/'fixture'
        result=cli('init',project)
        if result.returncode: raise RuntimeError(result.stderr)
        asset=project/'assets/tiny.png'
        asset.parent.mkdir()
        asset.write_bytes(png())
        source={'schema_version':1,'title':'续作测试','assets':{'picture':{'file':'assets/tiny.png'}},'slides':[
            {'id':1,'layout':'hero','title':'钢琴入门','artwork':'picture','bullets':['每天练习20分钟']},
            {'id':2,'layout':'bullets','title':'第二页','bullets':['先慢慢弹，再连起来']} ]}
        (project/'deck.json').write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')
        result=cli('build',project/'deck.json','--node',NODE,'--no-preview')
        if result.returncode: raise RuntimeError(result.stderr)
        cls.fixture=Path(json.loads(result.stdout)['pptx'])

    @classmethod
    def tearDownClass(cls): cls.shared.cleanup()

    def setUp(self):
        self.temp=TemporaryDirectory(prefix='native-case-',dir=os.environ.get('CODEX_PPT_TEST_DIR'))
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    def import_file(self,file=None):
        project=self.folder/'continue'
        result=cli('import-pptx',file or self.fixture,project)
        self.assertEqual(result.returncode,0,result.stderr)
        return project,json.loads((project/'deck.json').read_text(encoding='utf-8'))

    def build(self,project,source):
        (project/'deck.json').write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')
        result=cli('build',project/'deck.json','--node',NODE,'--no-preview')
        self.assertEqual(result.returncode,0,result.stderr)
        return Path(json.loads(result.stdout)['pptx'])

    def manual_file(self,*,mixed=False,fill=False,reorder=False,wide=False):
        file=self.folder/'user-edited.pptx'
        def modify(name,data):
            if name=='ppt/slides/slide1.xml':
                root=ET.fromstring(data)
                shape=next(s for s in root.findall('.//p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('name')=='bullet-1')
                shape.find('p:txBody/a:p/a:r/a:t',NS).text='每天练习15分钟'
                shape.find('p:spPr/a:xfrm/a:off',NS).set('x','666750')
                shape.find('p:spPr/a:xfrm/a:off',NS).set('y','3238500')
                rpr=shape.find('p:txBody/a:p/a:r/a:rPr',NS)
                rpr.set('sz','2100')
                rpr.find('a:solidFill/a:srgbClr',NS).set('val','CC3366')
                if mixed:
                    run=deepcopy(shape.find('p:txBody/a:p/a:r',NS))
                    run.find('a:rPr',NS).set('b','1')
                    run.find('a:t',NS).text='，保留强调'
                    shape.find('p:txBody/a:p',NS).insert(2,run)
                if fill:
                    prop=shape.find('p:spPr',NS)
                    for child in list(prop):
                        if child.tag=='{'+A+'}noFill': prop.remove(child)
                    element=ET.SubElement(prop,'{'+A+'}solidFill')
                    ET.SubElement(element,'{'+A+'}srgbClr',{'val':'EAF4FF'})
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            if name=='ppt/presentation.xml' and (reorder or wide):
                root=ET.fromstring(data)
                if reorder:
                    seq=root.find('p:sldIdLst',NS)
                    seq[:]=list(reversed(list(seq)))
                if wide:
                    root.find('p:sldSz',NS).set('cx','12192000')
                    root.find('p:sldSz',NS).set('cy','6858000')
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            return data
        rewrite(self.fixture,file,modify)
        return file

    def append(self,source):
        source['slides']=[{'id':3,'layout':'closing','title':'新增练习页',
                           'items':[{'heading':'复盘','body':'每次找到一个改进点。'}],'takeaway':'下次继续。'}]

    def test_reads_manual_text_geometry_size_and_color(self):
        manual=self.manual_file()
        info=inspect_pptx(manual)
        target=next(t for t in info['slides'][0]['texts'] if t['name']=='bullet-1')
        self.assertEqual(target['text'],'每天练习15分钟')
        self.assertEqual(target['x'],70)
        self.assertEqual(target['y'],340)
        self.assertEqual(target['size'],21)
        self.assertEqual(target['color'],'#CC3366')

    def test_append_keeps_all_original_slide_and_media_bytes(self):
        manual=self.manual_file(fill=True)
        before=manual.read_bytes()
        project,source=self.import_file(manual)
        self.append(source)
        out=self.build(project,source)
        self.assertEqual(manual.read_bytes(),before)
        with ZipFile(manual) as old,ZipFile(out) as new:
            for name in old.namelist():
                if name.startswith(('ppt/slides/','ppt/media/','ppt/slideMasters/','ppt/theme/','ppt/notesSlides/','ppt/notesMasters/')) and not name.endswith('/'):
                    self.assertEqual(new.read(name),old.read(name),name)
            parts=ordered_slide_parts(new)
            self.assertEqual(len(parts),3)
            self.assertIn('新增练习页',new.read(parts[-1]).decode())
            self.assertIn('03 / 03',new.read(parts[-1]).decode())
            root=ET.fromstring(new.read('ppt/presentation.xml'))
            resource_ids=[e.get('id') for e in root.findall('p:sldMasterIdLst/p:sldMasterId',NS)]
            for file in new.namelist():
                if file.startswith('ppt/slideMasters/slideMaster') and file.endswith('.xml'):
                    master=ET.fromstring(new.read(file))
                    resource_ids += [e.get('id') for e in master.findall('p:sldLayoutIdLst/p:sldLayoutId',NS)]
            self.assertEqual(len(resource_ids),len(set(resource_ids)))
            self.assertEqual(len(root.findall('p:notesMasterIdLst/p:notesMasterId',NS)),1)
        data,_,_=read_package(out)
        validate_relationships(data)

    def test_native_edits_roundtrip_then_import_again(self):
        project,source=self.import_file(self.manual_file())
        target=next(t for t in source['base']['slides'][0]['texts'] if t['name']=='bullet-1')
        target.update(text='每天练习12分钟',x=84,y=350,size=22,color='#1655AA',bold=True,align='center')
        out=self.build(project,source)
        info=inspect_pptx(out)
        current=next(t for t in info['slides'][0]['texts'] if t['name']=='bullet-1')
        for key in ['text','x','y','size','color','bold','align']: self.assertEqual(current[key],target[key],key)
        again=self.folder/'second-import'
        result=cli('import-pptx',out,again)
        self.assertEqual(result.returncode,0,result.stderr)
        source2=json.loads((again/'deck.json').read_text(encoding='utf-8'))
        self.append(source2)
        final=self.build(again,source2)
        self.assertEqual(inspect_pptx(final)['slides'][0]['texts'],info['slides'][0]['texts'])

    def test_actual_page_order_is_used_after_manual_reordering(self):
        manual=self.manual_file(reorder=True)
        project,source=self.import_file(manual)
        self.assertTrue(source['base']['slides'][0]['part'].endswith('slide2.xml'))
        self.append(source)
        final=self.build(project,source)
        self.assertTrue(inspect_pptx(final)['slides'][0]['part'].endswith('slide2.xml'))

    def test_widescreen_physical_size_is_respected(self):
        manual=self.manual_file(wide=True)
        project,source=self.import_file(manual)
        self.append(source)
        final=self.build(project,source)
        info=inspect_pptx(final)
        self.assertEqual(info['width_emu'],12192000)
        self.assertEqual(len(info['slides']),3)

    def test_mixed_run_text_is_preserved_and_unsupported_replacement_rejected(self):
        manual=self.manual_file(mixed=True)
        project,source=self.import_file(manual)
        target=next(t for t in source['base']['slides'][0]['texts'] if t['name']=='bullet-1')
        self.assertFalse(target['text_editable'])
        self.append(source)
        final=self.build(project,source)
        original=final.read_bytes()
        target['text']='不应悄悄丢掉强调格式'
        (project/'deck.json').write_text(json.dumps(source,ensure_ascii=False),encoding='utf-8')
        result=cli('build',project/'deck.json','--node',NODE,'--no-preview')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('specialized',result.stderr)
        self.assertEqual(final.read_bytes(),original)

    def test_noop_keeps_every_original_package_member(self):
        manual=self.manual_file()
        project,source=self.import_file(manual)
        out=self.build(project,source)
        with ZipFile(manual) as old,ZipFile(out) as new:
            self.assertEqual(set(old.namelist())-{n for n in old.namelist() if n.endswith('/')},set(new.namelist()))
            for name in new.namelist(): self.assertEqual(new.read(name),old.read(name),name)

    def test_unused_compatibility_namespace_stays_bound_after_text_patch(self):
        manual=self.manual_file()
        namespaced=self.folder/'namespaced.pptx'
        def namespaces(name,data):
            if name=='ppt/slides/slide1.xml':
                # The prefix is referenced only by mc:Ignorable, not XML tags.
                end=data.index(b'>',data.index(b'<ns0:sld') if b'<ns0:sld' in data else data.index(b'<p:sld'))
                extra=b' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" mc:Ignorable="p14"'
                data=data[:end]+extra+data[end:]
            return data
        rewrite(manual,namespaced,namespaces)
        project,source=self.import_file(namespaced)
        target=next(t for t in source['base']['slides'][0]['texts'] if t['name']=='bullet-1')
        target['text']='修改后仍保留兼容命名空间'
        output=self.build(project,source)
        with ZipFile(output) as z:
            xml=z.read('ppt/slides/slide1.xml')
            self.assertIn(b'xmlns:p14=',xml)
            self.assertIn(b'mc:Ignorable="p14"',xml)

    def test_changed_import_snapshot_is_rejected(self):
        project,source=self.import_file()
        original=project/'source/original.pptx'
        original.write_bytes(original.read_bytes()+b' changed snapshot')
        result=cli('build',project/'deck.json','--no-preview')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('source PPTX changed',result.stderr)

if __name__=='__main__': unittest.main(verbosity=2)
