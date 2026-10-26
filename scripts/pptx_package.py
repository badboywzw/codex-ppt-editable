"""OPC helpers for preserving an existing PPTX and appending generated slides."""
from copy import deepcopy
from io import BytesIO
import posixpath
import re
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'p':P,'a':A,'r':R,'rel':REL}

def rels_part(part):
    folder,name=posixpath.split(part)
    return posixpath.join(folder,'_rels',name+'.rels')

def target_part(owner,target):
    path=unquote(urlsplit(target).path)
    result=posixpath.normpath(path.lstrip('/') if path.startswith('/') else posixpath.join(posixpath.dirname(owner),path))
    if result=='..' or result.startswith('../'): raise ValueError('Relationship escapes the package')
    return result

def xml_bytes(root,original):
    # Preserve namespace bindings also used by values such as mc:Ignorable.
    bindings={}
    for _,(prefix,uri) in ET.iterparse(BytesIO(original),events=['start-ns']):
        if prefix in bindings and bindings[prefix]!=uri:
            raise ValueError('Namespace rebinding requires a specialized XML editor')
        bindings[prefix]=uri
    for prefix,uri in bindings.items():
        if not re.fullmatch(r'ns\d+',prefix): ET.register_namespace(prefix,uri)
    text=ET.tostring(root,encoding='unicode')
    end=text.index('>')
    opening=text[:end]
    declarations=[]
    for prefix,uri in bindings.items():
        attr='xmlns'+(':'+prefix if prefix else '')
        if not re.search(r'\s'+re.escape(attr)+r'=',opening):
            escaped=uri.replace('&','&amp;').replace('"','&quot;')
            declarations.append(f' {attr}="{escaped}"')
    if declarations:
        at=end-1 if text[end-1]=='/' else end
        text=text[:at]+''.join(declarations)+text[at:]
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'+text).encode('utf-8')

def ordered_slide_parts(package):
    presentation=ET.fromstring(package.read('ppt/presentation.xml'))
    relationships=ET.fromstring(package.read('ppt/_rels/presentation.xml.rels'))
    targets={r.get('Id'):r.get('Target') for r in relationships if r.get('Type','').endswith('/slide')}
    parts=[]
    for slide in presentation.findall('p:sldIdLst/p:sldId',NS):
        rid=slide.get('{'+R+'}id')
        if rid not in targets: raise ValueError(f'Slide relationship missing: {rid}')
        part=target_part('ppt/presentation.xml',targets[rid])
        if part not in package.namelist(): raise ValueError(f'Slide part missing: {part}')
        parts.append(part)
    if len(set(parts))!=len(parts): raise ValueError('Repeated slide parts are unsupported')
    return parts

def read_package(path):
    with ZipFile(path) as package:
        corrupt=package.testzip()
        if corrupt: raise ValueError(f'Corrupt PPTX member: {corrupt}')
        if any(name.startswith('_xmlsignatures/') for name in package.namelist()):
            raise ValueError('Signed PPTX requires signature-aware handling')
        if len(set(package.namelist()))!=len(package.namelist()): raise ValueError('Duplicate ZIP members')
        data={info.filename:package.read(info.filename) for info in package.infolist() if not info.is_dir()}
        infos={info.filename:info for info in package.infolist() if not info.is_dir()}
        return data,infos,package.comment

def validate_relationships(data):
    for file,content in data.items():
        if not file.endswith('.rels'): continue
        if file=='_rels/.rels': owner=''
        else:
            folder,name=posixpath.split(file)
            owner=posixpath.join(posixpath.dirname(folder),name[:-5])
        for rel in ET.fromstring(content):
            if rel.get('TargetMode')=='External': continue
            target=rel.get('Target','')
            if not target or (not urlsplit(target).path and urlsplit(target).fragment): continue
            part=target_part(owner,target)
            if part not in data: raise ValueError(f'Broken relationship: {file} -> {target}')

def append_package(data,additional_path):
    """Import generated slide dependency closures while keeping all base parts."""
    added,_,_=read_package(additional_path)
    with ZipFile(additional_path) as source_zip:
        source_slides=ordered_slide_parts(source_zip)
    base_presentation=ET.fromstring(data['ppt/presentation.xml'])
    source_presentation=ET.fromstring(added['ppt/presentation.xml'])
    for key in ['cx','cy']:
        if base_presentation.find('p:sldSz',NS).get(key)!=source_presentation.find('p:sldSz',NS).get(key):
            # Different physical sizes with the same aspect ratio can be scaled
            # only by rewriting every new shape. Keep the append contract exact.
            raise ValueError('Appended pages must use the same physical slide size as the base')
    mapping={}
    occupied=set(data)
    def blank_notes(part):
        root=ET.fromstring(added[part])
        for shape in root.findall('.//p:sp',NS):
            placeholder=shape.find('p:nvSpPr/p:nvPr/p:ph',NS)
            if placeholder is not None and placeholder.get('type') in ['sldNum','dt','hdr','ftr','sldImg']:
                continue
            if any((t.text or '').strip() for t in shape.findall('.//a:t',NS)): return False
        return True
    keep_notes=any(not blank_notes(part) for part in added
                   if re.fullmatch(r'ppt/notesSlides/[^/]+\.xml',part))
    def allocate(part):
        if part not in occupied:
            occupied.add(part)
            return part
        folder,name=posixpath.split(part)
        stem,extension=posixpath.splitext(name)
        stem=re.sub(r'\d+$','',stem)
        number=1
        while True:
            candidate=posixpath.join(folder,f'{stem}{number}{extension}')
            if candidate not in occupied:
                occupied.add(candidate)
                return candidate
            number+=1
    def copy_part(part):
        if part in mapping: return mapping[part]
        if part not in added: raise ValueError(f'Append dependency missing: {part}')
        dest=allocate(part)
        mapping[part]=dest
        data[dest]=added[part]
        relationships=rels_part(part)
        if relationships in added:
            root=ET.fromstring(added[relationships])
            for rel in list(root):
                if rel.get('TargetMode')=='External': continue
                raw=rel.get('Target','')
                if not raw: raise ValueError('Empty append relationship target')
                if rel.get('Type','').endswith('/notesSlide') and blank_notes(target_part(part,raw)):
                    # PPTXGenJS emits empty notes for every new page. Do not
                    # import an extra notes-master tree for those empty pages.
                    root.remove(rel)
                    continue
                target=copy_part(target_part(part,raw))
                suffix=urlsplit(raw).fragment
                rel.set('Target',posixpath.relpath(target,posixpath.dirname(dest))+('#'+suffix if suffix else ''))
            data[rels_part(dest)]=xml_bytes(root,added[relationships])
        return dest
    root_rels=ET.fromstring(data['ppt/_rels/presentation.xml.rels'])
    used_rids={r.get('Id') for r in root_rels}
    def new_relationship(part,kind):
        number=1
        while f'rId{number}' in used_rids: number+=1
        rid=f'rId{number}'
        used_rids.add(rid)
        ET.SubElement(root_rels,'{'+REL+'}Relationship',{'Id':rid,'Type':R+'/'+kind,
                      'Target':posixpath.relpath(part,'ppt')})
        return rid
    def ensure_list(name):
        result=base_presentation.find('p:'+name,NS)
        if result is None:
            result=ET.Element('{'+P+'}'+name)
            size=base_presentation.find('p:sldSz',NS)
            base_presentation.insert(list(base_presentation).index(size) if size is not None else 0,result)
        return result
    def unique_numeric(existing,start):
        value=max(existing,default=start-1)+1
        if value>=2**32: value=start
        while value in existing: value+=1
        existing.add(value)
        return str(value)
    source_root_rels=ET.fromstring(added['ppt/_rels/presentation.xml.rels'])
    source_relationships={r.get('Id'):r for r in source_root_rels}
    # Master/layout resource IDs share the high-ID range in Office files. Give
    # appended resources fresh IDs instead of duplicating a base layout's ID.
    resource_ids={int(e.get('id')) for e in base_presentation.findall('p:sldMasterIdLst/p:sldMasterId',NS)}
    for part,content in list(data.items()):
        if re.fullmatch(r'ppt/slideMasters/[^/]+\.xml',part):
            master=ET.fromstring(content)
            resource_ids.update(int(e.get('id')) for e in master.findall('p:sldLayoutIdLst/p:sldLayoutId',NS))
    # Imported slide/notes masters carry their own themes and layouts.
    for tag,child,kind in [('sldMasterIdLst','sldMasterId','slideMaster'),
                           ('notesMasterIdLst','notesMasterId','notesMaster')]:
        source_list=source_presentation.find('p:'+tag,NS)
        if source_list is None: continue
        if kind=='notesMaster' and not keep_notes: continue
        base_list=ensure_list(tag)
        numbers={int(e.get('id')) for e in base_list if e.get('id')}
        for entry in source_list:
            relationship=source_relationships[entry.get('{'+R+'}id')]
            original=target_part('ppt/presentation.xml',relationship.get('Target'))
            copied_part=copy_part(original)
            rid=new_relationship(copied_part,kind)
            attrs={'{'+R+'}id':rid}
            if entry.get('id') is not None:
                attrs['id']=unique_numeric(resource_ids,2**31)
                master=ET.fromstring(data[copied_part])
                for layout in master.findall('p:sldLayoutIdLst/p:sldLayoutId',NS):
                    layout.set('id',unique_numeric(resource_ids,2**31))
                data[copied_part]=xml_bytes(master,data[copied_part])
            ET.SubElement(base_list,'{'+P+'}'+child,attrs)
    slide_list=ensure_list('sldIdLst')
    slide_ids={int(s.get('id')) for s in slide_list}
    new_ids=[]
    for part in source_slides:
        rid=new_relationship(copy_part(part),'slide')
        number=unique_numeric(slide_ids,256)
        new_ids.append(number)
        ET.SubElement(slide_list,'{'+P+'}sldId',{'id':number,'{'+R+'}id':rid})
    # Existing sections continue to contain new final pages in their last section.
    p14='http://schemas.microsoft.com/office/powerpoint/2010/main'
    section_lists=base_presentation.findall('.//{'+p14+'}section/{'+p14+'}sldIdLst')
    if section_lists:
        for number in new_ids: ET.SubElement(section_lists[-1],'{'+p14+'}sldId',{'id':number})
    types=ET.fromstring(data['[Content_Types].xml'])
    existing_defaults={e.get('Extension'):e.get('ContentType') for e in types if e.tag.endswith('Default')}
    source_types=ET.fromstring(added['[Content_Types].xml'])
    for entry in source_types:
        if entry.tag.endswith('Default'):
            ext=entry.get('Extension')
            if ext in existing_defaults and existing_defaults[ext]!=entry.get('ContentType'):
                raise ValueError(f'Conflicting content type for {ext}')
            if ext not in existing_defaults:
                types.append(deepcopy(entry))
                existing_defaults[ext]=entry.get('ContentType')
        elif entry.get('PartName','').lstrip('/') in mapping:
            copied=deepcopy(entry)
            copied.set('PartName','/'+mapping[entry.get('PartName').lstrip('/')])
            types.append(copied)
    data['[Content_Types].xml']=xml_bytes(types,data['[Content_Types].xml'])
    data['ppt/presentation.xml']=xml_bytes(base_presentation,data['ppt/presentation.xml'])
    data['ppt/_rels/presentation.xml.rels']=xml_bytes(root_rels,data['ppt/_rels/presentation.xml.rels'])
    if 'docProps/app.xml' in data:
        app=ET.fromstring(data['docProps/app.xml'])
        slides=app.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides')
        if slides is not None:
            slides.text=str(len(slide_list))
            data['docProps/app.xml']=xml_bytes(app,data['docProps/app.xml'])
    return len(source_slides)

def write_package(path,data,infos,comment=b''):
    validate_relationships(data)
    with ZipFile(path,'w',ZIP_DEFLATED) as output:
        output.comment=comment
        for name,content in data.items():
            output.writestr(infos.get(name,name),content)
