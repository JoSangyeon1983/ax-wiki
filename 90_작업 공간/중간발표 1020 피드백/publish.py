from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
manifest = json.loads((WORK / '원문 목록.json').read_text(encoding='utf-8'))
snapshots = json.loads((WORK / '수정 전 상태.json').read_text(encoding='utf-8'))
now = datetime.now(timezone(timedelta(hours=9)))
date = now.strftime('%Y-%m-%d')
time = now.strftime('%H:%M')
ref_stage = WORK / '등록안/중간발표 1020 발표 원자료.md'
ref_target = ROOT / '01_References/중간발표 1020/중간발표 1020 발표 원자료.md'
report_stage = WORK / '중간발표 1020.md'
report_target = ROOT / '03_Articles/보고서/중간발표 1020.md'

for rel, snapshot in snapshots.items():
    assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == snapshot['sha256'], f'작업 중 변경 감지: {rel}'
for meta in manifest:
    original = ROOT / meta['original']
    staged = WORK / '등록안/원문' / meta['file']
    target = ROOT / meta['reference']
    assert hashlib.sha256(original.read_bytes()).hexdigest() == meta['sha256']
    assert original.read_bytes() == staged.read_bytes()
    assert not target.exists() or target.read_bytes() == staged.read_bytes(), f'기존 원자료 충돌: {target}'
assert not ref_target.exists(), '원자료 설명 문서가 이미 존재함. 기존 내용 검토 필요.'

reference = ref_stage.read_text(encoding='utf-8').replace('target_folder: 01_References\n', '')
report = report_stage.read_text(encoding='utf-8').replace('target_folder: 03_Articles\n', '')
assert 'target_folder:' not in reference and 'target_folder:' not in report

index = snapshots['00_System/00_Index/Index.md']['text'].replace('\r\n', '\n')
old_description = '- [중간발표 1020](<../../03_Articles/보고서/중간발표 1020.md>): 사용자 추가 문서. 본문과 근거 자료가 미등록된 초안임.'
new_description = '- [중간발표 1020](<../../03_Articles/보고서/중간발표 1020.md>): 발표 녹취 14개를 검토한 초안. 파일별 4~5개, 총 65개 피드백과 근거 시각 기록함.'
assert index.count(old_description) == 1
index = index.replace(old_description, new_description)
source_entry = '### 4.1.3 발표 원자료\n\n- [중간발표 1020 발표 원자료](<../../01_References/중간발표 1020/중간발표 1020 발표 원자료.md>): 사용자 제공 TXT 14개의 원문 사본과 보존 정보. 원음과 발표 자료는 미대조임.\n\n'
assert index.count('## 4.2 Syntheses') == 1
index = index.replace('## 4.2 Syntheses', source_entry + '## 4.2 Syntheses')

log = snapshots['00_System/02_Logs/2026-10.md']['text'].replace('\r\n', '\n')
front_end = log.index('\n---\n', 4) + len('\n---\n')
entry = f'''
# {date} {time}: 중간발표 1020 발표별 피드백 작성

- 대상: `03_Articles/보고서/중간발표 1020.md`, `01_References/중간발표 1020`, 위키 색인과 Workspace 검토 자료.
- 작업: 제공 TXT 14개를 전체 읽고 원문 위치가 있는 822개 단위를 추출한 뒤 주제와 근거를 대응시킴. 파일별 발표 요지와 4~5개 피드백, 총 65개를 작성하고 원문 링크 및 근거 시각 추가함. 출처 계층에 맞춰 원문 사본과 설명 문서를 References에 등록함.
- 이유: 사용자가 각 텍스트 파일의 발표 내용을 분석해 파일별 3~5개 피드백을 문서에 추가하도록 요청함.
- 검증: Workspace 문서 2개의 헤더 번호와 계층 및 헤더 링크 검사 통과함. 파일 14개와 피드백 수, 각 근거 시각의 원문 존재를 확인함. 원본과 References 사본 14개의 바이트 및 SHA-256 일치 확인함. 원음과 슬라이드 및 실험 원자료는 미대조임.
- 결과: 기존 보고서에 피드백 초안 반영하고 `status: draft` 유지함. 원자료 설명은 `source_check: partial`로 등록함. 원본 TXT 14개는 제공 위치와 내용 유지함. 녹취의 불명확한 수치 및 용어와 실제 발표일은 미확인으로 보존함.

'''
log = log[:front_end] + entry + log[front_end:].lstrip('\n')

for meta in manifest:
    target = ROOT / meta['reference']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((WORK / '등록안/원문' / meta['file']).read_bytes())
    assert target.read_bytes() == (ROOT / meta['original']).read_bytes()
ref_target.write_text(reference, encoding='utf-8')
report_target.write_text(report, encoding='utf-8')
for rel, text in [('00_System/00_Index/Index.md', index), ('00_System/02_Logs/2026-10.md', log)]:
    original_text = snapshots[rel]['text']
    ending = '\r\n' if '\r\n' in original_text else '\n'
    (ROOT / rel).write_bytes(text.replace('\n', ending).encode('utf-8'))
print(json.dumps({'published': str(report_target.relative_to(ROOT)), 'references': len(manifest), 'feedback': 65, 'log_time': f'{date} {time}'}, ensure_ascii=False))
