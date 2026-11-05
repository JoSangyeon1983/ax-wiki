"""전환 전후 파일, 링크, 메타데이터와 본문 보존을 대조함."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote, urlsplit
import argparse, hashlib, importlib.util, json, re, sys
from PIL import Image

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def front(t):
    if not t.startswith('---\n'):return {},''
    fm=t.split('---',2)[1]; fields={}
    for key,val in re.findall(r'^(\w+):([^\n]*(?:\n[ \t]+[^\n]*)*)',fm,re.M):fields[key]=val.strip().strip('"\'')
    return fields,fm

def resolve(root,source,value,wiki=False):
    value=unquote(value).split('|')[0].split('#')[0]
    if not value:return None
    if value.startswith('file:///'):return Path(value[8:])
    if urlsplit(value).scheme or value.startswith('//'):return None
    p=(root/value if wiki else source.parent/value).resolve()
    if wiki and not p.suffix:
        p=p.with_suffix('.md')
    return p

def links(root,hn):
    failures=[]; count=0
    for p in hn.wiki_files(root):
        t=p.read_text(encoding='utf-8-sig');d=hn.parse(p,t,root)
        if d.is_log:continue
        fm=front(t)[1]
        visible='\n'.join(line for _,line in d.visible)
        pairs=[]
        pairs += [(m,True) for m in re.findall(r'\[\[([^\]\n]+)\]\]',visible+'\n'+fm)]
        pairs += [(a or b,False) for a,b in re.findall(r'\]\((?:<([^>]+)>|([^\s)]+))\)',visible)]
        pairs += [(m,False) for m in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"',visible)]
        # Literal root paths in asset_files, outside wiki-link syntax.
        fields,_=front(t)
        pairs += [(m,True) for m in re.findall(r'"([^"\n]+)"',fields.get('asset_files',''))]
        for value,wiki in pairs:
            q=resolve(root,p,value,wiki)
            if q is None:continue
            count+=1
            if not q.is_file() and not q.is_dir():failures.append({'source':p.relative_to(root).as_posix(),'target':value})
            if q.is_relative_to(root/'99_보관소'):failures.append({'source':p.relative_to(root).as_posix(),'target':value,'archive':True})
    return count,failures

def normalized(t):
    if t.startswith('---\n'):t=t.split('---',2)[2]
    result=[]
    for line in t.splitlines():
        line=line.strip()
        if line.startswith('#'):
            line=re.sub(r'^(#+)\s+(?:\d+(?:\.\d+)*[.)]?|\(\d+\))\s+',r'\1 ',line)
        if line:result.append(line)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    root=args.root.resolve();work=Path(__file__).resolve().parent;oldroot=work.parents[1]
    record=json.loads((work/'파일별 이관 목록.json').read_text(encoding='utf-8'))
    data=json.loads((work/'기준 목록.json').read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('verify_hn',root/'00_시스템/03_도구/heading_numbers.py');hn=importlib.util.module_from_spec(spec);sys.modules[spec.name]=hn;spec.loader.exec_module(hn)
    errors=[];raw=0;png=0;status_count=0;semantic=0;tools=0
    for row in record['files']:
        if row.get('policy')=='archive_cache' and root!=oldroot:continue
        p=root/row['new']
        if not p.is_file():errors.append('Missing mapped file: '+row['new']);continue
        if row['new'].startswith('00_시스템/03_도구/') and p.suffix=='.py':
            source=next(x for x in data['latest_sources'] if x['path']==row['new'])
            if digest(p)!=source['sha256']:errors.append('Tool differs from frozen source: '+row['new'])
            tools+=1
        elif row.get('policy')=='agent_tool':
            if digest(p)!=row['source_at_seal_sha256']:errors.append('Migration tool changed after sealing')
        elif p.suffix!='.md':
            if digest(p)!=row['before_sha256']:errors.append('Changed raw file: '+row['new'])
            else:raw+=1
        if p.suffix=='.png':
            with Image.open(p) as im:im.verify()
            png+=1
    baseline={r['path']:r for r in data['files']}
    # Original text from immutable ZIP after cutover, or current original files before it.
    backup_path=data['backup'].replace('99_Archive/','99_보관소/',1) if (oldroot/'99_보관소').exists() else data['backup']
    import zipfile,runpy
    with zipfile.ZipFile(oldroot/backup_path/'현재 파일.zip') as z:
        migrator=runpy.run_path(str(work/'전환.py'))
        for key,(old,new) in record['documents'].items():
            t=z.read(old).decode('utf-8-sig').replace('\r\n','\n');u=(root/new).read_text(encoding='utf-8-sig')
            before,_=front(t);after,_=front(u)
            for field in ['created','status','source_check']:
                if field in before and before[field]!=after.get(field):errors.append('State changed: '+key+' '+field)
            status_count+=1
            expected=normalized(migrator['rewrite'](t,old,new,record['mapping']))
            actual=iter(normalized(u))
            if not all(any(x==line for x in actual) for line in expected):errors.append('Body preservation: '+key)
            else:semantic+=1
    for p in hn.wiki_files(root):
        t=p.read_text(encoding='utf-8-sig');f,fm=front(t)
        for required in ['title','type','created','updated']:
            if required not in f:errors.append('Metadata missing: '+str(p.relative_to(root))+' '+required)
        if len(re.findall(r'^\w+:',fm,re.M))!=len(f):errors.append('Duplicate metadata: '+str(p.relative_to(root)))
        allowed_targets={'01_프로젝트','02_기획 근거','03_기반 기획','04_상세 기획','05_참고 자료','06_자산','07_프로토타입','08_산출물'}
        if f.get('target_folder') and f['target_folder'] not in allowed_targets:errors.append('Invalid target_folder: '+str(p.relative_to(root)))
        if p.is_relative_to(root/'03_기반 기획') or p.is_relative_to(root/'04_상세 기획'):
            if f.get('approval_status')!='unverified' or f.get('status')!='draft':errors.append('Planning state: '+p.name)
            if f.get('sources')!='[]':errors.append('Unadopted planning sources: '+p.name)
        for item in re.findall(r'\[\[([^\]]+)\]\]',f.get('sources','')):
            source_top=item.split('/')[0]
            if source_top in ['00_시스템','99_보관소']:errors.append('Forbidden source: '+str(p.relative_to(root)))
    count,failed=links(root,hn)
    # Compare to failures in original active documents (not historical log bodies).
    if (oldroot/'00_System').exists():
        spec2=importlib.util.spec_from_file_location('original_hn',oldroot/'00_System/03_Tools/heading_numbers.py');oldhn=importlib.util.module_from_spec(spec2);sys.modules[spec2.name]=oldhn;spec2.loader.exec_module(oldhn)
        # Restrict catalog to original files so nested verification copies are excluded.
        oldhn.wiki_files=lambda _: [oldroot/r['path'] for r in data['files'] if r['path'].endswith('.md') and not r['path'].startswith('99_Archive/') and not any(x.startswith('.') for x in Path(r['path']).parts)]
        _,original=links(oldroot,oldhn)
        allowed={(record['mapping'].get(x['source'],x['source']),x['target']) for x in original}
    else:
        previous=json.loads((work/'검증 결과.json').read_text(encoding='utf-8'))
        allowed={(x['source'],x['target']) for x in previous['existing_link_failures']}
    existing=[x for x in failed if (x['source'],x['target']) in allowed]
    new=[x for x in failed if (x['source'],x['target']) not in allowed]
    errors += ['New link failure: '+json.dumps(x,ensure_ascii=False) for x in new]
    result={'root':str(root),'mapped_files':len(record['files']),'raw_files_unchanged':raw,'tools_from_frozen_snapshot':tools,'png_decoded':png,
            'document_states_checked':status_count,'bodies_preserved':semantic,'links_checked':count,
            'existing_link_failures':existing,'new_link_failures':new,'errors':errors}
    output=work/('이동 후 검증 결과.json' if root==oldroot else '검증 결과.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['existing_link_failures']},ensure_ascii=False,indent=2))
    print('Existing link failures:',len(existing))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
