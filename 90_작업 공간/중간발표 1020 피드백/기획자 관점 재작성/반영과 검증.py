from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
STAGE = WORK / '중간발표 1020.md'
REPORT = ROOT / '03_Articles/보고서/중간발표 1020.md'
INDEX = ROOT / '00_System/00_Index/Index.md'
LOG = ROOT / '00_System/02_Logs/2026-10.md'
SNAPSHOT = WORK / '수정 전 상태.json'
RESULT = WORK / '검증 결과.json'
MANIFEST = json.loads((WORK.parent / '원문 목록.json').read_text(encoding='utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(path, staged):
    text = path.read_text(encoding='utf-8')
    front = text.split('---', 2)[1]
    assert 'status: review' in front if staged else 'status: draft' in front
    assert ('target_folder: 03_Articles' in front) == staged
    assert text.count('# 문서 정보\n') == 1
    assert 'created: "2026-10-23"' in front
    sources = re.findall(r'^  - "\[\[(.+?)\]\]"$', front, re.M)
    assert len(sources) == 14
    assert set(sources) == {m['reference'] for m in MANIFEST}
    links = re.findall(r'\]\(<([^>]+)>\)', text)
    assert len(links) == 15
    for target in links:
        assert (path.parent / target).resolve().is_file(), target
    sections = re.findall(r'^### [^\n]+\n(.*?)(?=^### |^## |\Z)', text, re.M | re.S)
    assert len(sections) == 14
    counts = {}
    cited = {}
    for section in sections:
        filename = re.search(r'^원문: \[([^\]]+)\]', section, re.M).group(1)
        assert filename not in counts
        points = re.findall(r'^(\d+)\. \*\*([^*]+)\*\*: (.+)$', section, re.M)
        assert [p[0] for p in points] == ['1', '2', '3', '4'], filename
        counts[filename] = len(points)
        source = (ROOT / '01_References/중간발표 1020/원문' / filename).read_text(encoding='utf-8')
        available = set(re.findall(r'^.+? (\d{2}:\d{2})\s*$', source, re.M))
        citations = re.findall(r'\(근거: ([\d:, ]+)\)', section)
        assert len(citations) == 5, filename
        used = {t.strip() for citation in citations for t in citation.split(',')}
        assert used <= available, (filename, used - available)
        cited[filename] = sorted(used)
    assert sum(counts.values()) == 56
    assert set(counts) == {m['file'] for m in MANIFEST}
    body = text.split('# 문서 정보', 1)[1]
    jargon = r'셰이더|쉐이더|GPU|API|렌더링|파이프라인|클록|좌표계|트래킹|블렌드|회귀|검정력|효과 크기|공변량|유의확률|신뢰도|표본|통계|HMD|NFC|CER|BERT'
    assert not re.search(jargon, body, re.I)
    assert '\u00b7' not in text and '\u2014' not in text
    assert not any(line.rstrip() != line for line in text.splitlines())
    source_hashes = {}
    for meta in MANIFEST:
        original = (ROOT / meta['original']).read_bytes()
        copy = (ROOT / meta['reference']).read_bytes()
        assert original == copy
        assert sha(copy) == meta['sha256']
        source_hashes[meta['file']] = sha(copy)
    return {'files': len(counts), 'feedback_total': sum(counts.values()),
            'feedback_per_file': counts, 'document_links_checked': len(links),
            'cited_timestamps': cited, 'original_and_reference_hashes': source_hashes}


def write_preserving(path, text, snapshot):
    ending = '\r\n' if '\r\n' in snapshot['text'] else '\n'
    path.write_bytes(text.replace('\r\n', '\n').replace('\n', ending).encode('utf-8'))


mode = sys.argv[1]
if mode == 'stage':
    result = check(STAGE, True)
    snapshots = {}
    for path in (REPORT, INDEX, LOG):
        raw = path.read_bytes()
        snapshots[path.relative_to(ROOT).as_posix()] = {'sha256': sha(raw), 'text': raw.decode('utf-8')}
    assert not SNAPSHOT.exists(), '기존 수정 전 상태를 덮어쓰지 않음'
    SNAPSHOT.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
elif mode == 'publish':
    result = check(STAGE, True)
    snapshots = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    for rel, item in snapshots.items():
        assert sha((ROOT / rel).read_bytes()) == item['sha256'], f'작업 중 변경 감지: {rel}'
    report = STAGE.read_text(encoding='utf-8').replace('status: review\n', 'status: draft\n', 1)
    report = report.replace('target_folder: 03_Articles\n', '', 1)
    report = report.replace('](<../../../01_References/', '](<../../01_References/')
    index = snapshots[INDEX.relative_to(ROOT).as_posix()]['text'].replace('\r\n', '\n')
    old = '- [중간발표 1020](<../../03_Articles/보고서/중간발표 1020.md>): 발표 녹취 14개를 검토한 초안. 파일별 4~5개, 총 65개 피드백과 근거 시각 기록함.'
    new = '- [중간발표 1020](<../../03_Articles/보고서/중간발표 1020.md>): 게임 기획자의 관점으로 재작성한 초안. 발표별 4개, 총 56개 피드백과 원문 근거 시각 기록함.'
    assert index.count(old) == 1
    index = index.replace(old, new)
    now = datetime.now(timezone(timedelta(hours=9)))
    assert now.strftime('%Y-%m') == '2026-10'
    date = now.strftime('%Y-%m-%d')
    report = re.sub(r'^updated: "[^"]+"$', f'updated: "{date}"', report, count=1, flags=re.M)
    log = snapshots[LOG.relative_to(ROOT).as_posix()]['text'].replace('\r\n', '\n')
    front_end = log.index('\n---\n', 4) + len('\n---\n')
    entry = f'''\n# {now.strftime('%Y-%m-%d %H:%M')}: 중간발표 1020 피드백을 게임 기획자 관점으로 재작성

- 대상: `03_Articles/보고서/중간발표 1020.md`, 위키 색인과 Workspace 재작성본.
- 작업: 발표 녹취 14개를 다시 읽고 발표별 4개, 총 56개 피드백으로 재작성함. 발표 요지와 소제목도 쉬운 표현으로 정리하고 원문 링크와 근거 시각 유지함.
- 이유: 사용자가 자신의 게임 기획 경험과 지식 범위에 맞는 피드백을 요청함. 하드웨어, 테크니컬 아트 및 전문 분석 방법에 대한 요구를 제거하고 사용자 행동, 재미, 선택, 조작과 활용 장면 중심으로 변경함.
- 검증: 재작성본의 헤더 번호와 계층 검사 통과함. 발표 14개, 피드백 56개, 내부 문서 링크 15개 및 각 근거 시각의 원문 존재 확인함. 원본과 References 사본 14개의 바이트 및 기존 SHA-256 일치 확인함. 각 의견을 해당 원문 맥락과 대조함. 원음과 슬라이드는 미확인임.
- 결과: 기존 보고서에 재작성본을 반영하고 `status: draft` 유지함. 색인의 관점과 피드백 수 갱신함. 수정 전 상태와 검증 결과는 Workspace에 보관함.

'''
    log = log[:front_end] + entry + log[front_end:].lstrip('\n')
    for path, value in ((INDEX, index), (LOG, log)):
        value = re.sub(r'^updated: "[^"]+"$', f'updated: "{date}"', value, count=1, flags=re.M)
        write_preserving(path, value, snapshots[path.relative_to(ROOT).as_posix()])
    write_preserving(REPORT, report, snapshots[REPORT.relative_to(ROOT).as_posix()])
    result = check(REPORT, False)
    result['published_at'] = now.isoformat(timespec='seconds')
elif mode == 'final':
    result = check(REPORT, False)
    assert '총 56개 피드백' in INDEX.read_text(encoding='utf-8')
    assert '피드백을 게임 기획자 관점으로 재작성' in LOG.read_text(encoding='utf-8')
    expected = STAGE.read_text(encoding='utf-8').replace('status: review\n', 'status: draft\n', 1)
    expected = expected.replace('target_folder: 03_Articles\n', '', 1)
    expected = expected.replace('](<../../../01_References/', '](<../../01_References/')
    assert REPORT.read_text(encoding='utf-8') == expected
else:
    raise ValueError(mode)

result['checked_at'] = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
result['check_mode'] = mode
result['limits'] = '원음과 슬라이드 미대조. 피드백은 게임 기획 관점의 의견과 제안임.'
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ('files', 'feedback_total', 'document_links_checked', 'check_mode')}, ensure_ascii=False))
