"""Read native text and patch an immutable PPTX base without rebuilding its pages."""
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
import hashlib
import math
import re
import xml.etree.ElementTree as ET

from pptx_package import A,P,NS,ordered_slide_parts,read_package,xml_bytes,append_package,write_package

FIELDS={'name','text','x','y','w','h','rotation','size','typeface','color','bold','italic','align'}

def sha256(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def shape_text(shape):
    paragraphs=[]
    for paragraph in shape.findall('p:txBody/a:p',NS):
        parts=[]
        for child in paragraph:
            if child.tag=='{'+A+'}br': parts.append('\n')
            elif child.tag in ['{'+A+'}r','{'+A+'}fld']:
                parts.append(''.join(t.text or '' for t in child.findall('a:t',NS)))
        paragraphs.append(''.join(parts))
    return '\n'.join(paragraphs)

def signature(element):
    if element is None: return None
    return (element.tag,tuple(sorted((k,v) for k,v in element.attrib.items() if k not in ['dirty','smtClean','err'])),
            tuple(signature(c) for c in element))

def text_replaceable(shape):
    if shape.find('.//a:fld',NS) is not None: return False
    runs=shape.findall('p:txBody/a:p/a:r',NS)
    return len({signature(r.find('a:rPr',NS)) for r in runs})<=1

def native_shapes(root):
    parents={c:p for p in root.iter() for c in p}
    for shape in root.findall('.//p:sp',NS):
        if shape.find('p:txBody',NS) is None: continue
        parent=parents.get(shape)
        grouped=False
        while parent is not None:
            if parent.tag=='{'+P+'}grpSp': grouped=True
            parent=parents.get(parent)
        yield shape,grouped

def properties(shape):
    styles=[]
    aligns=[]
    for paragraph in shape.findall('p:txBody/a:p',NS):
        ppr=paragraph.find('a:pPr',NS)
        default=ppr.find('a:defRPr',NS) if ppr is not None else None
        aligns.append(ppr.get('algn') if ppr is not None else None)
        for run in list(paragraph.findall('a:r',NS))+list(paragraph.findall('a:fld',NS)):
            rpr=run.find('a:rPr',NS)
            def attr(key):
                value=rpr.get(key) if rpr is not None else None
                return value if value is not None else default.get(key) if default is not None else None
            def node(path):
                value=rpr.find(path,NS) if rpr is not None else None
                return value if value is not None else default.find(path,NS) if default is not None else None
            color=node('a:solidFill/a:srgbClr')
            font=node('a:ea')
            if font is None: font=node('a:latin')
            size=attr('sz')
            styles.append({'size':float(size)/100 if size else None,
                           'typeface':font.get('typeface') if font is not None else None,
                           'color':'#'+color.get('val') if color is not None and len(color)==0 else None,
                           'bold':attr('b') in ['1','true'] if attr('b') is not None else None,
                           'italic':attr('i') in ['1','true'] if attr('i') is not None else None})
    result={}
    for key in ['size','typeface','color','bold','italic']:
        values=[s[key] for s in styles]
        result[key]=values[0] if values and all(v==values[0] for v in values) else None
    mapping={'l':'left','ctr':'center','r':'right','just':'justify'}
    result['align']=mapping.get(aligns[0]) if aligns and all(a==aligns[0] for a in aligns) else None
    return result

def inspect_pptx(path):
    data,_,_=read_package(path)
    presentation=ET.fromstring(data['ppt/presentation.xml'])
    size=presentation.find('p:sldSz',NS)
    width,height=int(size.get('cx')),int(size.get('cy'))
    if width<=0 or height<=0: raise ValueError('Invalid slide size')
    factor=width/960
    with ZipFile(path) as package: parts=ordered_slide_parts(package)
    if not parts: raise ValueError('The PPTX has no slides')
    pages=[]
    for number,part in enumerate(parts,1):
        root=ET.fromstring(data[part])
        objects=[]
        ids=set()
        for shape,grouped in native_shapes(root):
            info=shape.find('p:nvSpPr/p:cNvPr',NS)
            if info is None or not info.get('id'): raise ValueError('Native text shape lacks an ID')
            sid=info.get('id')
            if sid in ids: raise ValueError('Duplicate native text shape ID')
            ids.add(sid)
            item={'id':sid,'name':info.get('name',''),'text':shape_text(shape),**properties(shape),
                  'text_editable':text_replaceable(shape),'position_editable':False}
            xfrm=shape.find('p:spPr/a:xfrm',NS)
            if not grouped and xfrm is not None:
                off,ext=xfrm.find('a:off',NS),xfrm.find('a:ext',NS)
                if off is not None and ext is not None:
                    item.update(x=round(int(off.get('x'))/factor,6),y=round(int(off.get('y'))/factor,6),
                                w=round(int(ext.get('cx'))/factor,6),h=round(int(ext.get('cy'))/factor,6),
                                rotation=float(xfrm.get('rot','0'))/60000,position_editable=True)
            objects.append(item)
        pages.append({'page':number,'part':part,'texts':objects})
    return {'width_emu':width,'height_emu':height,'canvas':[960,height/factor],'slides':pages,
            'native_text_objects':sum(bool(t['text'].strip()) for p in pages for t in p['texts']),
            'complex_text_objects':sum(not t['text_editable'] for p in pages for t in p['texts'])}

def resolve_base(path,expected_hash,edits):
    if sha256(path)!=expected_hash: raise ValueError('Imported source PPTX changed; import the latest file into a new project')
    original=inspect_pptx(path)
    resolved=deepcopy(original['slides'])
    by_part={p['part']:p for p in resolved}
    if not isinstance(edits,list): raise ValueError('base.slides must be a list')
    seen=set()
    for page in edits:
        part=page.get('part')
        if part not in by_part or part in seen: raise ValueError(f'Unknown or duplicate imported slide part: {part}')
        seen.add(part)
        objects={t['id']:t for t in by_part[part]['texts']}
        ids=set()
        for item in page.get('texts',[]):
            sid=str(item.get('id'))
            if sid not in objects or sid in ids: raise ValueError(f'Unknown or duplicate text shape ID: {sid}')
            ids.add(sid)
            old=objects[sid]
            for field,value in item.items():
                if field in FIELDS:
                    if value==old.get(field): continue
                    if field=='text' and not old['text_editable']:
                        raise ValueError(f'{part} shape {sid}: mixed runs/fields require specialized text editing; unchanged rich text is preserved')
                    if field in ['x','y','w','h','rotation'] and not old['position_editable']:
                        raise ValueError(f'{part} shape {sid}: grouped/inherited position is read-only')
                    if field in ['x','y','w','h','rotation','size']:
                        if type(value) not in [int,float] or not math.isfinite(value) or (field in ['w','h','size'] and value<=0):
                            raise ValueError(f'Invalid imported text {field}')
                    elif field in ['text','name','typeface']:
                        if not isinstance(value,str) or (field=='typeface' and not value): raise ValueError(f'Invalid imported {field}')
                    elif field=='color':
                        if not isinstance(value,str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}',value): raise ValueError('Imported color requires #RRGGBB')
                    elif field in ['bold','italic'] and type(value) is not bool: raise ValueError(f'Invalid imported {field}')
                    elif field=='align' and value not in ['left','center','right','justify']: raise ValueError('Invalid imported alignment')
                    old[field]=value
                elif field not in old or value!=old[field]:
                    raise ValueError(f'Unsupported imported text field: {field}')
    return {'path':path,'sha256':expected_hash,'original':original,'resolved':resolved,
            'edits':edits,'slide_count':len(resolved)}

def replace_text(shape,value):
    body=shape.find('p:txBody',NS)
    old=body.findall('a:p',NS)
    template_run=shape.find('p:txBody/a:p/a:r/a:rPr',NS)
    for paragraph in old: body.remove(paragraph)
    for index,line in enumerate(value.split('\n')):
        paragraph=ET.SubElement(body,'{'+A+'}p')
        previous=old[min(index,len(old)-1)] if old else None
        ppr=previous.find('a:pPr',NS) if previous is not None else None
        if ppr is not None: paragraph.append(deepcopy(ppr))
        run=ET.SubElement(paragraph,'{'+A+'}r')
        if template_run is not None: run.append(deepcopy(template_run))
        node=ET.SubElement(run,'{'+A+'}t')
        if line!=line.strip(): node.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        node.text=line
        end=previous.find('a:endParaRPr',NS) if previous is not None else None
        if end is not None: paragraph.append(deepcopy(end))

def patch_shape(shape,before,after,factor):
    changed={key for key in FIELDS if before.get(key)!=after.get(key)}
    if not changed: return False
    if 'name' in changed: shape.find('p:nvSpPr/p:cNvPr',NS).set('name',after['name'])
    if 'text' in changed: replace_text(shape,after['text'])
    if changed & {'x','y','w','h','rotation'}:
        xfrm=shape.find('p:spPr/a:xfrm',NS)
        for key,node,attr in [('x','off','x'),('y','off','y'),('w','ext','cx'),('h','ext','cy')]:
            if key in changed: xfrm.find('a:'+node,NS).set(attr,str(round(after[key]*factor)))
        if 'rotation' in changed: xfrm.set('rot',str(round(after['rotation']*60000)))
    for paragraph in shape.findall('p:txBody/a:p',NS):
        if 'align' in changed:
            ppr=paragraph.find('a:pPr',NS)
            if ppr is None:
                ppr=ET.Element('{'+A+'}pPr')
                paragraph.insert(0,ppr)
            ppr.set('algn',{'left':'l','center':'ctr','right':'r','justify':'just'}[after['align']])
        if changed & {'size','typeface','color','bold','italic'}:
            styles=[]
            for run in list(paragraph.findall('a:r',NS))+list(paragraph.findall('a:fld',NS)):
                rpr=run.find('a:rPr',NS)
                if rpr is None:
                    rpr=ET.Element('{'+A+'}rPr')
                    run.insert(0,rpr)
                styles.append(rpr)
            end=paragraph.find('a:endParaRPr',NS)
            if end is None: end=ET.SubElement(paragraph,'{'+A+'}endParaRPr')
            styles.append(end)
            for rpr in styles:
                for field,attribute in [('size','sz'),('bold','b'),('italic','i')]:
                    if field in changed: rpr.set(attribute,str(round(after[field]*100)) if field=='size' else '1' if after[field] else '0')
                if 'color' in changed:
                    for child in list(rpr):
                        if child.tag.rsplit('}',1)[-1] in ['noFill','solidFill','gradFill','blipFill','pattFill','grpFill']: rpr.remove(child)
                    fill=ET.Element('{'+A+'}solidFill')
                    ET.SubElement(fill,'{'+A+'}srgbClr',{'val':after['color'].lstrip('#').upper()})
                    # Fill precedes effect/font elements in CT_TextCharacterProperties.
                    at=1 if len(rpr) and rpr[0].tag=='{'+A+'}ln' else 0
                    rpr.insert(at,fill)
                if 'typeface' in changed:
                    for name in ['latin','ea','cs']:
                        font=rpr.find('a:'+name,NS)
                        if font is None:
                            font=ET.Element('{'+A+'}'+name)
                            order=['latin','ea','cs','sym','hlinkClick','hlinkMouseOver','rtl','extLst']
                            following=set(order[order.index(name)+1:])
                            at=next((i for i,c in enumerate(rpr) if c.tag.rsplit('}',1)[-1] in following),len(rpr))
                            rpr.insert(at,font)
                        font.set('typeface',after['typeface'])
    return True

def assemble(base,additional_path,out):
    data,infos,comment=read_package(base['path'])
    original={p['part']:p for p in base['original']['slides']}
    changes=[]
    factor=base['original']['width_emu']/960
    for page in base['resolved']:
        before={t['id']:t for t in original[page['part']]['texts']}
        after={t['id']:t for t in page['texts']}
        if before==after: continue
        root=ET.fromstring(data[page['part']])
        changed_ids=[]
        for shape,_ in native_shapes(root):
            sid=shape.find('p:nvSpPr/p:cNvPr',NS).get('id')
            if patch_shape(shape,before[sid],after[sid],factor): changed_ids.append(sid)
        if changed_ids:
            data[page['part']]=xml_bytes(root,data[page['part']])
            changes.append({'part':page['part'],'shape_ids':changed_ids})
    added=append_package(data,additional_path) if additional_path is not None else 0
    write_package(out,data,infos,comment)
    return {'preserved_base_slides':base['slide_count'],'appended_slides':added,'patched_shapes':changes}

def expected_text(base,appended):
    result=[]
    for number,page in enumerate(base['resolved'],1):
        result.append({'slide':number,'texts':[{'name':t['name'],'text':t['text']} for t in page['texts']]})
    for page in appended['slides']:
        result.append({'slide':len(result)+1,'texts':page['texts']})
    return {'slides':result}
