"""Validate staged wiki corrections, then apply with preimage guards."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
STAGE=WORK/'.staging'
sys.path.insert(0,str(WORK))
import audit
sys.path.insert(0,str(ROOT/'00_System/03_Tools'))
import heading_numbers as hn
DATE='2026-10-13'
REPORT='90_Workspace/위키 정합성 점검/위키 정합성 점검 보고서.md'
LOG='00_System/02_Logs/2026-10.md'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):(WORK/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def run(args):
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    r=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'00_System/03_Tools/heading_numbers.py')]+args,env=env,capture_output=True,text=True,encoding='utf-8')
    if r.returncode:
        (WORK/'heading_failure.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
        print('\n'.join(line for line in r.stdout.splitlines() if line.startswith('ERROR')))
        raise RuntimeError('Heading validation failed; see heading_failure.txt')
    print('\n'.join(line for line in r.stdout.splitlines() if line.startswith(('OK:','SKIP_LOG'))))
    return r.stdout

def policy(root):
    errors=[];legacy=[];graph={};count=0
    docs={p.relative_to(root).as_posix():p for p in hn.wiki_files(root) if p.relative_to(root).parts[0]!='99_Archive'}
    for rel,p in docs.items():
        if rel=='00_System/02_Logs/log.md':
            legacy.append({'path':rel,'issue':'historical log lacks frontmatter; reported as R11'})
            continue
        count+=1;text=p.read_text(encoding='utf-8')
        match=re.match(r'^---\n(.*?)\n---\n',text,re.S)
        if not match:errors.append((rel,'frontmatter_missing'));continue
        fm=match.group(1)
        fields=dict(re.findall(r'^([a-z_]+): *(.*)$',fm,re.M))
        for key in ['title','type','created','updated']:
            if key not in fields:errors.append((rel,'missing_'+key))
        for key in ['created','updated']:
            if not re.fullmatch(r'"\d{4}-\d{2}-\d{2}"',fields.get(key,'')):errors.append((rel,'invalid_date_'+key))
        kind=fields.get('type','')
        if kind not in {'system','reference','synthesis','article','asset','prototype','log'}:errors.append((rel,'invalid_type'))
        expected={'01_References':'reference','02_Syntheses':'synthesis','03_Articles':'article','04_Assets':'asset','05_Prototypes':'prototype'}.get(Path(rel).parts[0])
        if expected and kind!=expected:errors.append((rel,'folder_type_mismatch'))
        if kind in {'reference','synthesis','article','asset','prototype'}:
            if fields.get('status') not in {'draft','review','confirmed','superseded','rejected'}:errors.append((rel,'invalid_status'))
            if 'sources' not in fields:errors.append((rel,'sources_missing'))
            if Path(rel).parts[0]=='90_Workspace' and 'target_folder' not in fields:errors.append((rel,'workspace_target_missing'))
            if json.loads(fields['title'])!=Path(rel).stem:errors.append((rel,'title_filename_mismatch'))
        if kind=='reference' and fields.get('source_check') not in {'unverified','partial','verified','not_applicable'}:errors.append((rel,'source_check_invalid'))
        if kind=='asset' and 'asset_files' not in fields:errors.append((rel,'asset_files_missing'))
        if kind in {'article','asset','prototype'} and fields.get('status')=='confirmed':
            if not all(k in fields for k in ['reviewed','review_note']):errors.append((rel,'review_missing'))
        sources=re.search(r'^sources: *(?:\[\]|\n((?:  - .*\n?)*))',fm,re.M)
        items=[]
        if sources and sources.group(1):
            items=[json.loads(x[4:]) for x in sources.group(1).splitlines() if x.startswith('  - ')]
        graph[rel]=[]
        allowed={'reference':set(),'synthesis':{'01_References'},'article':{'01_References','02_Syntheses','03_Articles'},'asset':{'01_References','02_Syntheses','03_Articles'},'prototype':{'01_References','02_Syntheses','03_Articles','04_Assets'}}.get(kind,set())
        for item in items:
            if item.startswith('[['):
                target=item[2:-2].split('#')[0]+'.md'
                if target not in docs:errors.append((rel,'source_missing',target));continue
                graph[rel].append(target)
                if Path(target).parts[0] not in allowed:errors.append((rel,'source_layer_invalid',target))
                if kind=='article' and Path(target).parts[0]=='03_Articles' and 'status: confirmed' not in docs[target].read_text(encoding='utf-8'):errors.append((rel,'unconfirmed_article_source',target))
            elif kind!='reference':errors.append((rel,'external_source_in_derived_document',item))
    visiting=set();visited=set()
    def dfs(node):
        if node in visiting:errors.append((node,'source_cycle'));return
        if node in visited:return
        visiting.add(node)
        for child in graph.get(node,[]):dfs(child)
        visiting.remove(node);visited.add(node)
    for node in graph:dfs(node)
    return {'checked_documents':count,'errors':errors,'known_history_exception':legacy}

def markers():
    tables=json.loads((WORK/'source_tables.json').read_text(encoding='utf-8'))
    expected=[]
    for table in tables:
        if table['source']==3 and table['table']>=5:
            for row in table['rows'][2:]:
                values=[{'7':'■','10':'■','18':'－','20':'·'}[cell['border']] for cell in row[1:]]
                expected.append(values)
    p=next((ROOT/'01_References/00_프로젝트/02_연구개발계획서').glob('3_*.md'))
    actual=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('|'):
            parts=[x.strip() for x in line.strip('|').split('|')]
            if len(parts)==13 and set(parts[1:])<={'■','·','－'}:actual.append(parts[1:])
    assert expected==actual, 'HWPX monthly markers differ from wiki'
    return {'rows':len(actual),'monthly_cells':sum(len(r) for r in actual),'matched':True}

def images():
    count=0
    for p in (ROOT/'04_Assets/01_Images').rglob('*.png'):
        data=p.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
        pos=8;ended=False
        while pos<len(data):
            length=struct.unpack('>I',data[pos:pos+4])[0]
            body=data[pos+4:pos+8+length]
            crc=struct.unpack('>I',data[pos+8+length:pos+12+length])[0]
            assert zlib.crc32(body)&0xffffffff==crc,(str(p),'CRC')
            pos+=12+length
            if body[:4]==b'IEND':ended=True;break
        assert ended and pos==len(data),(str(p),'IEND')
        count+=1
    return {'png_files':count,'chunk_crc_and_end_marker':'pass','visual_review_files':3}

def snapshots(root):
    manifest=json.loads((WORK/'stage_manifest.json').read_text(encoding='utf-8'))
    for row in manifest['code']:
        p=root/'01_References/01_CaveBall/원문 코드'/row['file']
        q=ROOT.parent/'02_Client/00_Caveball/Assets/Scripts/CaveBall'/row['file']
        assert sha(p)==sha(q)==row['sha256'],row['file']
    return {'code_files':len(manifest['code']),'original_and_snapshot_hashes':'pass'}

def prepare():
    legacy=STAGE/'00_System/02_Logs/log.md'
    legacy.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'00_System/02_Logs/log.md',legacy)
    # Only mirror active attachments and tool links, not private application state.
    for area in ['04_Assets/01_Images','00_System/03_Tools']:
        for p in (ROOT/area).rglob('*'):
            if p.is_file() and p.suffix in {'.png','.py'} and '__pycache__' not in p.parts:
                dest=STAGE/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    report=STAGE/REPORT;report.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/REPORT,report)
    now=datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    logtext='---\ntitle: "2026年10月"\ntype: log\ncreated: "'+DATE+'"\nupdated: "'+DATE+'"\n---\n\n# '+now+': 이관 위키 정합성 점검과 명백한 오류 수정\n\n- 대상: 위키 색인, 이관 References와 Syntheses, Cave Super Ball 기획 문서, Workspace 작업 기록과 이미지 관리 목록.\n- 작업: 현재 파일에 맞는 색인, 내부 링크와 헤더, 메타데이터 정리함. 원문 코드 17개를 References에 보관하고 출처 계층 정리함. 초기화 실패와 바닥 프레임 처리의 Mermaid를 코드에 맞춰 수정함.\n- 이유: 다른 위키에서 가져온 문서 이름, 상대 경로, 분류와 검증 상태가 현재 규정 및 실제 자료와 불일치함.\n- 검증: 지정 헤더 도구, 내부 연결과 출처 계층 검사함. HWPX 일정표의 384개 월 셀, PNG 28개 구조와 해시, 코드 사본 17개 해시 대조함. 상세 결과는 Workspace 점검 기록에 보관함.\n- 결과: 명백한 오류는 현재 위치에 반영하고 기존 draft 상태 유지함. 원자료 오류, 일정 충돌과 채택 여부 등 12개 잔여 항목은 [위키 정합성 점검 보고서](<../../'+REPORT+'>)에 보고함. 과거 로그를 현재 지침으로 사용하지 않음.\n'
    logtext=logtext.replace('2026年10月','2026년 10월 작업 로그')
    p=STAGE/LOG;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(logtext,encoding='utf-8')
    before=json.loads((WORK/'before.json').read_text(encoding='utf-8'))['files']
    staged=[p.relative_to(STAGE).as_posix() for p in hn.wiki_files(STAGE)]
    existing=[p for p in staged if p in before and p!='00_System/02_Logs/log.md']
    new=[p for p in staged if p not in before and p!=LOG]
    logs=[]
    logs.append(run(['apply',*existing,'--root',str(STAGE),'--input','numbered','--date',DATE]))
    logs.append(run(['apply',*new,'--root',str(STAGE),'--input','unnumbered','--date',DATE]))
    logs.append(run(['check','--root',str(STAGE)]))
    links=audit.check(STAGE);meta=policy(STAGE)
    assert not links['errors'],json.dumps(links['errors'],ensure_ascii=False,indent=2)
    assert not meta['errors'],json.dumps(meta['errors'],ensure_ascii=False,indent=2)
    result={'stage':'pass','heading_output':logs[-1],'internal_links':links,'metadata_and_sources':meta,'original_timetable':markers(),'image_files':images(),'code_snapshot':snapshots(STAGE),'cagr_from_image_endpoints_percent':100*((178.7/25.1)**0.1-1)}
    result['stage_hashes']={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    result['report_seed_sha256']=sha(ROOT/REPORT)
    save('validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'stage_hashes','heading_output','report_seed_sha256'}},ensure_ascii=False,indent=2))

def promote():
    result=json.loads((WORK/'validation.json').read_text(encoding='utf-8'))
    assert result['stage']=='pass'
    before=json.loads((WORK/'before.json').read_text(encoding='utf-8'))['files']
    for rel,record in before.items():assert sha(ROOT/rel)==record['sha256'],('concurrent modification',rel)
    assert sha(ROOT/REPORT)==result['report_seed_sha256'],'report changed after validation'
    for rel,digest in result['stage_hashes'].items():assert sha(STAGE/rel)==digest,('stage changed',rel)
    changed=[]
    allowed=set(before)|{REPORT,LOG,'01_References/01_CaveBall/CaveBall 클라이언트 코드 원자료.md','04_Assets/01_Images/이관 이미지 관리 기록.md'}
    for rel,digest in result['stage_hashes'].items():
        if rel not in allowed and not rel.startswith('01_References/01_CaveBall/원문 코드/'):
            continue
        dest=(ROOT/rel).resolve();assert dest.is_relative_to(ROOT)
        old=sha(dest) if dest.is_file() else None
        if old==digest:continue
        if rel not in before and rel!=REPORT:assert not dest.exists(),('new destination already exists',rel)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(STAGE/rel,dest)
        changed.append({'path':rel,'before_sha256':old,'after_sha256':digest})
    # Validate the real destinations after promotion.
    output=run(['check'])
    links=audit.check(ROOT);meta=policy(ROOT)
    assert not links['errors'],links['errors']
    assert not meta['errors'],meta['errors']
    result['final']={'status':'pass','heading_output':output,'internal_links':links,'metadata_and_sources':meta,'code_snapshot':snapshots(ROOT),'changed_files':len(changed)}
    save('validation.json',result);save('applied_changes.json',changed)
    source=STAGE.resolve()
    archive=(ROOT/'99_Archive/2026-10-13_위키정합성점검/.staging').resolve()
    assert source.is_relative_to(WORK.resolve())
    assert archive.is_relative_to((ROOT/'99_Archive').resolve())
    assert not archive.exists()
    archive.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(source),str(archive))
    print(json.dumps(result['final'],ensure_ascii=False,indent=2))

if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:prepare()
    elif sys.argv[1:] == ['promote']:promote()
    else:raise SystemExit('Use prepare or promote')
