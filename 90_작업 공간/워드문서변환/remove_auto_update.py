"""Remove only the automatic field-update setting introduced by conversion."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import hashlib, json, os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
report_path=HERE/'검증/conversion_report.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
target=Path(report['output']);reference=Path(report['template'])
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns={'w':W}
sha=lambda data:hashlib.sha256(data).hexdigest()
before_sha=sha(target.read_bytes())
with ZipFile(target) as z,ZipFile(reference) as ref:
    old={n:z.read(n) for n in z.namelist()}
    settings=E.fromstring(old['word/settings.xml'])
    removed=[]
    for n in settings.findall('w:updateFields',ns):
        removed.append(dict(n.attrib));settings.remove(n)
    ref_settings=ref.read('word/settings.xml')
    if E.tostring(settings,method='c14n')==E.tostring(E.fromstring(ref_settings),method='c14n'):
        fixed=ref_settings
    else:
        fixed=E.tostring(settings,xml_declaration=True,encoding='UTF-8',standalone=True)
    temporary=target.with_name(target.stem+'.field-fix.tmp')
    with ZipFile(temporary,'w') as out:
        for entry in z.infolist():out.writestr(entry,fixed if entry.filename=='word/settings.xml' else old[entry.filename])
with ZipFile(temporary) as z:
    assert all(z.read(n)==data for n,data in old.items() if n!='word/settings.xml')
    assert not E.fromstring(z.read('word/settings.xml')).findall('w:updateFields',ns)
os.replace(temporary,target)
report['changed_parts']=[n for n in report['changed_parts'] if n!='word/settings.xml']
if fixed==ref_settings and 'word/settings.xml' not in report['preserved_parts']:
    report['preserved_parts'].append('word/settings.xml')
report['auto_field_update']=False
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
result={'output':str(target),'before_sha256':before_sha,'after_sha256':sha(target.read_bytes()),
        'removed_update_fields':removed,'only_changed_part':'word/settings.xml',
        'all_other_parts_identical':True,'settings_matches_reference':fixed==ref_settings,
        'reference_sha256':sha(reference.read_bytes())}
(HERE/'검증/field_fix_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
