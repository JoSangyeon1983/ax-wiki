from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import hashlib, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
paths=[next(HERE.glob('*.docx')),ROOT/'08_산출물/워드 문서 변환/Cave Action 콘셉트 기획서.docx']
report=[]
for path in paths:
    item={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fields':{},'external_relationships':[],'update_fields':[]}
    with ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith('.xml'):
                root=E.fromstring(z.read(name))
                fields=root.xpath('//w:instrText/text()|//w:fldSimple/@w:instr',namespaces=NS)
                if fields:item['fields'][name]=fields
                item['update_fields']+=root.xpath('//w:updateFields/@w:val',namespaces=NS)
            elif name.endswith('.rels'):
                for n in E.fromstring(z.read(name)):
                    if n.get('TargetMode')=='External':item['external_relationships'].append({'part':name,**dict(n.attrib)})
    report.append(item)
(HERE/'검증/field_open_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
