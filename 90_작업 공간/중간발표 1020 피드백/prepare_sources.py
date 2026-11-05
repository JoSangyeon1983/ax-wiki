from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / '04_Assets/02_Records'
STAGE = WORK / '등록안/원문'
STAGE.mkdir(parents=True, exist_ok=True)

files = sorted(SOURCE.glob('*.txt'))
manifest = []
units = []
for path in files:
    raw = path.read_bytes()
    content = raw.decode('utf-8-sig')
    lines = content.splitlines()
    sha = hashlib.sha256(raw).hexdigest()
    staged = STAGE / path.name
    if staged.exists() and staged.read_bytes() != raw:
        raise RuntimeError(f'기존 등록안과 원문 불일치: {path.name}')
    staged.write_bytes(raw)
    speaker = stamp = None
    local_count = 0
    for number, line in enumerate(lines, 1):
        found = re.fullmatch(r'(.+?)\s+(\d{2}:\d{2})', line.strip())
        if found:
            speaker, stamp = found.groups()
            continue
        if not speaker or not line.strip() or line.strip() == 'clovanote.naver.com':
            continue
        local_count += 1
        units.append({
            'id': f'{path.name[:2]}-U{local_count:04d}',
            'file': path.name,
            'line': number,
            'speaker': speaker,
            'timestamp': stamp,
            'text': line,
        })
    manifest.append({
        'file': path.name,
        'original': path.relative_to(ROOT).as_posix(),
        'reference': f'01_References/중간발표 1020/원문/{path.name}',
        'sha256': sha,
        'bytes': len(raw),
        'lines': len(lines),
        'header': lines[:3],
        'units': local_count,
        'first_timestamp': next(u['timestamp'] for u in units if u['file'] == path.name),
        'last_timestamp': next(u['timestamp'] for u in reversed(units) if u['file'] == path.name),
    })

(WORK / '원문 목록.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(WORK / '최초 추출표.json').write_text(json.dumps({
    'scope': 'TXT 14개를 각 파일 첫 발언부터 마지막 발언까지 전체 읽음. 헤더와 사이트 주소는 별도 메타데이터로 보존함.',
    'segmentation': '발언자와 시각을 식별하고, 원문 줄바꿈의 문장 또는 의미 단위를 개수 제한 없이 추출함. 원문을 교정하지 않음.',
    'comparison': '발표별 개별 녹취 분석임. 동일 발표에 대한 복수 녹취 대조나 원음 검증은 수행하지 않음.',
    'units': units,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'files': len(files), 'units': len(units), 'per_file': [{k: m[k] for k in ('file', 'units', 'first_timestamp', 'last_timestamp')} for m in manifest]}, ensure_ascii=False, indent=2))
