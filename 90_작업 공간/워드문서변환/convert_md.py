"""Test converter for the retained CELLBIG proposal template.

Patch a copy of the package and preserve every unrelated ZIP part byte for byte.
No source MD text or reference DOCX is modified.
"""
from __future__ import annotations
import argparse, copy, hashlib, html, json, re, sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from PIL import Image

SKILL=Path('C:/Users/cellbig/.codex/plugins/cache/openai-primary-runtime/documents/26.1104.12130/skills/documents')
sys.path.insert(0,str(SKILL/'scripts'))
from docx_ooxml_patch import _qn

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
PIC='http://schemas.openxmlformats.org/drawingml/2006/picture'
PR='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'w':W,'r':R,'wp':WP,'a':A,'pic':PIC}
def q(t): return _qn('w',t)
def node(t,attrs=None):
    n=E.Element(q(t))
    for k,v in (attrs or {}).items(): n.set(q(k),str(v))
    return n
def child(p,t,attrs=None):
    n=node(t,attrs);p.append(n);return n
def xml(n): return E.tostring(n,xml_declaration=True,encoding='UTF-8',standalone=True)
def plain(n): return ''.join(n.xpath('.//w:t/text()',namespaces=NS))
def replace_text(n,value):
    ts=n.xpath('.//w:t',namespaces=NS)
    if not ts: raise ValueError('Expected a retained text slot')
    ts[0].text=value
    ts[0].set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    for t in ts[1:]: t.text=''
def put_run(p,text,bold=False):
    r=child(p,'r')
    if bold: child(child(r,'rPr'),'b')
    if text=='\t': child(r,'tab')
    else:
        t=child(r,'t');t.text=text
        t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    return r
def inlines(p,text):
    # Supported inline forms are deliberately bounded and fail on leftovers.
    for part in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)',text):
        if not part: continue
        if part.startswith('**') and part.endswith('**'): put_run(p,part[2:-2],True)
        elif part.startswith('`') and part.endswith('`'): put_run(p,part[1:-1])
        else:
            if re.search(r'!?\[[^\]]+\]\(|<[^>]+>|\*\*|`',part):
                raise ValueError('Unsupported inline syntax: '+part)
            put_run(p,html.unescape(part))
def para(text='',style=None,keep=False):
    p=node('p');pr=child(p,'pPr')
    if style: child(pr,'pStyle',{'val':style})
    if keep: child(pr,'keepNext')
    if text: inlines(p,text)
    return p
def field(p,code,cached):
    child(child(p,'r'),'fldChar',{'fldCharType':'begin'})
    t=child(child(p,'r'),'instrText');t.text=code;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    child(child(p,'r'),'fldChar',{'fldCharType':'separate'})
    put_run(p,str(cached))
    child(child(p,'r'),'fldChar',{'fldCharType':'end'})

def parse_md(path):
    content=path.read_text(encoding='utf-8-sig')
    content=re.sub(r'\A---\s*\n.*?\n---\s*\n','',content,count=1,flags=re.S)
    lines=content.splitlines();blocks=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1;continue
        m=re.fullmatch(r'(#{1,3})\s+(.+)',line)
        if m:
            level=len(m[1]);src=m[2]
            title=re.sub(r'^\d+(?:\.\d+)*\s+','',src)
            blocks.append({'kind':'heading','level':level,'text':title,'source':src});i+=1;continue
        if line.startswith('<img '):
            m=re.search(r'src="([^"]+)"',line);a=re.search(r'alt="([^"]*)"',line)
            if not m: raise ValueError('img src missing')
            image=(path.parent/html.unescape(m[1])).resolve()
            if not image.is_relative_to(ROOT): raise ValueError('Image outside wiki')
            if not image.is_file(): raise FileNotFoundError(image)
            blocks.append({'kind':'image','path':str(image),'alt':html.unescape(a[1]) if a else image.stem});i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                rows.append([x.strip() for x in lines[i].strip().strip('|').split('|')]);i+=1
            if len(rows)<2 or not all(re.fullmatch(r':?-+:?',x) for x in rows[1]): raise ValueError('Invalid Markdown table')
            if len({len(r) for r in rows})!=1: raise ValueError('Unequal table row lengths')
            blocks.append({'kind':'table','rows':[rows[0]]+rows[2:]});continue
        m=re.fullmatch(r'(- |\d+\. )(.+)',line)
        if m:
            kind='bullet' if m[1]=='- ' else 'ordered'
            blocks.append({'kind':kind,'text':m[2],'number':int(m[1][:-2]) if kind=='ordered' else None});i+=1;continue
        if re.match(r'\s|[#<>`]|!\[',line): raise ValueError('Unsupported block: '+line)
        blocks.append({'kind':'paragraph','text':line});i+=1
    return blocks

def build(args):
    ref=args.template.resolve();source=args.source.resolve();out=args.output.resolve()
    if out==ref or out==source: raise ValueError('Output must be separate')
    if out.exists() and not args.overwrite: raise FileExistsError('Existing output requires --overwrite after checking user edits')
    inv=json.loads((HERE/'검증/reference_inventory.json').read_text(encoding='utf-8'))
    if hashlib.sha256(ref.read_bytes()).hexdigest()!=inv['sha256']: raise ValueError('Template changed; repeat inspection')
    blocks=parse_md(source)
    report_dir=args.report_dir.resolve()
    report_dir.mkdir(parents=True,exist_ok=True)
    suffix='콘셉트 기획서'
    cover_title=args.cover_title or (source.stem[:-len(suffix)].strip() if source.stem.endswith(suffix) else source.stem)
    cover_subtitle=args.cover_subtitle or (suffix if source.stem.endswith(suffix) else '\u00a0')
    pages=json.loads(args.pages_json.read_text(encoding='utf-8-sig')) if args.pages_json else {}
    with ZipFile(ref) as zin:
        original={n:zin.read(n) for n in zin.namelist()}
        changed={};additions={}
        doc=E.fromstring(original['word/document.xml']);body=doc.find('w:body',NS)
        # Exact source structures, all retained outside named edit slots.
        old_sections=[E.tostring(n) for n in doc.xpath('//w:sectPr',namespaces=NS)]
        old_sdts=[E.tostring(n) for n in doc.xpath('//w:sdtPr',namespaces=NS)]
        tables=body.findall('w:tbl',NS)
        cover_sdts=tables[0].xpath('.//w:sdt',namespaces=NS)
        replace_text(cover_sdts[1],cover_title)
        replace_text(cover_sdts[2],cover_subtitle)
        # A visible-empty NBSP avoids Word replacing an empty bound slot with
        # its blue author/date placeholder when opening the document.
        for s in tables[1].xpath('.//w:sdt',namespaces=NS): replace_text(s,'\u00a0')
        version=tables[2]
        for c in version.findall('w:tr',NS)[1].findall('w:tc',NS): replace_text(c,'')
        # Source's front matter remains present but its example data is not adopted.
        core=E.fromstring(original['docProps/core.xml'])
        for n in core:
            name=E.QName(n).localname
            if name=='title': n.text=cover_title
            elif name=='subject': n.text=cover_subtitle
            elif name=='creator': n.text='\u00a0'
            elif name in ('lastModifiedBy','keywords','description'): n.text=''
        changed['docProps/core.xml']=xml(core)
        cp=E.fromstring(original['customXml/item1.xml'])
        for n in cp:
            if E.QName(n).localname=='PublishDate': n.text='\u00a0'
        changed['customXml/item1.xml']=xml(cp)
        # Retain every style/abstract numbering definition. Add only list instances.
        numbering=E.fromstring(original['word/numbering.xml'])
        next_num=max(int(n.get(q('numId'))) for n in numbering.findall('w:num',NS))+1
        bullet_id=24
        def new_ordered_list():
            nonlocal next_num
            num=node('num',{'numId':next_num});child(num,'abstractNumId',{'val':'25'})
            override=child(num,'lvlOverride',{'ilvl':'0'});child(override,'startOverride',{'val':'1'})
            cleanup=numbering.find('w:numIdMacAtCleanup',NS)
            if cleanup is not None: cleanup.addprevious(num)
            else: numbering.append(num)
            next_num+=1;return next_num-1
        rels=E.fromstring(original['word/_rels/document.xml.rels'])
        rid=max(int(n.get('Id')[3:]) for n in rels if n.get('Id','').startswith('rId'))+1
        headings=[];image_meta=[];output_blocks=[];bookmark=1000;drawing=1000;ordered_id=None
        for index,b in enumerate(blocks):
            kind=b['kind']
            if kind!='ordered': ordered_id=None
            if kind=='heading':
                p=para(b['text'],str(b['level']))
                name=f'_CaveHeading{len(headings)+1:03}'
                p.insert(1,node('bookmarkStart',{'id':bookmark,'name':name}))
                p.append(node('bookmarkEnd',{'id':bookmark}));bookmark+=1
                headings.append({**b,'bookmark':name})
            elif kind in ('bullet','ordered'):
                p=para(b['text']);pr=p.find('w:pPr',NS)
                child(pr,'keepLines')
                # Keep short lists with their heading rather than splitting a
                # small procedure or leaving a single bullet on the next page.
                first=index
                while first>0 and blocks[first-1]['kind']==kind: first-=1
                last=index
                while last+1<len(blocks) and blocks[last+1]['kind']==kind: last+=1
                if last-first<4 and sum(len(v['text']) for v in blocks[first:last+1])<=250 and index<last:
                    pr.insert(0,node('keepNext'))
                np=child(pr,'numPr');child(np,'ilvl',{'val':'0'})
                if kind=='ordered' and (ordered_id is None or b['number']==1): ordered_id=new_ordered_list()
                child(np,'numId',{'val':ordered_id if kind=='ordered' else bullet_id})
            elif kind=='paragraph': p=para(b['text'])
            elif kind=='table':
                p=copy.deepcopy(version)
                for tr in list(p.findall('w:tr',NS)): p.remove(tr)
                cols=len(b['rows'][0]);width=9746
                fractions=[.18,.41,.41] if cols==3 else [.38,.62] if cols==2 else [1/cols]*cols
                widths=[round(width*f) for f in fractions];widths[-1]=width-sum(widths[:-1])
                tpr=p.find('w:tblPr',NS);tpr.find('w:tblW',NS).set(q('w'),str(width))
                child(tpr,'tblLayout',{'type':'fixed'})
                margins=child(tpr,'tblCellMar')
                for side,w in [('top',70),('bottom',70),('left',115),('right',115)]: child(margins,side,{'w':w,'type':'dxa'})
                grid=p.find('w:tblGrid',NS)
                for c in list(grid): grid.remove(c)
                for w in widths: child(grid,'gridCol',{'w':w})
                samples=version.findall('w:tr',NS)
                for ri,row in enumerate(b['rows']):
                    tr=node('tr');trpr=child(tr,'trPr');child(trpr,'cantSplit')
                    if ri==0: child(trpr,'tblHeader')
                    for ci,value in enumerate(row):
                        sample=samples[0 if ri==0 else 1].findall('w:tc',NS)[min(ci,4)]
                        tc=node('tc');tcpr=copy.deepcopy(sample.find('w:tcPr',NS))
                        tcpr.find('w:tcW',NS).set(q('w'),str(widths[ci]));tc.append(tcpr)
                        cp=para(value);pr=cp.find('w:pPr',NS)
                        if ri==0: child(pr,'jc',{'val':'center'});child(pr,'keepNext')
                        child(pr,'spacing',{'after':'0','line':'240','lineRule':'auto'})
                        tc.append(cp);tr.append(tc)
                    p.append(tr)
                # A trailing spacer is required for separation from following body text.
            elif kind=='image':
                image_path=Path(b['path']);data=image_path.read_bytes()
                iw,ih=Image.open(image_path).size
                cx=round(9746/1440*914400);cy=round(cx*ih/iw)
                # Inline media remains within the source's usable page rectangle.
                maxcy=round(7.5*914400)
                if cy>maxcy: cx=round(cx*maxcy/cy);cy=maxcy
                media=f'word/media/cave_action_{len(image_meta)+1}.png'
                additions[media]=data
                r=E.SubElement(rels,'{'+PR+'}Relationship',Id=f'rId{rid}',Type=R+'/image',Target=media[5:])
                p=para();child(p.find('w:pPr',NS),'jc',{'val':'center'})
                drawing_node=child(child(p,'r'),'drawing')
                inline=E.SubElement(drawing_node,'{'+WP+'}inline',distT='0',distB='0',distL='0',distR='0')
                E.SubElement(inline,'{'+WP+'}extent',cx=str(cx),cy=str(cy))
                E.SubElement(inline,'{'+WP+'}docPr',id=str(drawing),name=image_path.name,descr=b['alt'])
                frame=E.SubElement(inline,'{'+WP+'}cNvGraphicFramePr')
                E.SubElement(frame,'{'+A+'}graphicFrameLocks',noChangeAspect='1')
                graphic=E.SubElement(inline,'{'+A+'}graphic');gd=E.SubElement(graphic,'{'+A+'}graphicData',uri=PIC)
                pic=E.SubElement(gd,'{'+PIC+'}pic');nv=E.SubElement(pic,'{'+PIC+'}nvPicPr')
                E.SubElement(nv,'{'+PIC+'}cNvPr',id='0',name=image_path.name);E.SubElement(nv,'{'+PIC+'}cNvPicPr')
                fill=E.SubElement(pic,'{'+PIC+'}blipFill');E.SubElement(fill,'{'+A+'}blip',{'{'+R+'}embed':f'rId{rid}'})
                stretch=E.SubElement(fill,'{'+A+'}stretch');E.SubElement(stretch,'{'+A+'}fillRect')
                sp=E.SubElement(pic,'{'+PIC+'}spPr');xf=E.SubElement(sp,'{'+A+'}xfrm')
                E.SubElement(xf,'{'+A+'}off',x='0',y='0');E.SubElement(xf,'{'+A+'}ext',cx=str(cx),cy=str(cy))
                geom=E.SubElement(sp,'{'+A+'}prstGeom',prst='rect');E.SubElement(geom,'{'+A+'}avLst')
                image_meta.append({'path':str(image_path.relative_to(ROOT)),'media':media,'sha256':hashlib.sha256(data).hexdigest(),'pixels':[iw,ih],'extent':[cx,cy]})
                rid+=1;drawing+=1
            else: raise ValueError(kind)
            output_blocks.append(p)
            if kind=='table':
                spacer=para();child(spacer.find('w:pPr',NS),'spacing',{'after':'100','line':'80','lineRule':'exact'})
                output_blocks.append(spacer)
        # Extend source body slot while preserving the final section and all page furniture.
        source_heading=body.xpath('./w:p[w:pPr/w:pStyle[@w:val="1"]]',namespaces=NS)[0]
        position=body.index(source_heading);body.remove(source_heading)
        for p in output_blocks: body.insert(position,p);position+=1
        # Reuse the existing TOC content control, title, tab geometry and section break.
        toc=body.find('w:sdt',NS);content=toc.find('w:sdtContent',NS)
        toc_paras=content.findall('w:p',NS)
        title=toc_paras[0];boundary=toc_paras[-1]
        proto=toc_paras[1];basepr=copy.deepcopy(proto.find('w:pPr',NS))
        toc_style2='11'
        styles=E.fromstring(original['word/styles.xml'])
        for s in styles.findall('w:style',NS):
            if s.find('w:name',NS).get(q('val')).lower()=='toc 2': toc_style2=s.get(q('styleId'))
        for n in list(content):
            if n is not title and n is not boundary: content.remove(n)
        entries=[h for h in headings if h['level']<=2]
        for i,h in enumerate(entries):
            p=node('p');pr=copy.deepcopy(basepr);p.append(pr)
            pr.find('w:pStyle',NS).set(q('val'),'11' if h['level']==1 else toc_style2)
            if h['level']==2: child(pr,'ind',{'left':'425'})
            if i==0:
                child(child(p,'r'),'fldChar',{'fldCharType':'begin'})
                ins=child(child(p,'r'),'instrText');ins.text=' TOC \\o "2-2" \\h \\z \\t "제목 1,1" '
                ins.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                child(child(p,'r'),'fldChar',{'fldCharType':'separate'})
            link=E.SubElement(p,q('hyperlink'),{q('anchor'):h['bookmark'],q('history'):'1'})
            put_run(link,h['source']);put_run(link,'\t')
            field(link,f' PAGEREF {h["bookmark"]} \\h ',pages.get(h['bookmark'],1))
            if i==len(entries)-1: child(child(p,'r'),'fldChar',{'fldCharType':'end'})
            boundary.addprevious(p)
        assert old_sections==[E.tostring(n) for n in doc.xpath('//w:sectPr',namespaces=NS)]
        assert old_sdts==[E.tostring(n) for n in doc.xpath('//w:sdtPr',namespaces=NS)]
        changed['word/document.xml']=xml(doc)
        changed['word/_rels/document.xml.rels']=xml(rels)
        changed['word/numbering.xml']=xml(numbering)
        ct=E.fromstring(original['[Content_Types].xml'])
        if not any(n.get('Extension')=='png' for n in ct):
            E.SubElement(ct,'{'+CT+'}Default',Extension='png',ContentType='image/png')
            changed['[Content_Types].xml']=xml(ct)
        out.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(out,'w',ZIP_DEFLATED) as zout:
            for info in zin.infolist(): zout.writestr(info,changed.get(info.filename,original[info.filename]))
            for name,data in additions.items(): zout.writestr(name,data)
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'template':str(ref),'template_sha256':inv['sha256'],'output':str(out),
        'frontmatter_included':False,'counts':{k:sum(b['kind']==k for b in blocks) for k in sorted({b['kind'] for b in blocks})},
        'headings':headings,'images':image_meta,'changed_parts':list(changed),'added_parts':list(additions),
        'preserved_parts':[n for n in original if n not in changed],'blocks':blocks,'page_cache_updated':bool(pages)}
    (report_dir/'conversion_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('output','counts','page_cache_updated')},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--template',type=Path,default=next(HERE.glob('*.docx')))
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--pages-json',type=Path)
    ap.add_argument('--report-dir',type=Path,default=HERE/'검증')
    ap.add_argument('--cover-title')
    ap.add_argument('--cover-subtitle')
    ap.add_argument('--overwrite',action='store_true')
    build(ap.parse_args())
