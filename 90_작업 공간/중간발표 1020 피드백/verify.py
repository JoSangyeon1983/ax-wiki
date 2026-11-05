from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
manifest = json.loads((WORK / '원문 목록.json').read_text(encoding='utf-8'))
plan = json.loads((WORK / '피드백 구성.json').read_text(encoding='utf-8'))
report_path = ROOT / '03_Articles/보고서/중간발표 1020.md'
source_path = ROOT / '01_References/중간발표 1020/중간발표 1020 발표 원자료.md'
report = report_path.read_text(encoding='utf-8')
source = source_path.read_text(encoding='utf-8')
assert set(p.name for p in (ROOT / '04_Assets/02_Records').glob('*.txt')) == {m['file'] for m in manifest}
assert len(manifest) == len(plan) == 14
hashes = {}
for meta in manifest:
    original = (ROOT / meta['original']).read_bytes()
    copy = (ROOT / meta['reference']).read_bytes()
    assert original == copy
    assert hashlib.sha256(original).hexdigest() == meta['sha256']
    assert meta['sha256'] in source
    hashes[meta['file']] = '원본 일치'

counts = {}
sections = re.split(r'^### .+\n', report, flags=re.M)[1:]
assert len(sections) == 14
for section in sections:
    match = re.search(r'^원문: \[([^\]]+)\]', section, flags=re.M)
    assert match
    filename = match.group(1)
    points = re.findall(r'^\d+\. \*\*', section, flags=re.M)
    expected = next(p for p in plan if p['file'] == filename)
    assert 3 <= len(points) <= 5 and len(points) == len(expected['items'])
    for item in expected['items']:
        assert item['text'] in section
        assert f'(근거: {", ".join(item["times"])})' in section
    counts[filename] = len(points)
assert set(counts) == {m['file'] for m in manifest}
assert sum(counts.values()) == 65

links = 0
for path in [report_path, source_path]:
    text = path.read_text(encoding='utf-8')
    front = text.split('---', 2)[1]
    assert 'target_folder:' not in front
    for field in ['title:', 'type:', 'created:', 'updated:', 'status:', 'sources:']:
        assert field in front
    for target in re.findall(r'\]\(<([^>]+)>\)', text):
        assert (path.parent / unquote(target)).resolve().is_file(), (path.name, target)
        links += 1
    sources = re.findall(r'^  - "\[\[(.+?)\]\]"$', front, flags=re.M)
    assert len(sources) == 14 and set(sources) == {m['reference'] for m in manifest}
    assert all((ROOT / target).is_file() for target in sources)
    assert '\u00b7' not in text and '\u2014' not in text
    assert not any(line.rstrip() != line for line in text.splitlines())
assert 'status: draft' in report
assert 'source_check: partial' in source
assert report.count('# 문서 정보\n') == 1
assert '본문 미작성' not in report
index = (ROOT / '00_System/00_Index/Index.md').read_text(encoding='utf-8')
assert index.count('[중간발표 1020]') == 1
assert index.count('[중간발표 1020 발표 원자료]') == 1
assert '총 65개 피드백' in index
result = {
    'checked_at': datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'),
    'report': report_path.relative_to(ROOT).as_posix(),
    'files': len(counts),
    'feedback_total': sum(counts.values()),
    'feedback_per_file': counts,
    'original_preservation': hashes,
    'document_links_checked': links,
    'source_paths_checked': 28,
    'limits': '원음, 슬라이드와 실험 및 통계 원자료 미대조. 실제 발표일과 녹취의 불명확한 표현 미확인.',
    'status': '검사 통과',
}
(WORK / '검증 결과.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ['files', 'feedback_total', 'document_links_checked', 'source_paths_checked', 'status']}, ensure_ascii=False))
