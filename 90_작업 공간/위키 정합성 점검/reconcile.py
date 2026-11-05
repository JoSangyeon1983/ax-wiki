"""Stage and apply narrowly scoped re-audit corrections with concurrent-edit guards."""
from pathlib import Path
import hashlib
import json
import re
import sys
import shutil
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
STAGE = WORK / '.recheck_stage'
sys.path.insert(0, str(ROOT/'00_System/03_Tools'))
import heading_numbers as hn

def stage():
    changes = {}
    def put(p, text):
        rel = p.relative_to(ROOT).as_posix()
        old = p.read_bytes()
        if old.decode('utf-8') == text: return
        target = STAGE/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text,encoding='utf-8')
        changes[rel] = {'before':hashlib.sha256(old).hexdigest(), 'after':hashlib.sha256(target.read_bytes()).hexdigest()}
    for p in (ROOT/'01_References/00_프로젝트/02_연구개발계획서').glob('*.md'):
        text = p.read_text(encoding='utf-8').replace('source_check: partial','source_check: verified')
        text = text.replace('- 과거 대조 이력은 이관 당시 기록임. 이번 점검의 전체 원문 검증 완료로 해석하지 않음.', '- 원자료 대조 상태: 2026-10-13 사용자가 기존 위키에서 HWPX 변환 문서의 원문 대조를 마친 뒤 이관했음을 확인함. `source_check: verified`는 그 이관본의 원문 대조 완료 상태를 반영함. 이번 재점검에서 HWPX 대조를 반복한 것은 아님.\n- 대조 완료와 원자료 자체의 사실성 구분: 원문의 일정 불일치, 그림 번호 중복과 별도 이미지 해석의 확인 한계는 그대로 보존함. 원자료의 외부 사실 검증이나 추가 그림 추출 완료를 뜻하지 않음.')
        text = text.replace('- 2026-10-13 점검:', '- 2026-10-13 최초 점검의 직접 확인 범위:')
        text = text.replace('전체 표와 원문 이미지 34개의 완전성은 미확인임.', '표의 원문 대조 완료 상태는 아래 사용자 확인에 따름. 원문 이미지 34개는 이관 문서에서 자리표시자로 유지됨.')
        put(p,text)
    p = ROOT/'00_System/00_Index/Index.md'
    text = p.read_text(encoding='utf-8').replace('원자료 일부 대조 상태의 이관본.', '기존 위키에서 원문 대조 완료 후 이관한 문서. 사용자 확인 반영함.')
    text = text.replace('명백한 오류의 수정 결과와 판단이 필요한 잔여 항목.', '재점검 결과, 수정 완료 항목과 원문 불일치 및 향후 검토 사항의 구분.')
    put(p,text)
    p = ROOT/'00_System/01_Rules/위키 작업 절차.md'
    text = re.sub(r'\]\(([^)\n]*%20[^)\n]*)\)',lambda m: '](<'+m[1].replace('%20',' ')+'>)',p.read_text(encoding='utf-8'))
    put(p,text)
    p = ROOT/'00_System/02_Logs/log.md'
    text = p.read_text(encoding='utf-8')
    assert not text.startswith('---')
    put(p,'---\ntitle: "이관된 과거 작업 기록"\ntype: log\ncreated: "2026-10-13"\nupdated: "2026-10-13"\n---\n\n> 다른 위키에서 가져온 과거 기록의 보관본임. 프론트매터의 작성일은 이 위키에서 보관 문서로 정비한 날짜이며 원래 로그 파일의 최초 작성일은 미확인임. 아래 날짜, 경로와 당시 절차는 역사적 기록으로 보존함. 현재 운영 지침은 AGENTS.md와 지정 규정에 따름.\n\n'+text)
    p = ROOT/'03_Articles/기획서/Cave Super Ball 기획서.md'
    text = p.read_text(encoding='utf-8')
    text = text.replace('코어 시스템은 코드 분석과 계층형 플로우를 참고함.', '코어 시스템은 [CaveBall 클라이언트 코드 구조 분석](<../../02_Syntheses/CaveBall 클라이언트 코드 구조 분석.md>)과 [CaveBall 계층형 플로우](<../../02_Syntheses/CaveBall 계층형 플로우.md>)를 참고함.')
    for num, title, anchor in [('4.1','콘텐츠 준비','2-사전-프로세스-a-콘텐츠-준비'),('4.2','손 입력 처리','3-사전-프로세스-b-손-입력-처리'),('4.3','바닥 입력 처리','4-사전-프로세스-c-바닥-입력-처리')]:
        heading = f'## {num} {title}\n'
        text = text.replace(heading, heading+f'\n근거: [CaveBall 계층형 플로우: {title}](<../../02_Syntheses/CaveBall 계층형 플로우.md#{anchor}>). 정적 코드 설명이며 실제 설치 및 실행 검증과 구분함.\n')
    put(p,text)
    p = ROOT/'03_Articles/기획서/Cave Super Ball 기획서 초안.md'
    text = p.read_text(encoding='utf-8').replace('이 콘텐츠를 셀빅의 1차년도', '**기획상 해석**: 원자료에서 Cave Super Ball을 특정한 것은 아니며, 본 초안에서 이 콘텐츠를 셀빅의 1차년도',1)
    put(p,text)
    (WORK/'recheck_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'staged':len(changes),'paths':list(changes)},ensure_ascii=False))

def apply():
    changes = json.loads((WORK/'recheck_changes.json').read_text(encoding='utf-8'))
    catalog = {p:hn.parse(p,p.read_text(encoding='utf-8'),ROOT) for p in hn.wiki_files(ROOT) if '99_Archive' not in p.relative_to(ROOT).parts}
    for rel, info in changes.items():
        p = ROOT/rel
        assert hashlib.sha256(p.read_bytes()).hexdigest()==info['before'], 'Changed while staging: '+rel
        text = (STAGE/rel).read_text(encoding='utf-8')
        doc = hn.parse(p,text,ROOT)
        assert not hn.numbered(doc,'check')[1], rel
        catalog[p.resolve()] = doc
    issues = hn.link_issues(catalog,{(ROOT/r).resolve() for r in changes},ROOT)
    assert not issues, str(issues)
    for rel in changes: shutil.copyfile(STAGE/rel, ROOT/rel)
    print('Applied '+str(len(changes))+' documents; staged headings and links passed.')

def log():
    p = ROOT/'00_System/02_Logs/2026-10.md'
    stamp = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    entry = f'''# {stamp}: イ관 정합성 재점검과 보고 범위 정정

- 대상: 연구개발계획서 5개, 색인, 위키 작업 절차, 이관 과거 로그, 기획 초안 2개와 정합성 점검 보고서.
- 작업: 사용자 확인에 따라 기존 위키의 원문 대조 완료 상태를 복원함. 운영 규정의 링크 표기 5곳, 과거 로그의 프론트매터, 기획 문서의 근거 연결과 기획상 해석 표시를 보완함.
- 이유: 원문 대조 완료 이력을 최초 점검의 일부 확인 범위와 혼동하고, 원문 불일치와 향후 개발 검토 사항을 사용자 해결 과제로 과도하게 보고한 문제 정정함.
- 검증: 활성 Markdown 26개의 메타데이터, 출처 목록 계층과 내부 연결 점검함. 헤더 도구로 비로그 문서 24개 검사 통과함. 이미지 28개와 코드 사본 17개의 관리 해시 일치 확인함. 실무 미팅 사용자 정정 사항과 개인 이름 표기 범위 확인함.
- 결과: 현재 연결 오류와 필수 메타데이터 누락 해소함. 존재가 확인되지 않은 협약 변경본 요청 철회함. 원문 일정 불일치와 7월 회의일의 불확실성은 보존하고, 초안 통합 및 실행 검증 등은 향후 작업으로 구분함. HWPX 재대조와 원본 수정 없음.

'''.replace('イ관','이관')
    text = p.read_text(encoding='utf-8')
    end = text.index('\n---',4)+4
    p.write_text(text[:end]+'\n\n'+entry+text[end:].lstrip(),encoding='utf-8')
    print('Monthly log updated.')

def finalize():
    before = json.loads((WORK/'recheck_before.json').read_text(encoding='utf-8'))
    changes = {}
    for rel, record in before.items():
        p = ROOT/rel
        now = hashlib.sha256(p.read_bytes()).hexdigest()
        if now != record['sha256']:
            changes[rel] = {'before':record['sha256'], 'after':now}
        if rel.startswith('01_References/00_프로젝트/02_연구개발계획서/'):
            original_body = record['text'].split('# 1 원문 사본',1)[1].split('# 2 대조 범위와 한계',1)[0]
            current_body = p.read_text(encoding='utf-8').split('# 1 원문 사본',1)[1].split('# 2 대조 범위와 한계',1)[0]
            assert original_body == current_body, rel
        if rel.startswith(('01_References/90_회의록/','02_Syntheses/90_회의록/')):
            assert now == record['sha256'], rel
    (WORK/'recheck_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'changed_documents':len(changes),'plan_original_bodies':'unchanged','meeting_documents':'unchanged'},ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'stage':stage,'apply':apply,'log':log,'finalize':finalize}[sys.argv[1]]()
