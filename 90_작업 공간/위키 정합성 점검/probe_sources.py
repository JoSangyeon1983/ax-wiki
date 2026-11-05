from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT.parent / '00_KOCCA_AX_Wiki/assets'
ns = {'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hh':'http://www.hancom.co.kr/hwpml/2011/head'}
records=[]
for n in [3,4]:
    with zipfile.ZipFile(OLD / f'{n}.hwpx') as z:
        tree=ET.fromstring(z.read('Contents/section0.xml'))
        for i,t in enumerate(tree.findall('.//hp:tbl',ns),1):
            rows=[]
            for row in t.findall('hp:tr',ns):
                cells=[]
                for cell in row.findall('hp:tc',ns):
                    text=''.join(x.text or '' for x in cell.findall('.//hp:t',ns)).strip()
                    addr=cell.find('hp:cellAddr',ns)
                    cells.append({'text':text,'border':cell.attrib.get('borderFillIDRef'),'address':addr.attrib if addr is not None else {}})
                rows.append(cells)
            if n==3 and i>=5:
                print(json.dumps({'source':3,'table':i,'monthly_cells':sum(len(r)-1 for r in rows[2:]),'rows':len(rows)-2},ensure_ascii=False))
            records.append({'source':n,'table':i,'rows':rows})
        if n==3:
            header=ET.fromstring(z.read('Contents/header.xml'))
            borderfills=[{'id':el.attrib.get('id'),'xml':ET.tostring(el,encoding='unicode')} for el in header.findall('.//hh:borderFill',ns)]
            print(json.dumps([b for b in borderfills if b['id'] in {'7','10','18','20'}],ensure_ascii=False))
(Path(__file__).parent / 'source_tables.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
