"""Reusable textless layouts; linguistic content remains native PPTX text."""
from copy import deepcopy
import math
import re
import sys
import unicodedata

LAYOUTS = {
    'hero': 'Left-side title and short copy; optional full-page textless artwork.',
    'bullets': 'One or more labeled lists; optional artwork on the right.',
    'columns': 'Two or three parallel groups for comparisons.',
    'steps': 'Two to five stages with optional values and descriptions.',
    'timeline': 'Two to five alternating events along a timeline.',
    'matrix': 'A compact table with native text in every cell.',
    'closing': 'A short completion/action list and a concluding takeaway.',
    'custom': 'Explicit text frames and positioned assets for precise diagrams.',
}
DEFAULT_FONT = 'Microsoft YaHei' if sys.platform == 'win32' else 'PingFang SC' if sys.platform == 'darwin' else 'Arial'

def string(value, context, required=True):
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f'{context} must be {"a nonempty" if required else "a"} string')
    return value

def items(value, context, minimum=0, maximum=100):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f'{context} must be a list with {minimum}..{maximum} items')
    return value

def rect(x,y,w,h,fill,stroke='none',radius=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'

def line(x1,y1,x2,y2,color,width=1):
    return f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="{width}" fill="none"/>'

def circle(x,y,r,fill):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'

class Page:
    def __init__(self, spec, theme, position, total):
        self.spec,self.theme,self.position,self.total = spec,theme,position,total
        self.texts,self.graphics,self.warnings = [],[],[]

    def text(self,name,value,x,y,w,h,size=16,color=None,bold=False,align='left'):
        value=string(value,f'Slide {self.spec["id"]} {name}')
        self.texts.append(dict(name=name,text=value,x=x,y=y,w=w,h=h,size=size,
                               typeface=self.theme['font'],color=color or self.theme['ink'],bold=bold,align=align))

    def header(self):
        self.text('title',self.spec['title'],48,34,864,74,29,self.theme['navy'],True)
        if self.spec.get('subtitle'):
            self.text('subtitle',self.spec['subtitle'],48,121,864,47,18,self.theme['blue'])

    def footer(self):
        if self.spec.get('page_number',True):
            self.text('page-number',f'{self.position:02} / {self.total:02}',844,509,68,22,11,self.theme['blue'],align='right')

    def svg(self):
        decor = self.spec.get('decoration',self.spec['layout'] != 'custom')
        if decor:
            self.graphics.append(line(48,501,912,501,self.theme['rule']))
            for x in range(790,923,22):
                self.graphics.append(line(x,16,x,80,self.theme['grid'],.8))
            for y in range(16,81,16):
                self.graphics.append(line(790,y,922,y,self.theme['grid'],.8))
        return '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">'+''.join(self.graphics)+'</svg>'

def hero(p):
    s=p.spec
    p.text('title',s['title'],48,79,442,95,50,p.theme['navy'],True)
    if s.get('subtitle'): p.text('subtitle',s['subtitle'],50,187,442,81,24,p.theme['navy'],True)
    if s.get('eyebrow'): p.text('eyebrow',s['eyebrow'],50,290,430,35,17,p.theme['blue'],True)
    for i,value in enumerate(items(s.get('bullets',[]),'hero.bullets',0,3)):
        p.text(f'bullet-{i+1}',value,50,342+43*i,432,35,15)
    if s.get('takeaway'): p.text('takeaway',s['takeaway'],50,467,450,31,17,p.theme['blue'],True)
    p.graphics.append(line(50,273,432,273,p.theme['rule'],2))

def bullets(p):
    p.header()
    sections=p.spec.get('sections')
    if sections is None: sections=[{'items':p.spec.get('bullets',[])}]
    sections=items(sections,'bullets.sections',1,3)
    bands=0
    for section in sections:
        if not isinstance(section,dict): raise ValueError('Each section must be an object')
        bands+=len(items(section.get('items',[]),'section.items',1,8))+(1.35 if section.get('heading') else 0)+.35
    step=min(39,300/bands)
    y=177 if p.spec.get('subtitle') else 148
    width=410 if p.spec.get('artwork') else 820
    for i,section in enumerate(sections):
        if section.get('heading'):
            p.text(f'section-{i+1}',section['heading'],48,y,width,step*1.25,21,p.theme['blue'],True)
            y+=step*1.35
        for j,value in enumerate(section['items']):
            p.text(f'section-{i+1}-item-{j+1}',value,48,y,width,step,15.5)
            y+=step
        y+=step*.35
    if p.spec.get('takeaway'): p.text('takeaway',p.spec['takeaway'],48,468,840,31,16,p.theme['blue'],True)

def columns(p):
    p.header()
    groups=items(p.spec.get('columns'),'columns',2,3)
    width=(864-32*(len(groups)-1))/len(groups)
    for i,group in enumerate(groups):
        x=48+i*(width+32)
        p.text(f'column-{i+1}-heading',group.get('heading'),x,187,width,45,22,p.theme['blue'],True)
        p.graphics.append(line(x,240,x+width,240,p.theme['rule'],2))
        values=items(group.get('items'),'column.items',1,6)
        step=min(49,218/len(values))
        for j,value in enumerate(values):
            p.text(f'column-{i+1}-item-{j+1}',value,x+15,260+j*step,width-15,step,15)
            p.graphics.append(circle(x+3,269+j*step,3,p.theme['blue']))

def steps(p):
    p.header()
    stages=items(p.spec.get('steps'),'steps',2,5)
    gap=24
    width=(864-gap*(len(stages)-1))/len(stages)
    centers=[48+i*(width+gap)+width/2 for i in range(len(stages))]
    p.graphics.append(line(centers[0],283,centers[-1],283,p.theme['rule'],3))
    for i,(stage,cx) in enumerate(zip(stages,centers)):
        x=cx-width/2
        p.graphics.extend([circle(cx,234,40,p.theme['ice']),circle(cx,283,5,p.theme['blue'])])
        p.text(f'stage-{i+1}-number',str(i+1),cx-30,212,60,45,24,p.theme['blue'],True,'center')
        if stage.get('value'):
            p.text(f'stage-{i+1}-value',str(stage['value']),x,312,width,58,29,p.theme['blue'],True,'center')
        p.text(f'stage-{i+1}-title',stage.get('title'),x,380 if stage.get('value') else 325,width,42,20,p.theme['navy'],True,'center')
        if stage.get('description'):
            p.text(f'stage-{i+1}-description',stage['description'],x,425 if stage.get('value') else 379,width,49,13.5,align='center')
    if p.spec.get('takeaway'): p.text('takeaway',p.spec['takeaway'],48,474,850,27,14,p.theme['blue'],True)

def timeline(p):
    p.header()
    events=items(p.spec.get('events'),'events',2,5)
    width=min(180,820/len(events))
    centers=[100+i*760/(len(events)-1) for i in range(len(events))]
    p.graphics.append(line(centers[0],309,centers[-1],309,p.theme['rule'],3))
    for i,(event,cx) in enumerate(zip(events,centers)):
        x=max(48,min(912-width,cx-width/2))
        top=184 if i%2==0 else 338
        p.graphics.extend([circle(cx,309,7,p.theme['blue']),line(cx,275 if i%2==0 else 322,cx,302 if i%2==0 else 331,p.theme['rule'],2)])
        if event.get('value'): p.text(f'event-{i+1}-value',str(event['value']),x,top,width,31,17,p.theme['blue'],True,'center')
        p.text(f'event-{i+1}-title',event.get('title'),x,top+34,width,34,17,p.theme['navy'],True,'center')
        if event.get('description'): p.text(f'event-{i+1}-description',event['description'],x,top+72,width,56,12.5,align='center')

def matrix(p):
    p.header()
    headers=items(p.spec.get('headers'),'headers',2,6)
    rows=items(p.spec.get('rows'),'rows',1,7)
    width=864/len(headers)
    height=min(55,252/len(rows))
    p.graphics.append(rect(48,180,864,48,p.theme['ice']))
    for col,value in enumerate(headers):
        p.text(f'header-{col+1}',value,56+col*width,191,width-16,31,14,p.theme['blue'],True)
    for r,row in enumerate(rows):
        items(row,f'row {r+1}',len(headers),len(headers))
        y=228+r*height
        p.graphics.append(rect(48,y,864,height,p.theme['background'] if r%2 else p.theme['stripe']))
        p.graphics.append(line(48,y+height,912,y+height,p.theme['rule']))
        for col,value in enumerate(row):
            if not isinstance(value,(str,int,float)) or isinstance(value,bool): raise ValueError('Table values must be strings or numbers')
            p.text(f'cell-{r+1}-{col+1}',str(value),56+col*width,y+8,width-16,height-10,12.5)

def closing(p):
    p.header()
    entries=items(p.spec.get('items'),'closing.items',1,4)
    for i,entry in enumerate(entries):
        y=155+i*70
        p.graphics.append(circle(66,y+17,14,p.theme['ice']))
        p.graphics.append(f'<path d="M59 {y+17} L64 {y+22} L73 {y+12}" stroke="{p.theme["blue"]}" stroke-width="2.4" fill="none"/>')
        p.text(f'item-{i+1}-heading',entry.get('heading'),94,y,80,37,19,p.theme['navy'],True)
        p.text(f'item-{i+1}-body',entry.get('body'),184,y+1,325 if p.spec.get('artwork') else 700,51,14.5)
    if p.spec.get('takeaway'): p.text('takeaway',p.spec['takeaway'],48,463,530,39,23,p.theme['blue'],True)

def custom(p):
    for i,item in enumerate(items(p.spec.get('texts'),'custom.texts',1,300)):
        if not isinstance(item,dict): raise ValueError('Custom text frames must be objects')
        frame=deepcopy(item)
        string(frame.get('text'),'custom text')
        frame.setdefault('name',f'text-{i+1}')
        frame.setdefault('typeface',p.theme['font'])
        frame.setdefault('color',p.theme['ink'])
        p.texts.append(frame)

def compile_deck(source,base,*,allow_empty=False,page_offset=0,total_pages=None):
    if not isinstance(source,dict) or source.get('schema_version') != 1:
        raise ValueError('deck.json requires schema_version: 1')
    string(source.get('title'),'deck title')
    theme=dict(font=DEFAULT_FONT,background='#FFFFFF',navy='#0B2148',blue='#166BFF',ink='#35506F',ice='#EAF4FF',rule='#DCE9F8',grid='#F0F5FC',stripe='#F8FBFF')
    overrides=source.get('theme',{})
    if not isinstance(overrides,dict): raise ValueError('theme must be an object')
    theme.update(overrides)
    string(theme['font'],'theme.font')
    for key in ['background','navy','blue','ink','ice','rule','grid','stripe']:
        if not isinstance(theme[key],str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}',theme[key]):
            raise ValueError(f'theme.{key} must be #RRGGBB')
    asset_specs=source.get('assets',{})
    if not isinstance(asset_specs,dict): raise ValueError('assets must be an object')
    assets={}
    for name,asset in asset_specs.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',name): raise ValueError(f'Invalid asset ID: {name}')
        if not isinstance(asset,dict): raise ValueError(f'Asset {name} must be an object')
        file=string(asset.get('file'),f'Asset {name}.file')
        assets[name]={**asset,'path':(base/file).resolve()}
        if asset.get('prompt') is not None: string(asset['prompt'],f'Asset {name}.prompt')
    pages=[]
    slide_specs=items(source.get('slides'),'slides',0 if allow_empty else 1,500)
    ids=set()
    for pos,original in enumerate(slide_specs,1):
        if not isinstance(original,dict): raise ValueError(f'Slide {pos} must be an object')
        spec={**original,'id':original.get('id',pos)}
        if type(spec['id']) is not int or spec['id']<1 or spec['id'] in ids:
            raise ValueError(f'Slide {pos} needs a unique positive integer id')
        ids.add(spec['id'])
        if spec.get('layout') not in LAYOUTS: raise ValueError(f'Slide {pos}: unknown layout {spec.get("layout")}')
        string(spec.get('title'),f'Slide {pos}.title')
        page=Page(spec,theme,pos+page_offset,total_pages or len(slide_specs)+page_offset)
        globals()[spec['layout']](page)
        page.footer()
        visuals=[]
        if spec.get('artwork'): visuals.append({'asset':spec['artwork'],'position':[0,0,960,540]})
        visuals+=items(spec.get('visuals',[]),'visuals',0,100)
        for visual in visuals:
            if not isinstance(visual,dict) or visual.get('asset') not in assets:
                raise ValueError(f'Slide {pos}: unknown visual asset {visual}')
            bounds=visual.get('position',[0,0,960,540])
            if not isinstance(bounds,list) or len(bounds)!=4 or any(type(n) not in [int,float] or not math.isfinite(n) for n in bounds) or bounds[2]<=0 or bounds[3]<=0:
                raise ValueError(f'Slide {pos}: visual position requires finite x/y and positive w/h')
            visual['position']=bounds
        for frame in page.texts:
            try:
                x,y,w,h,size=[float(frame[k]) for k in ['x','y','w','h','size']]
            except (KeyError,TypeError,ValueError) as error:
                raise ValueError(f'Slide {pos}: invalid text frame {frame.get("name")}') from error
            if not all(math.isfinite(n) for n in [x,y,w,h,size]) or min(w,h,size)<=0 or x<0 or y<0 or x+w>961 or y+h>541:
                raise ValueError(f'Slide {pos}: text frame outside canvas or invalid: {frame.get("name")}')
            if frame.get('fill') or frame.get('line'):
                raise ValueError('Project text frames must remain transparent without outlines')
            units=sum(1 if unicodedata.east_asian_width(c) in 'WF' else .55 for c in frame['text'])
            estimate=math.ceil(units*size/0.75/w)*size/0.75*1.15
            if estimate>h+3:
                page.warnings.append(f'Slide {spec["id"]} {frame["name"]}: wording may need more room; inspect the rendered slide')
        pages.append({'id':spec['id'],'title':spec['title'],'layout':spec['layout'],'texts':page.texts,'svg':page.svg(),'visuals':visuals,'spec':spec,'warnings':page.warnings})
    return {'theme':theme,'assets':assets,'pages':pages,
            'text_source':{'background':theme['background'],'typeface':theme['font'],'slides':[{'slide':p['id'],'texts':p['texts']} for p in pages]},
            'warnings':[w for p in pages for w in p['warnings']]}
