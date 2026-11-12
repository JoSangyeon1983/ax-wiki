from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import hashlib, json

HERE = Path(__file__).resolve().parent
REF = next(HERE.glob('*.docx'))
OUT = HERE / '검증'
OUT.mkdir(exist_ok=True)
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def xml(n): return E.tostring(n, encoding='unicode') if n is not None else None
def text(n): return ''.join(n.xpath('.//w:t/text()', namespaces=NS))
with ZipFile(REF) as z:
    root = E.fromstring(z.read('word/document.xml'))
    styles = E.fromstring(z.read('word/styles.xml'))
    info = {'reference':str(REF), 'sha256':hashlib.sha256(REF.read_bytes()).hexdigest(),
            'parts': {n:{'size':len(z.read(n)), 'sha256':hashlib.sha256(z.read(n)).hexdigest()}
                      for n in z.namelist()}, 'body':[], 'styles':[], 'other_parts':{}}
    for i,n in enumerate(root.find('w:body', NS)):
        item={'index':i,'tag':E.QName(n).localname,'text':text(n),'xml':xml(n)}
        info['body'].append(item)
        print(i, item['tag'], repr(item['text']))
        if item['tag']=='p':
            print('   ', xml(n.find('w:pPr',NS)))
            for r in n.findall('w:r',NS):
                if text(r): print('   RUN',repr(text(r)),xml(r.find('w:rPr',NS)))
    for n in styles.findall('w:style',NS):
        name=n.find('w:name',NS)
        info['styles'].append({'id':n.get('{'+NS['w']+'}styleId'),
            'name':name.get('{'+NS['w']+'}val') if name is not None else None, 'xml':xml(n)})
    for n in z.namelist():
        if n.startswith(('word/footer','word/header','docProps/')) or n in ('word/numbering.xml','word/settings.xml','word/_rels/document.xml.rels'):
            info['other_parts'][n]=z.read(n).decode('utf-8')
    (OUT/'reference_inventory.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    for s in info['styles']:
        if s['id'] in ('Normal','Title','1','2','3','4','5','6','TOC1','TOC2','TOC3') or any(x in (s['name'] or '') for x in ('제목','본문','목차')):
            print('STYLE',s['id'],s['name'],s['xml'])
    print('FEATURES', {k:len(root.xpath(v,namespaces=NS)) for k,v in {'sdt':'//w:sdt','fields':'//w:instrText','drawings':'//w:drawing','textboxes':'//w:txbxContent','tables':'//w:tbl','sections':'//w:sectPr'}.items()})
