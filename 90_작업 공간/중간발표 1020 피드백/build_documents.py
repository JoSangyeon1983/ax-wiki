from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
DATE = '2026-10-23'
REFERENCE_DIR = '01_References/중간발표 1020'
REFERENCE_NAME = '중간발표 1020 발표 원자료.md'
data = json.loads((WORK / '피드백 구성.json').read_text(encoding='utf-8'))
manifest = json.loads((WORK / '원문 목록.json').read_text(encoding='utf-8'))
extraction = json.loads((WORK / '최초 추출표.json').read_text(encoding='utf-8'))
units = extraction['units']
by_file = {item['file']: item for item in data}
assert set(by_file) == {item['file'] for item in manifest}
assert all(3 <= len(item['items']) <= 5 for item in data)

# 피드백의 근거 위치와 전체 추출 단위의 채택 및 제외를 대응시킴.
mapping = []
for record in data:
    source_units = [u for u in units if u['file'] == record['file']]
    stamps = {u['timestamp'] for u in source_units}
    requested = set(record['summary_times'])
    requested.update(t for point in record['items'] for t in point['times'])
    assert requested <= stamps, (record['file'], requested - stamps)
    for unit in source_units:
        targets = []
        if unit['timestamp'] in record['summary_times']:
            targets.append('발표 요지')
        for index, point in enumerate(record['items'], 1):
            if unit['timestamp'] in point['times']:
                targets.append(f'피드백 {index}: {point["title"]}')
        is_logistics = (
            record['file'].startswith('09_') and unit['timestamp'] < '01:12'
        ) or (
            record['file'].startswith('15_') and unit['timestamp'] >= '11:25'
        ) or bool(re.fullmatch(r'(?:네[,. ]*)?(?:감사합니다|알겠습니다|잘 들었습니다|고맙습니다|수고하셨습니다)[.! ]*', unit['text'].strip()))
        if is_logistics:
            targets = []
            reason = '인사, 발표 준비 또는 전체 진행 안내로 연구 피드백에서 제외함.'
        elif not targets:
            reason = '전체 맥락 확인에 사용했으나 파일별 3~5개 피드백의 직접 근거로 채택하지 않은 세부 설명 또는 반복 질의임.'
        else:
            reason = None
        mapping.append({'id': unit['id'], 'file': unit['file'], 'line': unit['line'], 'timestamp': unit['timestamp'], 'targets': targets, 'excluded_reason': reason})
assert len(mapping) == len(units) and all(m['targets'] or m['excluded_reason'] for m in mapping)
(WORK / '원문 대응표.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

groups = list(dict.fromkeys(item['group'] for item in data))
source_paths = [m['reference'] for m in manifest]

def front(title, kind, status, target):
    lines = ['---', f'title: "{title}"', f'type: {kind}', f'created: "{DATE}"', f'updated: "{DATE}"', f'status: {status}', 'sources:']
    lines += [f'  - "[[{path}]]"' for path in source_paths]
    if kind == 'reference':
        lines.append('source_check: partial')
    lines += [f'target_folder: {target}', '---', '']
    return lines

reference = front('중간발표 1020 발표 원자료', 'reference', 'confirmed', '01_References')
reference += [
    '# 자료 개요', '',
    '- 사용자 제공 발표 녹취 TXT 14개의 원문 사본과 보존 정보를 관리함.',
    '- 최초 제공 위치는 `04_Assets/02_Records`이며 해당 파일은 수정하거나 이동하지 않음. 출처 계층에 맞춰 이 문서와 같은 폴더의 `원문`에 바이트가 동일한 사본을 등록함.',
    '- 발표자 표기는 파일명 기준임. 자동 녹취의 발언자 이름이나 참석자 번호와 실제 인물의 대응은 별도로 검증하지 않음.',
    '- 문서 식별명 `1020`과 TXT 헤더의 `2026.10.23`을 구분함. 헤더 날짜의 의미와 실제 발표일은 미확인임.', '',
    '# 출처와 작성 방식', '',
    '- 각 TXT에 클로바 노트 주소, 발언자와 발언 시작 시각이 포함되어 있음. 사용자 제공 녹취 텍스트로 취급하며 원문 표현을 교정하지 않음.',
    '- 발표 본문과 질의응답을 모두 읽고 연구 목적, 방법, 진행 상태와 검토 의견을 구분함. 원음, 발표 슬라이드와 실험 및 통계 원자료의 대조는 수행하지 않음.',
    '- 동일 발표의 복수 녹취를 대조한 완성본이나 회의록을 작성한 작업이 아님. TXT의 수치와 전문용어에 남은 불명확성은 보존함.',
    '- `source_check: partial`은 제공된 텍스트 전체와 사본 보존은 확인했으나 실제 발언 및 연구 결과의 정확성은 검증하지 않았다는 의미임.', '',
    '# 파일 목록과 보존 검증', '',
    '아래 시각은 각 TXT의 첫 발언과 마지막 발언의 시작 시각임. 녹음 전체 길이나 실제 행사 시각을 뜻하지 않음. 해시는 원본과 등록 사본 모두에 대해 확인한 SHA-256 값임.', ''
]
for group in groups:
    reference += [f'## {group}', '', '| 파일 | 포함 시각 | 줄 수 | SHA-256 |', '|---|---|---|---|']
    for item in data:
        if item['group'] != group:
            continue
        meta = next(m for m in manifest if m['file'] == item['file'])
        reference.append(f'| [{meta["file"]}](<원문/{meta["file"]}>) | {meta["first_timestamp"]}~{meta["last_timestamp"]} | {meta["lines"]} | `{meta["sha256"]}` |')
    reference.append('')
reference += [
    '# 확인 범위와 미확인 사항', '',
    '- TXT 14개 모두 UTF-8로 읽을 수 있으며, 각 파일의 첫 발언부터 마지막 발언까지 검토함.',
    '- 등록 사본은 원본 14개와 바이트 및 SHA-256이 일치함. 원본의 내용, 인코딩과 파일명 보존함.',
    '- 제공된 번호는 01~04와 06~15임. 05번 파일은 제공 폴더에 없으며 해당 발표를 추정하거나 피드백을 생성하지 않음.',
    '- 팬 집단 인원, 측정 API 명칭 등 녹취에서 불명확한 표현은 설문 원자료나 발표 자료로 재확인이 필요함. 텍스트만으로 임의 정정하지 않음.', ''
]
ref_stage = WORK / '등록안' / REFERENCE_NAME
ref_stage.write_text('\n'.join(reference), encoding='utf-8')

report = front('중간발표 1020', 'article', 'draft', '03_Articles')
report += [
    '# 문서 정보', '',
    '- 작성 상태: 발표 녹취 14개를 검토한 피드백 초안임. 발표자가 채택한 수정안이나 확정된 연구 평가가 아님.',
    f'- 입력 자료: [중간발표 1020 발표 원자료](<../../{REFERENCE_DIR}/{REFERENCE_NAME}>). 원본 파일 번호와 이름을 유지하고 연구 주제에 따라 묶음.',
    '- 검토 범위: 발표와 질의응답에 나타난 연구 목적, 비교 조건, 분석 방법과 해석 범위임. 원음, 슬라이드 및 실험 원자료는 미확인임.',
    '- 표기 기준: 발표 요지는 발표자의 설명을 요약한 것이며, 피드백은 이를 바탕으로 작성한 검토 의견과 제안임. 근거 시각은 각 TXT에 표시된 발언 시작 시각임.', '',
    '# 파일별 피드백', ''
]
for group in groups:
    report += [f'## {group}', '']
    for item in data:
        if item['group'] != group:
            continue
        name = item['file'].split('_')[1]
        report += [f'### {name}: {item["topic"]}', '', f'원문: [{item["file"]}](<../../{REFERENCE_DIR}/원문/{item["file"]}>)', '', f'발표 요지: {item["summary"]} (근거: {", ".join(item["summary_times"])})', '']
        for index, point in enumerate(item['items'], 1):
            report.append(f'{index}. **{point["title"]}**: {point["text"]} (근거: {", ".join(point["times"])})')
        report.append('')
report_stage = WORK / '중간발표 1020.md'
report_stage.write_text('\n'.join(report), encoding='utf-8')

snapshots = {}
for rel in ['03_Articles/보고서/중간발표 1020.md', '00_System/00_Index/Index.md', '00_System/02_Logs/2026-10.md']:
    raw = (ROOT / rel).read_bytes()
    snapshots[rel] = {'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8-sig')}
snapshot_path = WORK / '수정 전 상태.json'
if not snapshot_path.exists():
    snapshot_path.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'files': len(data), 'feedback': sum(len(i['items']) for i in data), 'source_units': len(units), 'groups': groups, 'per_file': {i['file']: len(i['items']) for i in data}}, ensure_ascii=False, indent=2))
