"""Read-only inventory and evidence capture for the 2026-10-13 wiki audit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '00_System/03_Tools'))
import heading_numbers as hn

def save(name, value):
    (WORK / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def documents():
    return [p for p in hn.wiki_files(ROOT) if p.relative_to(ROOT).parts[0] != '99_Archive']

def inventory():
    result = []
    for p in documents():
        text = p.read_text(encoding='utf-8')
        doc = hn.parse(p, text, ROOT)
        issues = hn.numbered(doc, 'check')[1]
        result.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                       'frontmatter': ''.join(doc.lines[:doc.front_end]),
                       'headings': [{'line': h.line, 'level': h.level, 'text': h.text} for h in doc.headings],
                       'heading_issues': [vars(i) for i in issues]})
    return result

def capture():
    paths = documents()
    save('before.json', {'files': {p.relative_to(ROOT).as_posix(): {'text': p.read_text(encoding='utf-8'),
         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}})
    save('inventory_before.json', inventory())
    original = ROOT.parent / '00_KOCCA_AX_Wiki/assets'
    records = []
    for n in range(1, 6):
        p = original / f'{n}.hwpx'
        with zipfile.ZipFile(p) as z:
            xmls = [name for name in z.namelist() if re.fullmatch(r'Contents/section\d+\.xml', name)]
            chunks = []
            for name in xmls:
                tree = ET.fromstring(z.read(name))
                chunks.extend(''.join(el.itertext()) for el in tree.iter() if el.tag.endswith('}t'))
            full = '\n'.join(chunks)
            (WORK / f'original_{n}.txt').write_text(full, encoding='utf-8')
            records.append({'path': str(p), 'size': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                            'sections': xmls, 'text_characters': len(full)})
    transcript = ROOT.parent / '인력양성 컨소회의 회의록.txt'
    raw = transcript.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp949')
    (WORK / 'original_transcript.txt').write_text(text, encoding='utf-8')
    records.append({'path': str(transcript), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    save('external_sources.json', records)
    print(json.dumps({'documents': len(paths), 'headings': sum(len(x['headings']) for x in inventory()),
                      'heading_errors': sum(len(x['heading_issues']) for x in inventory()),
                      'sources': records}, ensure_ascii=False, indent=2))

def check(root=ROOT):
    # Scan actual Markdown destinations, Obsidian links and HTML image paths.
    # History is preserved as history, not interpreted as live documentation.
    files = [p for p in root.rglob('*') if p.is_file() and not any(x.startswith('.') or x in {'99_Archive','node_modules','__pycache__'} for x in p.relative_to(root).parts)]
    md = [p for p in files if p.suffix == '.md']
    catalog = {p.resolve(): hn.parse(p.resolve(), p.read_text(encoding='utf-8'), root.resolve()) for p in md}
    errors = []
    counts = {'links': 0, 'markdown_documents': len(md)}
    for p in md:
        if p.relative_to(root).parts[:2] == ('00_System','02_Logs') and p.name == 'log.md':
            continue
        text = p.read_text(encoding='utf-8')
        fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if re.match(r'^\s*```', line):
                fence = not fence
                continue
            if fence:
                continue
            clean = hn.remove_inline_code(line)
            destinations = hn.links(clean)
            destinations += re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', clean)
            for dest in destinations:
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', dest) or dest.startswith('//'):
                    continue
                from urllib.parse import unquote
                target, _, fragment = unquote(dest).partition('#')
                counts['links'] += 1
                if not target:
                    resolved = p.resolve()
                elif '/' in target or '\\' in target:
                    candidates = [p.parent / target, root / target]
                    resolved = next((x.resolve() for x in candidates if x.is_file()), None)
                    if resolved is None and not Path(target).suffix:
                        resolved = next((x.with_suffix('.md').resolve() for x in candidates if x.with_suffix('.md').is_file()), None)
                else:
                    candidates = [x.resolve() for x in files if x.name == target or (not Path(target).suffix and x.stem == target and x.suffix == '.md')]
                    resolved = candidates[0] if len(candidates) == 1 else None
                if resolved is None:
                    errors.append({'path':p.relative_to(root).as_posix(),'line':number,'destination':dest,'issue':'missing_or_ambiguous'})
                elif fragment and resolved in catalog and not fragment.startswith('^') and len(hn.matching_headings(catalog[resolved], fragment)) != 1:
                    errors.append({'path':p.relative_to(root).as_posix(),'line':number,'destination':dest,'issue':'heading_missing_or_ambiguous'})
    return {'counts': counts, 'errors': errors}

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['capture']:
        capture()
        result = check()
        save('links_before.json', result)
        print(json.dumps({'link_counts': result['counts'], 'link_errors':len(result['errors'])}, ensure_ascii=False))
    else:
        result = check()
        save('links_after.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
