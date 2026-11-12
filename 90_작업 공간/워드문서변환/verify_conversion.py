from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import argparse, hashlib, json, re

HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser()
ap.add_argument('--report-dir',type=Path,default=HERE/'검증')
args=ap.parse_args()
report_dir=args.report_dir.resolve()
report=json.loads((report_dir/'conversion_report.json').read_text(encoding='utf-8'))
pages=json.loads((report_dir/'pages.json').read_text(encoding='utf-8-sig'))
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W=NS['w']
qn=lambda s:'{'+W+'}'+s
text=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=NS))
strip=lambda s:re.sub(r'\*\*([^*]+)\*\*|`([^`]+)`',lambda m:m[1] or m[2],s)
assert hashlib.sha256(Path(report['source']).read_bytes()).hexdigest()==report['source_sha256']
assert hashlib.sha256(Path(report['template']).read_bytes()).hexdigest()==report['template_sha256']
with ZipFile(report['template']) as ref, ZipFile(report['output']) as z:
    for name in report['preserved_parts']: assert ref.read(name)==z.read(name),name
    for name in ref.namelist(): assert name in z.namelist(),name
    settings=E.fromstring(z.read('word/settings.xml'))
    assert not settings.xpath('//w:updateFields[@w:val="true" or @w:val="1"]',namespaces=NS),'Automatic field-update prompt can be triggered'
    for name in z.namelist():
        if name.endswith('.rels'):
            assert not any(n.get('TargetMode')=='External' for n in E.fromstring(z.read(name))),name
    doc=E.fromstring(z.read('word/document.xml'));old=E.fromstring(ref.read('word/document.xml'))
    field_commands=set()
    for part in z.namelist():
        if part.endswith('.xml'):
            fields=E.fromstring(z.read(part)).xpath('//w:instrText/text()|//w:fldSimple/@w:instr',namespaces=NS)
            field_commands.update(f.strip().split()[0].upper() for f in fields if f.strip())
    assert field_commands<={'TOC','PAGEREF','PAGE'},field_commands
    for xpath in ('//w:sectPr','//w:sdtPr'):
        assert [E.tostring(n) for n in doc.xpath(xpath,namespaces=NS)]==[E.tostring(n) for n in old.xpath(xpath,namespaces=NS)],xpath
    for name in ref.namelist():
        if name.endswith('.rels'):
            a=E.fromstring(ref.read(name));b=E.fromstring(z.read(name))
            assert all(any(dict(n.attrib)==dict(m.attrib) for m in b) for n in a),name
    oldnum=E.fromstring(ref.read('word/numbering.xml'));newnum=E.fromstring(z.read('word/numbering.xml'))
    for n in oldnum:
        if E.QName(n).localname in ('abstractNum','num'):
            idattr=qn('abstractNumId' if E.QName(n).localname=='abstractNum' else 'numId')
            match=[m for m in newnum if m.tag==n.tag and m.get(idattr)==n.get(idattr)]
            assert len(match)==1 and E.tostring(match[0])==E.tostring(n)
    body=doc.find('w:body',NS);children=list(body)
    start=next(i for i,n in enumerate(children) if n.tag==qn('p') and n.find('w:pPr/w:pStyle',NS) is not None and n.find('w:pPr/w:pStyle',NS).get(qn('val'))=='1')
    actual=[]
    for n in children[start:]:
        if n.tag==qn('sectPr'): continue
        if n.tag==qn('tbl'):
            actual.append(('table',[[text(c) for c in r.findall('w:tc',NS)] for r in n.findall('w:tr',NS)]))
        elif n.find('.//w:drawing',NS) is not None: actual.append(('image',None))
        elif text(n): actual.append(('text',text(n)))
    expected=[]
    for b in report['blocks']:
        if b['kind']=='table': expected.append(('table',[[strip(c) for c in r] for r in b['rows']]))
        elif b['kind']=='image': expected.append(('image',None))
        else: expected.append(('text',strip(b['text'])))
    assert actual==expected,'Body text/table order or content mismatch'
    for info in report['images']:
        assert hashlib.sha256(z.read(info['media'])).hexdigest()==info['sha256']
        iw,ih=info['pixels'];cx,cy=info['extent']
        assert abs(cx/cy-iw/ih)<1e-5
    bookmarks={n.get(qn('name')) for n in doc.xpath('//w:bookmarkStart',namespaces=NS)}
    for h in report['headings']: assert h['bookmark'] in bookmarks
    toc=body.find('w:sdt/w:sdtContent',NS)
    entries=[h for h in report['headings'] if h['level']<=2]
    toclinks=toc.findall('.//w:hyperlink',NS)
    assert len(entries)==len(toclinks)
    for h,link in zip(entries,toclinks):
        assert link.get(qn('anchor'))==h['bookmark']
        assert text(link)==h['source']+str(pages[h['bookmark']]),(h['source'],text(link),pages[h['bookmark']])
    body_text='\n'.join(text(n) for n in children)
    for unwanted in ('approval_status:','sources:','덜미 전자책 변환','무형문화유산 전승','초안 작성','조상연'):
        assert unwanted not in body_text,unwanted
    if '콘셉트 초안이며 승인 대기 상태임.' in Path(report['source']).read_text(encoding='utf-8-sig'):
        assert '콘셉트 초안이며 승인 대기 상태임.' in body_text
    result={'passed':True,'source_unchanged':True,'reference_unchanged':True,
        'body_blocks_compared':len(expected),'preserve_only_parts':len(report['preserved_parts']),
        'source_section_count':len(old.xpath('//w:sectPr',namespaces=NS)),
        'output_section_count':len(doc.xpath('//w:sectPr',namespaces=NS)),
        'headings':len(report['headings']),'toc_entries':len(entries),'images':len(report['images']),
        'body_tables':sum(b['kind']=='table' for b in report['blocks']),
        'output_sha256':hashlib.sha256(Path(report['output']).read_bytes()).hexdigest(),
        'auto_field_update':False,'external_relationships':0,'field_commands':sorted(field_commands)}
    (report_dir/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
