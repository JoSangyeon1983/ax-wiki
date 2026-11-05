"""Current wiki checks. No external source conversion or source document writes."""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '00_System/03_Tools'))
import heading_numbers as hn

def files():
    return [p for p in hn.wiki_files(ROOT) if '99_Archive' not in p.relative_to(ROOT).parts and '.recheck_stage' not in p.parts]

def save(name, data):
    (WORK / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def snapshot():
    save('recheck_before.json', {str(p.relative_to(ROOT).as_posix()): {'text': p.read_text(encoding='utf-8'), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files()})

def check():
    docs = files()
    catalog = {p.resolve(): hn.parse(p, p.read_text(encoding='utf-8'), ROOT) for p in docs}
    errors, exceptions, records = [], [], []
    link_count = 0
    for p in docs:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding='utf-8')
        fm = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
        fields = dict(re.findall(r'^([\w_]+):[ \t]*(.*)$', fm[1], re.M)) if fm else {}
        kind = fields.get('type', '')
        required = ['title', 'type', 'created', 'updated']
        if kind in {'reference','synthesis','article','asset','prototype'}:
            required += ['status','sources']
        if kind == 'reference': required += ['source_check']
        if kind == 'asset': required += ['asset_files']
        for name in required:
            if name not in fields: errors.append([rel, 'missing_field', name])
        for name in ['created','updated']:
            if name in fields and not re.fullmatch(r'"\d{4}-\d{2}-\d{2}"', fields[name]): errors.append([rel, 'date_format', name])
        if kind in {'reference','synthesis','article','asset','prototype'} and fields.get('title','').strip('"') != p.stem:
            errors.append([rel, 'title_filename'])
        sources_match = re.search(r'^sources:[ \t]*(.*?)(?=^\w|\Z)', fm[1], re.M|re.S) if fm else None
        sources = re.findall(r'\[\[([^\]]+)\]\]', sources_match[1]) if sources_match else []
        allowed = {'synthesis': ['01_References'], 'article': ['01_References','02_Syntheses','03_Articles'], 'asset': ['01_References','02_Syntheses','03_Articles'], 'prototype': ['01_References','02_Syntheses','03_Articles','04_Assets']}
        for src in sources:
            target = ROOT / (src + ('' if Path(src).suffix else '.md'))
            if not target.is_file(): errors.append([rel,'source_missing',src])
            elif kind in allowed:
                if src.split('/')[0] not in allowed[kind]: errors.append([rel,'source_layer',src])
                if kind == 'article' and src.startswith('03_Articles/') and 'status: confirmed' not in target.read_text(encoding='utf-8'): errors.append([rel,'draft_article_source',src])
        legacy = rel == '00_System/02_Logs/log.md'
        if legacy: exceptions.append([rel,'historical body and paths retained'])
        fence = False
        for number, line in enumerate(text.splitlines(),1):
            if re.match(r'^\s*```',line): fence = not fence; continue
            if fence or legacy: continue
            clean = hn.remove_inline_code(line)
            wiki = re.findall(r'!?\[\[([^\]]+)\]\]',clean)
            ordinary = re.sub(r'!?\[\[[^\]]+\]\]','',clean)
            destinations = [(x.split('|')[0],True) for x in wiki]
            destinations += [(x,False) for x in hn.links(ordinary)]
            destinations += [(x,False) for x in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"',ordinary)]
            for dest, is_wiki in destinations:
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',dest) or dest.startswith('//'): continue
                link_count += 1
                path, _, fragment = unquote(dest).partition('#')
                if not path: target = p
                elif is_wiki:
                    candidates = [ROOT/path,p.parent/path]
                    if not Path(path).suffix: candidates += [x.with_suffix('.md') for x in candidates]
                    target = next((x.resolve() for x in candidates if x.is_file()), None)
                else: target = (p.parent/path).resolve()
                if target is None or not target.is_file(): errors.append([rel,number,'link_missing',dest]); continue
                if target.is_relative_to(ROOT/'99_Archive'): errors.append([rel,number,'archive_link',dest])
                if fragment and target in catalog and not fragment.startswith('^') and len(hn.matching_headings(catalog[target],fragment)) != 1: errors.append([rel,number,'anchor',dest])
                if not is_wiki and '%' in dest and re.search(r'%[0-9a-fA-F]{2}',dest): errors.append([rel,number,'encoded_internal_link',dest])
        records.append({'path':rel, 'type':kind, 'status':fields.get('status'), 'source_check':fields.get('source_check')})
    resource_count = 0
    for rel in ['04_Assets/01_Images/이관 이미지 관리 기록.md','01_References/01_CaveBall/CaveBall 클라이언트 코드 원자료.md']:
        p = ROOT/rel
        for line in p.read_text(encoding='utf-8').splitlines():
            match = re.search(r'\]\(<([^>]+)>\).*?`([a-f0-9]{64})`',line)
            if not match: continue
            resource_count += 1
            target = p.parent/match[1]
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=match[2]: errors.append([rel,'resource_hash',match[1]])
            elif target.suffix == '.png':
                data = target.read_bytes()
                size = re.search(r'(\d+) × (\d+)',line)
                if data[:8] != b'\x89PNG\r\n\x1a\n' or (size and struct.unpack('>II',data[16:24]) != tuple(map(int,size.groups()))): errors.append([rel,'png_size',match[1]])
    args = [sys.executable,'-X','utf8',str(ROOT/'00_System/03_Tools/heading_numbers.py'),'check'] + [str(p.relative_to(ROOT)) for p in docs]
    proc = subprocess.run(args,cwd=ROOT,capture_output=True,encoding='utf-8')
    result = {'scope':'Active wiki; archive and historical log body excluded; HWPX comparison not repeated', 'documents':len(docs), 'links':link_count, 'resource_hashes':resource_count, 'errors':errors, 'exceptions':exceptions, 'heading_check':{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}, 'metadata':records}
    save('recheck_validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='metadata'},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    snapshot() if sys.argv[1:] == ['capture'] else check()
