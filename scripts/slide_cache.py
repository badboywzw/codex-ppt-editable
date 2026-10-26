"""Per-slide export cache and order-aware OPC visual fingerprints."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import subprocess
import time
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from project_io import ResourceLock,atomic_copy,atomic_json,digest
from check_editable_pptx import check as check_pptx
from pptx_package import P,A,R,NS,ordered_slide_parts,read_package,rels_part,target_part,append_package,write_package

SCRIPTS=Path(__file__).resolve().parent

def key(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def export_pages(root,compiled,node,width,timeout):
    """A worker only touches a private staging file; receipt publication is atomic."""
    cache=Path(root)/'editable/page-cache'
    cache.mkdir(parents=True,exist_ok=True)
    work=cache/'.work'
    work.mkdir(exist_ok=True)
    engine={name:digest(SCRIPTS/name) for name in ['build_editable_ppt_from_layers.mjs']}
    package=SCRIPTS.parent/'node_modules/pptxgenjs/package.json'
    engine['pptxgenjs']=digest(package)
    paths,misses,hits=[],[],[]
    base_count=compiled.get('native_base',{}).get('slide_count',0)
    for position,page in enumerate(compiled['pages'],base_count+1):
        folder=Path(root)/f'editable/visual-layers/slide-{page["id"]:02}'
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        assets=[{'position':a.get('position'),'canvas':a.get('canvas'),'name':a.get('name'),
                 'sha256':digest(folder/a['file'])} for a in manifest['assets']]
        text={'background':compiled['text_source']['background'],'typeface':compiled['text_source']['typeface'],
              'slides':[{'slide':page['id'],'texts':page['texts']}]}
        fingerprint=key({'protocol':1,'text':text,'assets':assets,'physical_width':width,'engine':engine,
                         'node':{'path':str(Path(node).resolve()),'mtime_ns':Path(node).stat().st_mtime_ns}})
        entry=cache/fingerprint[:24]
        output=entry/'slide.pptx'
        receipt=entry/'export.json'
        valid=False
        try:
            old=json.loads(receipt.read_text(encoding='utf-8'))
            valid=old['fingerprint']==fingerprint and output.is_file() and digest(output)==old['sha256']
        except (OSError,ValueError,KeyError): pass
        if valid:
            hits.append(position)
        else:
            with TemporaryDirectory(prefix='page-',dir=work) as temporary:
                stage=Path(temporary).resolve()
                if stage.parent!=work.resolve(): raise RuntimeError('Slide staging escaped its cache workspace')
                source=stage/'text.json'
                atomic_json(source,text)
                command=[node,str(SCRIPTS/'build_editable_ppt_from_layers.mjs'),'--backend','pptxgenjs',
                         '--layers-root',str(Path(root)/'editable/visual-layers'),'--text-json',str(source),
                         '--out',str(stage/'slide.pptx'),'--workspace',str(stage/'workspace'),
                         '--pptx-width',str(width),'--slide-size','960x540','--fail-on-text-fill']
                result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',
                                      timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                if result.returncode: raise RuntimeError((result.stderr+'\n'+result.stdout).strip()[-2500:])
                checked=check_pptx(stage/'slide.pptx',source)
                if not checked['passed']: raise RuntimeError(f'Slide {position} failed native-text validation')
                atomic_copy(stage/'slide.pptx',output)
                atomic_json(receipt,{'fingerprint':fingerprint,'sha256':digest(output),'text_objects':checked['native_text_objects']})
            misses.append(position)
        paths.append(output)
    return paths,{'exported_pages':misses,'export_cache_hits':hits}

def combine_pages(paths,target):
    if not paths: raise ValueError('Cannot combine an empty slide list')
    data,infos,comment=read_package(paths[0])
    for file in paths[1:]: append_package(data,file)
    write_package(target,data,infos,comment)

def structural(element):
    if element is None: return None
    # Resource-list IDs are navigation, not the rendered master appearance.
    if element.tag=='{'+P+'}sldLayoutIdLst': return None
    text=element.text or ''
    if not text.strip() and element.tag!='{'+A+'}t': text=''
    return [element.tag,sorted(element.attrib.items()),text,
            [structural(child) for child in element if child.tag!='{'+P+'}sldLayoutIdLst']]

def visual_page_keys(pptx):
    """Hash visible page dependencies, ignoring ZIP dates and allocated part paths."""
    with ZipFile(pptx) as package:
        parts=ordered_slide_parts(package)
        data={n:package.read(n) for n in package.namelist() if not n.endswith('/')}
    presentation=ET.fromstring(data['ppt/presentation.xml'])
    root_rels=ET.fromstring(data['ppt/_rels/presentation.xml.rels'])
    excluded={'slide','slideMaster','notesMaster','handoutMaster','presProps','viewProps'}
    memo={}
    def graph(part,visiting=None):
        if part in memo: return memo[part]
        visiting=set() if visiting is None else visiting
        if part in visiting: return 'cycle'
        visiting=visiting|{part}
        content=data[part]
        if part.endswith('.xml'):
            value=structural(ET.fromstring(content))
        else: value=hashlib.sha256(content).hexdigest()
        relationships=[]
        if rels_part(part) in data:
            for rel in ET.fromstring(data[rels_part(part)]):
                kind=rel.get('Type','').rsplit('/',1)[-1]
                if kind in ['notesSlide','slide','comments','commentAuthors']: continue
                if kind=='slideLayout' and '/slideMasters/' in part: continue
                target=rel.get('Target','')
                dependency=target if rel.get('TargetMode')=='External' else graph(target_part(part,target),visiting)
                relationships.append([rel.get('Id'),rel.get('Type'),rel.get('TargetMode'),dependency])
        result=key([value,sorted(relationships,key=lambda r:r[0] or '')])
        memo[part]=result
        return result
    global_styles=[]
    def root_graph(part):
        # A cycle-pruned child hash must not be reused as another page's root:
        # that could omit dependencies reached through its former ancestor.
        memo.clear()
        return graph(part)
    for rel in root_rels:
        if rel.get('Type','').rsplit('/',1)[-1] in excluded: continue
        if rel.get('TargetMode')=='External': continue
        global_styles.append([rel.get('Type'),root_graph(target_part('ppt/presentation.xml',rel.get('Target')))])
    common=[sorted(presentation.attrib.items()),structural(presentation.find('p:sldSz',NS)),
            structural(presentation.find('p:defaultTextStyle',NS)),global_styles]
    result=[]
    for position,part in enumerate(parts,1):
        root=ET.fromstring(data[part])
        fields=[f.get('type','').lower() for f in root.findall('.//a:fld',NS)]
        dynamic={}
        if any('slidenum' in f for f in fields): dynamic['slide_number']=position
        if any('datetime' in f for f in fields): dynamic['time_bucket']=int(time.time()//60)
        result.append(key({'protocol':1,'page':root_graph(part),'global':common,'dynamic':dynamic}))
    return result

def preview_pages(root,pptx,args):
    """Export only cache misses in one LibreOffice PageRange batch, then join cached PDFs."""
    try:
        from pypdf import PdfReader,PdfWriter,__version__ as pdf_version
    except ImportError as error:
        raise RuntimeError('Incremental previews need pypdf; use the bundled Python runtime with its existing document libraries') from error
    from render_editable_preview import render,renderer_identity
    root,pptx=Path(root),Path(pptx)
    output=root/'qa/preview'
    with ResourceLock(output,'preview'):
        return _preview_pages(root,pptx,args,PdfReader,PdfWriter,pdf_version,render,renderer_identity)

def _preview_pages(root,pptx,args,PdfReader,PdfWriter,pdf_version,render,renderer_identity):
    source_hash=digest(pptx)
    renderer=renderer_identity(args)
    renderer['pdf_cache_protocol']=1
    renderer['pdf_library']=pdf_version
    signatures=visual_page_keys(pptx)
    fingerprints=[key([signature,renderer]) for signature in signatures]
    cache=root/'editable/preview-cache'
    work=cache/'.work'
    work.mkdir(parents=True,exist_ok=True)
    entries=[]
    misses,hits=[],[]
    for position,fingerprint in enumerate(fingerprints,1):
        entry=cache/fingerprint[:24]
        valid=False
        try:
            receipt=json.loads((entry/'preview.json').read_text(encoding='utf-8'))
            valid=(receipt['fingerprint']==fingerprint and
                   all((entry/n).is_file() and digest(entry/n)==receipt['files'][n] for n in ['page.pdf','image.jpg']))
        except (OSError,ValueError,KeyError): pass
        entries.append(entry)
        (hits if valid else misses).append(position)
    with TemporaryDirectory(prefix='batch-',dir=work) as temporary:
        stage=Path(temporary).resolve()
        if stage.parent!=work.resolve(): raise RuntimeError('Preview staging escaped its cache workspace')
        if misses:
            batch=SimpleNamespace(input=pptx,output_dir=stage/'rendered',soffice=args.soffice,pdftoppm=args.pdftoppm,
                                  temp_dir=args.temp_dir or SCRIPTS.parent.parents[1]/'.skill-install-temp/ppt',
                                  scale=args.scale,timeout=args.timeout,pages=','.join(map(str,misses)))
            rendered=render(batch)
            reader=PdfReader(rendered['pdf'])
            if len(reader.pages)!=len(misses): raise RuntimeError('Partial PDF export returned the wrong pages')
            for index,position in enumerate(misses):
                entry=entries[position-1]
                single=stage/f'page-{position}.pdf'
                writer=PdfWriter()
                writer.add_page(reader.pages[index])
                with single.open('wb') as stream:
                    writer.write(stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                atomic_copy(single,entry/'page.pdf')
                atomic_copy(rendered['pages'][index],entry/'image.jpg')
                atomic_json(entry/'preview.json',{'fingerprint':fingerprints[position-1],
                            'files':{name:digest(entry/name) for name in ['page.pdf','image.jpg']}})
        aggregate=key(fingerprints)
        artifacts=root/'qa/preview'/f'render-{aggregate[:16]}'
        pdf=artifacts/pptx.with_suffix('.pdf').name
        aggregate_receipt=artifacts/'assembly.json'
        valid=False
        try:
            old=json.loads(aggregate_receipt.read_text(encoding='utf-8'))
            valid=old['fingerprint']==aggregate and pdf.is_file() and digest(pdf)==old['sha256']
        except (OSError,ValueError,KeyError): pass
        if not valid:
            writer=PdfWriter()
            readers=[]  # Keep object identities alive while pypdf clones resources.
            for entry in entries:
                reader=PdfReader(entry/'page.pdf')
                readers.append(reader)
                if len(reader.pages)!=1: raise RuntimeError('Cached page PDF must contain exactly one page')
                writer.add_page(reader.pages[0])
            merged=stage/'complete.pdf'
            with merged.open('wb') as stream:
                writer.write(stream)
                stream.flush()
                os.fsync(stream.fileno())
            atomic_copy(merged,pdf)
            atomic_json(aggregate_receipt,{'fingerprint':aggregate,'sha256':digest(pdf)})
        if digest(pptx)!=source_hash: raise RuntimeError('PPTX changed while page previews were being prepared')
        result={'cached':not misses and valid,'pdf':str(pdf),'pages':[str(e/'image.jpg') for e in entries],
                'rendered_pages':misses,'preview_cache_hits':hits}
        atomic_json(root/'qa/preview/preview-report.json',{'identity':{'pptx_sha256':source_hash,'page_keys':fingerprints},
                    **result,'visual_review':'Not performed by this script; inspect the actual page images.'})
        return result
