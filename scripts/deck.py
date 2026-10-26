"""Plan, build, check and resume a codex-ppt project from one deck.json."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from zipfile import BadZipFile
import xml.etree.ElementTree as ET

from deck_layouts import LAYOUTS, compile_deck
from check_editable_pptx import check as check_pptx
from pptx_edit import inspect_pptx, resolve_base, assemble, expected_text
from project_io import ResourceLock,atomic_write,atomic_json,atomic_copy,project_staging,recover_publication,publish_pptx
from slide_cache import export_pages,combine_pages,preview_pages

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / 'scripts'
MARKER = '.codex-ppt-project.json'

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file() and path.read_text(encoding='utf-8-sig') == content:
        return
    atomic_write(path,content)

def write_json(path,value):
    write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def status(message):
    print(message,file=sys.stderr,flush=True)

def run_json(command,timeout):
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',
                          timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:
        raise RuntimeError((result.stderr+'\n'+result.stdout).strip()[-3000:])
    return json.loads(result.stdout)

def project(source_path):
    source_path=source_path.resolve(strict=True)
    root=source_path.parent
    marker=root/MARKER
    if not marker.is_file() or read_json(marker).get('tool')!='codex-ppt':
        raise ValueError('Use "deck.py init NEW_FOLDER" first; unowned folders are not overwritten')
    raw=source_path.read_bytes()
    source=json.loads(raw.decode('utf-8-sig'))
    imported=None
    if source.get('base') is not None:
        base=source['base']
        imported=resolve_base((root/base['file']).resolve(strict=True),base['sha256'],base.get('slides',[]))
    count=imported['slide_count'] if imported else 0
    compiled=compile_deck(source,root,allow_empty=imported is not None,page_offset=count)
    compiled['source_sha256']=hashlib.sha256(raw).hexdigest()
    if imported:
        if compiled['pages'] and abs(imported['original']['width_emu']/imported['original']['height_emu']-16/9)>.0002:
            raise ValueError('Appending layouts currently requires a 16:9 base; native text-only edits keep the original size')
        compiled['native_base']=imported
    return root,source,compiled

def document_plan(root,source,compiled):
    """Derived documents are generated views; deck.json stays authoritative."""
    pages=compiled['pages']
    write(root/'brief.md',f'# {source["title"]}\n\n'+
          '\n'.join(f'{key}: {source[key]}' for key in ['audience','objective','language','tone'] if key in source)+
          f'\n\nOutput: editable-pptx; slides: {len(pages)+compiled.get("native_base",{}).get("slide_count",0)}.\nSource: deck.json.\n')
    storyline=source.get('storyline') or ' → '.join(p['title'] for p in pages)
    write(root/'storyline.md','# Storyline\n\n'+stringify(storyline)+'\n')
    write(root/'design-system.md','# Design system\n\n'+json.dumps(compiled['theme'],ensure_ascii=False,indent=2)+
          '\n\n960×540 coordinate canvas; font sizes are PowerPoint points. Transparent native text.\n'+
          stringify(source.get('visual_direction',''))+'\n')
    storyboard=['# Storyboard (generated from deck.json)\n']
    for page in compiled.get('native_base',{}).get('resolved',[]):
        storyboard.append(f'## Preserved page {page["page"]}: {page["part"]}\n')
        for frame in page['texts']:
            storyboard.append(f'- shape {frame["id"]} / {frame["name"]}: '+frame['text'].replace('\n',' / ')+'\n')
    for p in pages:
        entry=p['spec']
        storyboard.append(f'## {p["id"]:02} · {p["title"]}\n\nLayout: {p["layout"]}\n')
        for key in ['role','takeaway','risk']:
            if entry.get(key): storyboard.append(f'{key}: {entry[key]}\n')
        for frame in p['texts']:
            storyboard.append(f'- {frame["name"]}: '+frame['text'].replace('\n',' / ')+
                              f' | ({frame["x"]}, {frame["y"]}, {frame["w"]}, {frame["h"]}) | {frame["size"]}pt\n')
    write(root/'storyboard.md','\n'.join(storyboard))

def stringify(value):
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)

def prepare(root,source,compiled):
    used={v['asset'] for p in compiled['pages'] for v in p['visuals']}
    pending=[]
    compiled['asset_source_hashes']={}
    for name in sorted(used):
        asset=compiled['assets'][name]
        if not asset['path'].is_file(): pending.append({'asset':name,'file':str(asset['path'])})
        if asset.get('prompt'):
            prompt=(asset['prompt'].strip()+'\n\n'+
                    'Textless artwork only. No words, Chinese characters, letters, numbers, labels, logos, watermarks or placeholders. '+
                    'Keep the planned text regions empty. Exact presentation wording is added as native PowerPoint text.\n')
            write(root/f'prompts/{name}.txt',prompt)
    for page in compiled['pages']:
        folder=root/f'editable/visual-layers/slide-{page["id"]:02}'
        assets=[]
        for visual in page['visuals']:
            name=visual['asset']
            original=compiled['assets'][name]['path']
            suffix=original.suffix.lower()
            if suffix not in ['.png','.jpg','.jpeg','.svg']:
                raise ValueError(f'Asset {name}: use PNG, JPEG or SVG')
            target=folder/f'asset-{name}{suffix}'
            target.parent.mkdir(parents=True,exist_ok=True)
            if original.is_file():
                stamp=digest(original)
                if not target.exists() or stamp!=digest(target):
                    if original.resolve()!=target.resolve(): atomic_copy(original,target)
                if digest(target)!=stamp: raise RuntimeError(f'Asset changed during copying: {original}')
                compiled['asset_source_hashes'][str(original)]=stamp
            assets.append({'file':target.name,'name':f'asset:{name}','position':visual['position'],'canvas':[960,540]})
        write(folder/'layout.svg',page['svg'])
        assets.append({'file':'layout.svg','name':f'layout:{page["layout"]}','position':[0,0,960,540],'canvas':[960,540]})
        write_json(folder/'manifest.json',{'assets':assets})
    base=compiled.get('native_base')
    if base:
        write_json(root/'editable/append-text-layer.json',compiled['text_source'])
    final_text=expected_text(base,compiled['text_source']) if base else compiled['text_source']
    write_json(root/'editable/text-layer.json',final_text)
    document_plan(root,source,compiled)
    result={'slides':len(final_text['slides']),'native_text_objects':sum(bool(t['text'].strip()) for p in final_text['slides'] for t in p['texts']),
            'pending_assets':pending,'layout_warnings':compiled['warnings'],'used_assets':sorted(used)}
    if base: result.update(preserved_base_slides=base['slide_count'],appended_slides=len(compiled['pages']))
    write_json(root/'qa/plan-report.json',result)
    return result

def init_project(args):
    root=args.folder.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('The project folder must be new or empty')
    example=args.example or SKILL/'assets/examples/starter.json'
    source=read_json(example.resolve(strict=True))
    if args.title: source['title']=source['slides'][0]['title']=args.title
    # Validate before claiming/writing the empty project.
    compile_deck(source,root)
    with project_staging(root) as stage:
        write_json(stage/MARKER,{'tool':'codex-ppt','schema_version':1,'project_id':str(uuid.uuid4())})
        write_json(stage/'deck.json',source)
    return {'project':str(root),'source':str(root/'deck.json'),'next':'Edit deck.json, then run plan or build'}

def import_project(args):
    incoming=args.pptx.resolve(strict=True)
    root=args.folder.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Import destination must be new or empty; the latest PPTX is not overwritten')
    snapshot=inspect_pptx(incoming)
    incoming_hash=digest(incoming)
    title=args.title or incoming.stem
    with project_staging(root) as stage:
        original=stage/'source/original.pptx'
        atomic_copy(incoming,original)
        if digest(original)!=incoming_hash: raise ValueError('Input changed during import; retry from its latest saved version')
        snapshot=inspect_pptx(original)
        source={'schema_version':1,'title':title,'filename':title+'-续作.pptx',
                'base':{'file':'source/original.pptx','sha256':incoming_hash,'slides':snapshot['slides']},'assets':{},'slides':[]}
        write_json(stage/MARKER,{'tool':'codex-ppt','schema_version':1,'project_id':str(uuid.uuid4())})
        write_json(stage/'deck.json',source)
        report={'project':str(root),'source':str(root/'deck.json'),'imported_from':str(incoming),
                'preserved_slides':len(snapshot['slides']),'native_text_objects':snapshot['native_text_objects'],
                'complex_text_objects':snapshot['complex_text_objects'],
                'next':'Edit native base text fields or append layouts in slides, then build. Original package objects stay preserved.'}
        write_json(stage/'qa/import-report.json',report)
    return report

def artifact_identity(compiled,node,backend):
    used={v['asset'] for p in compiled['pages'] for v in p['visuals']}
    value={'text':compiled['text_source'],
           'pages':[{'id':p['id'],'svg':p['svg'],'visuals':p['visuals']} for p in compiled['pages']],
           'assets':{n:digest(compiled['assets'][n]['path']) for n in sorted(used)},
            'engine':{n:digest(SCRIPTS/n) for n in ['deck.py','deck_layouts.py','build_editable_ppt_from_layers.mjs','pptx_package.py','pptx_edit.py','slide_cache.py','project_io.py']},
           'node':{'path':str(Path(node).resolve()),'mtime_ns':Path(node).stat().st_mtime_ns} if node else None,'backend':backend,
           'packages':{str(p.relative_to(SKILL)):digest(p) for p in
                       [SKILL/'package.json',SKILL/'node_modules/pptxgenjs/package.json'] if p.is_file()}}
    if compiled.get('native_base'):
        base=compiled['native_base']
        value['base']={'sha256':base['sha256'],'resolved':base['resolved']}
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def find_node(explicit):
    candidate=explicit or os.environ.get('CODEX_PPT_NODE') or shutil.which('node')
    resolved=shutil.which(str(candidate)) if candidate else None
    if not resolved and candidate and Path(candidate).is_file(): resolved=str(Path(candidate).resolve())
    if not resolved: raise ValueError('Node.js not found; pass --node with the bundled runtime path')
    return resolved

def default_output(root,source):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','-',source.get('filename') or source['title']).strip(' .')[:90]
    if not name or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?',name): name='deck'
    if not name.lower().endswith('.pptx'): name+='.pptx'
    return root/'final'/name

def build(args):
    root,source,compiled=project(args.source)
    status('Planning from deck.json')
    plan=prepare(root,source,compiled)
    if plan['pending_assets']:
        raise ValueError('Artwork is missing. Generate/copy only these assets, then rerun build: '+
                         json.dumps(plan['pending_assets'],ensure_ascii=False))
    base=compiled.get('native_base')
    preserved=base['slide_count'] if base else 0
    node=find_node(args.node) if compiled['pages'] else None
    if base and compiled['pages'] and args.backend!='pptxgenjs':
        raise ValueError('Appending to a native base currently uses --backend pptxgenjs')
    out=(args.out or default_output(root,source)).resolve()
    if out.suffix.lower()!='.pptx': raise ValueError('--out must end in .pptx')
    with ResourceLock(out,'output'):
        return build_output(args,root,compiled,plan,out,node)

def build_output(args,root,compiled,plan,out,node):
    base=compiled.get('native_base')
    preserved=base['slide_count'] if base else 0
    state_path=root/'qa/pipeline-state.json'
    recovered=recover_publication(root,out,state_path,args.source)
    try: state=read_json(state_path) if state_path.exists() else {}
    except (OSError,ValueError) as error:
        raise ValueError('Build state is unreadable; preserve/import the latest PPTX instead of overwriting it') from error
    existing_hash=digest(out) if out.is_file() else None
    if out.exists() and (state.get('output')!=str(out) or state.get('output_sha256')!=existing_hash):
        raise ValueError('The existing PPTX is untracked or was changed manually. Continue it with import-pptx into a new project. --out with a NEW filename makes a separate export, not a recovery of manual edits')
    fingerprint=artifact_identity(compiled,node,args.backend)
    cached=(state.get('build_fingerprint')==fingerprint and state.get('output')==str(out)
            and existing_hash is not None and state.get('output_sha256')==existing_hash)
    stage='build'
    temporary=None
    export_stats={'exported_pages':[],'export_cache_hits':list(range(preserved+1,plan['slides']+1))}
    try:
        if not cached:
            status('Building editable PPTX')
            out.parent.mkdir(parents=True,exist_ok=True)
            temporary=out.parent/f'.codex-ppt-{uuid.uuid4().hex}.pptx'
            append_file=None
            manifest={}
            if args.backend=='pptxgenjs':
                width=base['original']['width_emu']/914400 if base else 10
                pages,export_stats=export_pages(root,compiled,node,width,args.timeout)
                if base:
                    if len(pages)>1:
                        append_file=out.parent/f'.codex-ppt-append-{uuid.uuid4().hex}.pptx'
                        combine_pages(pages,append_file)
                    elif pages: append_file=pages[0]
                    manifest['native_continuation']=assemble(base,append_file,temporary)
                    if append_file is not None and append_file.parent==out.parent and append_file.name.startswith('.codex-ppt-append-'):
                        append_file.unlink()
                else:
                    combine_pages(pages,temporary)
                manifest.update(backend='pptxgenjs',slideCount=plan['slides'],page_cache=export_stats)
            elif compiled['pages']:
                append_file=out.parent/f'.codex-ppt-append-{uuid.uuid4().hex}.pptx' if base else temporary
                command=[node,str(SCRIPTS/'build_editable_ppt_from_layers.mjs'),'--backend',args.backend,
                         '--layers-root',str(root/'editable/visual-layers'),
                         '--text-json',str(root/'editable/append-text-layer.json' if base else root/'editable/text-layer.json'),
                         '--out',str(append_file),'--workspace',str(root/'editable/workspace'),'--slide-size','960x540','--fail-on-text-fill']
                if base: command+=['--pptx-width',str(base['original']['width_emu']/914400)]
                manifest=run_json(command,args.timeout)
                export_stats={'exported_pages':list(range(1,plan['slides']+1)),'export_cache_hits':[]}
            if base and args.backend!='pptxgenjs':
                manifest['native_continuation']=assemble(base,append_file,temporary)
                if append_file is not None: append_file.unlink()
            checked=check_pptx(temporary,root/'editable/text-layer.json',preserved)
            if not checked['passed']: raise RuntimeError('PPTX text check failed: '+json.dumps(checked['errors'],ensure_ascii=False))
            for file,stamp in compiled['asset_source_hashes'].items():
                if digest(Path(file))!=stamp: raise RuntimeError('Artwork changed during build; rerun with its latest saved version')
            if base and digest(base['path'])!=base['sha256']: raise RuntimeError('Imported base changed during build')
            new_state={'output':str(out),'output_sha256':digest(temporary),'build_fingerprint':fingerprint,'stage':'checked'}
            publish_pptx(root,temporary,out,existing_hash,state_path,new_state,args.source,compiled['source_sha256'])
            state=new_state
            temporary=None
            manifest['output']=str(out)
            write_json(root/'qa/build-report.json',manifest)
        else:
            status('Reusing unchanged PPTX')
            checked=check_pptx(out,root/'editable/text-layer.json',preserved)
            if not checked['passed']: raise RuntimeError('Cached PPTX failed text verification')
        write_json(root/'qa/editability.json',checked)
        preview=None
        if not args.no_preview:
            stage='preview'
            status('Rendering or reusing verified previews')
            preview=preview_pages(root,out,args)
            if len(preview['pages'])!=plan['slides']: raise RuntimeError('Preview page count does not match source')
            pdf_out=out.with_suffix('.preview.pdf')
            if not pdf_out.exists() or digest(Path(preview['pdf']))!=digest(pdf_out):
                atomic_copy(preview['pdf'],pdf_out)
            preview['delivery_pdf']=str(pdf_out)
        state.update(stage='preview-ready' if preview else 'checked',last_error=None)
        write_json(state_path,state)
        result={'pptx':str(out),'build_cached':cached,'preview':preview,'slides':plan['slides'],
                'native_text_objects':checked['native_text_objects'],'layout_warnings':plan['layout_warnings'],
                'visual_review_required':True,'source':str(args.source.resolve()),**export_stats,'recovery':recovered}
        write_json(root/'qa/pipeline-report.json',result)
        write(root/'qa/automated-checks.md','# Delivery checks\n\nNative text verification passed.\n'+
              f'Slides: {plan["slides"]}; editable text objects: {checked["native_text_objects"]}.\n'+
              ('Previews ready. ' if preview else 'Preview generation was explicitly skipped. ')+
              'Visual review is still required; scripts cannot prove artwork is textless or layout is attractive.\n'+
              '\nLayout estimates:\n'+'\n'.join('- '+w for w in plan['layout_warnings'])+'\n')
        if not (root/'qa/qa.md').exists():
            write(root/'qa/qa.md','# Visual review\n\nPending. Inspect the actual rendered pages and record page-specific findings here.\n'+
                  'Automated status is separate in automated-checks.md; reruns preserve this review file.\n')
        return result
    except Exception as error:
        # Keep a successfully exported/checksummed PPTX if preview failed.
        state.update(stage=stage+'-failed',last_error=str(error))
        if temporary is not None and temporary.is_file(): state['uncommitted_export']=str(temporary)
        write_json(state_path,state)
        raise

def dispatch(args):
    if args.command=='layouts': return LAYOUTS
    if args.command=='init': return init_project(args)
    if args.command=='import-pptx': return import_project(args)
    if args.command=='inspect-pptx':
        result=inspect_pptx(args.pptx.resolve(strict=True))
        if args.slide is not None:
            if not 1<=args.slide<=len(result['slides']): raise ValueError('Slide number is out of range')
            result['slides']=[result['slides'][args.slide-1]]
        return result
    if args.command=='plan':
        root,source,compiled=project(args.source)
        return prepare(root,source,compiled)
    return build(args)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('layouts',help='List reusable layouts')
    init=commands.add_parser('init',help='Create a new, owned deck project')
    init.add_argument('folder',type=Path)
    init.add_argument('--example',type=Path)
    init.add_argument('--title')
    native=commands.add_parser('import-pptx',help='Continue from the latest saved native PPTX, preserving its package objects')
    native.add_argument('pptx',type=Path)
    native.add_argument('folder',type=Path)
    native.add_argument('--title')
    inspect=commands.add_parser('inspect-pptx',help='Read native text, positions and style without exporting')
    inspect.add_argument('pptx',type=Path)
    inspect.add_argument('--slide',type=int)
    plan=commands.add_parser('plan',help='Validate source and prepare derived files/prompts; no AI calls')
    plan.add_argument('source',type=Path)
    export=commands.add_parser('build',help='Plan, export, check and preview; unchanged stages are reused')
    export.add_argument('source',type=Path)
    export.add_argument('--out',type=Path)
    export.add_argument('--node')
    export.add_argument('--backend',choices=['pptxgenjs','auto','artifact'],default='pptxgenjs')
    export.add_argument('--no-preview',action='store_true')
    export.add_argument('--temp-dir',type=Path)
    export.add_argument('--soffice')
    export.add_argument('--pdftoppm')
    export.add_argument('--scale',type=int,default=1600)
    export.add_argument('--timeout',type=int,default=45)
    args=parser.parse_args()
    if args.command=='build' and (args.scale<=0 or args.timeout<=0): parser.error('Scale and timeout must be positive')
    try:
        if args.command in ['layouts','inspect-pptx']:
            result=dispatch(args)
        else:
            root=(args.folder if args.command in ['init','import-pptx'] else args.source.parent).resolve()
            with ResourceLock(root,'project'):
                result=dispatch(args)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,BadZipFile,ET.ParseError,subprocess.TimeoutExpired) as error:
        print(f'codex-ppt: {error}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
