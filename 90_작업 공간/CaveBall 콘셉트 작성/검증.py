from pathlib import Path
import hashlib
import json
import re

wiki = Path.cwd()
work = wiki / '90_작업 공간/CaveBall 콘셉트 작성'
concept_paths = [
    '03_기반 기획/콘셉트/Cave Super Ball 기획서 초안.md',
    '03_기반 기획/콘셉트/Cave Action 콘셉트 기획서.md',
]
doc_paths = concept_paths + [
    '01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/2026-11-05 CaveBall 프로젝트 구현 원자료.md',
    '02_기획 근거/CaveBall 프로젝트/CaveBall과 Cave Action 콘셉트 작성 기준.md',
    '00_시스템/00_색인/위키 색인.md',
    '90_작업 공간/CaveBall 콘셉트 작성/콘셉트 작성 기록.md',
]
checks = []
for relative in concept_paths:
    text = (wiki / relative).read_text(encoding='utf-8')
    assert re.findall(r'^# (.+)$', text, re.M) == ['1 개요', '2 전체 플로우', '3 주요 시스템'], relative
    assert 'status: draft' in text and 'approval_status: pending' in text, relative
    assert 'planning_role: foundation' in text, relative
    front = text.split('---', 2)[1]
    assert '02_기획 근거/' in front, relative
    assert '05_참고 자료' not in text, relative
    checks.append({'path': relative, 'h1_count': 3, 'status': 'draft', 'approval_status': 'pending'})
link_count = 0
for relative in doc_paths:
    path = wiki / relative
    text = path.read_text(encoding='utf-8')
    assert '\u00b7' not in text and '\u2014' not in text, relative
    for target in re.findall(r'\]\(<([^>]+)>\)', text):
        file_part = target.split('#', 1)[0]
        if not file_part or '://' in file_part:
            continue
        assert (path.parent / file_part).resolve().exists(), (relative, file_part)
        link_count += 1
initial = json.loads((work / '최초 근거 추출.json').read_text(encoding='utf-8'))
extra = json.loads((work / '추가 근거 추출.json').read_text(encoding='utf-8'))
mapping = json.loads((work / '구조 대응.json').read_text(encoding='utf-8'))
ids = [x['id'] for x in initial['units'] + extra['units']]
assert len(ids) == len(set(ids)) == 35
assert set(ids) == set(mapping['mapping'])
snapshot = wiki / '01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료'
manifest = json.loads((snapshot / '원문 파일 목록.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    copied = snapshot / '원문' / item['path']
    original = Path(manifest['source_project']) / item['path']
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == item['sha256']
    assert copied.read_bytes() == original.read_bytes()
assert len(manifest['files']) == 19
result = {'concepts': checks, 'evidence_units_mapped': len(ids), 'source_files_verified': len(manifest['files']),
          'existing_file_links_checked': link_count,
          'scope': 'Document structure, source trace, local file links and source-copy bytes. No Unity execution.'}
(work / '검증 결과.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'concepts':len(checks), 'evidence_units':len(ids), 'source_files':len(manifest['files']), 'local_links':link_count}))
