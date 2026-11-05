from pathlib import Path
import hashlib
import json
import shutil
import re

wiki = Path.cwd()
work = wiki / '90_작업 공간/CaveBall 콘셉트 작성'
record = json.loads((work / '최초 근거 추출.json').read_text(encoding='utf-8'))
project = Path(record['project'])
snapshot = wiki / '01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료'
snapshot.mkdir(parents=True, exist_ok=True)
files = []
for relative in dict.fromkeys(item['path'] for item in record['units']):
    source = project / relative
    target = snapshot / '원문' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = source.read_bytes()
    if target.exists() and target.read_bytes() != source_bytes:
        raise RuntimeError(f'Existing snapshot differs: {target}')
    if not target.exists():
        shutil.copy2(source, target)
    digest = hashlib.sha256(source_bytes).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    files.append({'path': relative, 'sha256': digest, 'bytes': len(source_bytes)})
module_paths = re.findall(r'^\s*path = (.+)$', (project / '.gitmodules').read_text(encoding='utf-8'), re.M)
manifest = {'source_project': record['project'], 'commit': record['commit'], 'date': record['created'], 'files': files,
            'submodules': [{'path': p, 'local_file_count': sum(f.is_file() for f in (project / p).rglob('*'))} for p in module_paths],
            'verification': 'Listed source and snapshot byte hashes match. Unity execution was not performed.'}
(snapshot / '원문 파일 목록.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
old = wiki / '03_기반 기획/콘셉트/Cave Super Ball 기획서 초안.md'
backup = work / 'Cave Super Ball 기존 초안.txt'
if not backup.exists():
    shutil.copy2(old, backup)
print(json.dumps({'snapshots': len(files), 'bytes': sum(x['bytes'] for x in files), 'source_commit': record['commit']}, ensure_ascii=False))
