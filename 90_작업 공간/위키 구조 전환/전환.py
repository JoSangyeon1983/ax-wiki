"""AX 위키 구조 전환의 파일 보존, 사본 준비와 검증 도구."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, os, re, shutil, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
LATEST = ROOT.parents[1] / '30_무형문화유산/01_Wiki'
STAGE = WORK / '검증용 위키'
NOW = lambda: datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
DAY = '2026-11-04'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8', newline='\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def system_doc(title, body):
    return f'---\ntitle: "{title}"\ntype: system\ncreated: "{DAY}"\nupdated: "{DAY}"\n---\n\n'+body

def baseline():
    dest = WORK / '기준 목록.json'
    if dest.exists():
        raise RuntimeError('기준 목록이 이미 존재하므로 덮어쓰지 않음')
    run = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / '99_Archive/위키 구조 전환 백업' / run
    backup.mkdir(parents=True, exist_ok=False)
    paths=[]
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != '.git' and not (Path(base)/d).is_relative_to(backup.parent)]
        for name in files:
            p=Path(base)/name
            if p.is_symlink(): raise RuntimeError('심볼릭 링크 별도 검토 필요: '+str(p))
            paths.append(p)
    tracked=set(git('ls-files','-z').decode('utf-8').strip('\0').split('\0'))
    ignored=set(git('ls-files','--others','--ignored','--exclude-standard','-z').decode('utf-8').strip('\0').split('\0'))
    records=[]
    with zipfile.ZipFile(backup/'현재 파일.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):
            rel=p.relative_to(ROOT).as_posix()
            records.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p),
                            'git':'tracked' if rel in tracked else 'ignored' if rel in ignored else 'untracked'})
            z.write(p,rel)
    for name,args in {'git 상태.bin':('status','--porcelain=v1','-z'),
                      '작업 트리 변경.patch':('diff','--binary'),
                      '스테이지 변경.patch':('diff','--cached','--binary'),
                      '추적 목록.bin':('ls-files','--stage','-z'),
                      'HEAD.txt':('rev-parse','HEAD'),
                      '참조.txt':('show-ref',)}.items():
        (backup/name).write_bytes(git(*args))
    for name in ['index','HEAD','config','packed-refs','info/exclude']:
        p=ROOT/'.git'/name
        if p.is_file():
            q=backup/'git 상태 사본'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    with zipfile.ZipFile(backup/'현재 파일.zip') as z:
        for row in records:
            data=z.read(row['path'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    sample=next(row for row in records if row['path'].endswith('.cs'))
    with zipfile.ZipFile(backup/'현재 파일.zip') as z:
        recovered=backup/'복구 시험'/sample['path']
        recovered.parent.mkdir(parents=True,exist_ok=True);recovered.write_bytes(z.read(sample['path']))
        assert sha(recovered)==sample['sha256']
    sources=[]
    requested=[LATEST/'AGENTS.md', LATEST/'.gitignore', *sorted((LATEST/'00_시스템/01_규정').glob('*.md')),
               *sorted((LATEST/'00_시스템/03_도구').glob('*.py'))]
    for p in requested:
        rel=p.relative_to(LATEST).as_posix();q=backup/'참고 규정'/rel
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        sources.append({'path':rel,'sha256':sha(p),'snapshot':q.relative_to(ROOT).as_posix()})
    data={'captured_at':NOW(),'root':str(ROOT),'backup':backup.relative_to(ROOT).as_posix(),
          'zip_sha256':sha(backup/'현재 파일.zip'),'files':records,'latest_sources':sources,
          'verified':len(records),'restore_sample':sample['path']}
    save(dest,data);save(backup/'기준 목록.json',data)
    print(json.dumps({'files':len(records),'bytes':sum(x['bytes'] for x in records),
                      'backup':data['backup'],'latest_sources':len(sources),'restore_sample':sample['path']},ensure_ascii=False))

def mark(stage, message):
    p=WORK/'AX 위키 구조 전환 실행 계획.md'; t=p.read_text(encoding='utf-8')
    t=t.replace(f'- [ ] {stage}-',f'- [x] {stage}-')
    t=re.sub(rf'(^\| {stage} \|[^\n]*?\| )미착수 \| 미완료 \|',rf'\g<1>완료 | {DAY} |',t,flags=re.M)
    t=re.sub(r'^- 현재 요청 범위:.*$', '- 현재 요청 범위: 사용자의 시작 지시에 따라 S1~S6 구조 전환을 순차 실행함. 기획 내용의 신규 채택과 승인은 별개임.',t,flags=re.M)
    t=re.sub(r'^- 현재 단계:.*$', f'- 현재 단계: {stage} 완료. {message}',t,flags=re.M)
    t=re.sub(r'^- 다음 작업:.*$', '- 다음 작업: 단계 현황의 첫 미완료 항목부터 진행함.',t,flags=re.M)
    row=f'| {NOW()[:16].replace("T"," ")} | {stage} | {message} | 실제 결과는 같은 폴더의 검증 및 대조 기록에서 확인함 | 다음 미완료 단계 |\n'
    t=t.replace('# 8 운영 참고 문서', row+'\n# 8 운영 참고 문서')
    write(p,t)

def mapping():
    baseline=json.loads((WORK/'기준 목록.json').read_text(encoding='utf-8'))
    result={}
    docs={}
    plan=(WORK/'AX 위키 구조 전환 실행 계획.md').read_text(encoding='utf-8')
    for key,old,new in re.findall(r'^\| (D\d+) \| `([^`]+)` \| `([^`]+)`',plan,re.M):
        if int(key[1:])<=5: old='01_References/00_프로젝트/02_연구개발계획서/'+old
        if key=='D16':new='90_작업 공간/중간발표 1020 피드백/현재 정본/중간발표 1020.md'
        docs[key]=(old,new)
    assert len(docs)==18
    explicit=dict(docs.values())
    for row in baseline['files']:
        old=row['path']; parts=old.split('/'); new=old
        if old in explicit:new=explicit[old]
        elif old.startswith('00_System/'):
            new=old.replace('00_System/00_Index/Index.md','00_시스템/00_색인/위키 색인.md').replace('00_System/01_Rules/','00_시스템/01_규정/').replace('00_System/02_Logs/','00_시스템/02_작업 기록/').replace('00_System/03_Tools/','00_시스템/03_도구/')
            new=new.replace('문서 작성 규칙.md','작성 규칙.md').replace('위키 작업 절차.md','작업 절차.md')
        elif old.startswith('01_References/01_CaveBall/'):
            new=old.replace('01_References/01_CaveBall/','01_프로젝트/개발 자료/CaveBall/')
        elif old.startswith('01_References/90_회의록/원문/중간점검_1013/'):
            new='90_작업 공간/회의록/2026-10-13 실무 미팅/원문/'+parts[-1]
        elif old.startswith('01_References/중간발표 1020/'):
            new=old.replace('01_References/중간발표 1020/','01_프로젝트/회의 및 검토/중간발표 1020/')
        elif old.startswith('04_Assets/01_Images/'):
            new=old.replace('04_Assets/01_Images/','06_자산/이미지/')
        elif old.startswith('04_Assets/02_Records/'):
            new='90_작업 공간/중간발표 1020 피드백/제공 원본/'+parts[-1]
        elif old.startswith('90_Workspace/'):
            new=old.replace('90_Workspace/','90_작업 공간/',1)
        elif old.startswith('99_Archive/'):
            new=old.replace('99_Archive/','99_보관소/',1)
        elif parts[0] in ['01_References','02_Syntheses','03_Articles','05_Prototypes'] and parts[-1]=='.gitkeep':
            new={'01_References':'01_프로젝트','02_Syntheses':'02_기획 근거','03_Articles':'03_기반 기획','05_Prototypes':'07_프로토타입'}[parts[0]]+'/.gitkeep'
        elif old=='04_Assets/.gitkeep':new='06_자산/.gitkeep'
        elif old=='04_Assets/00_Localization/.gitkeep':new='90_작업 공간/위키 구조 전환/이전 빈 폴더 표식/00_Localization.gitkeep'
        if new.startswith(('01_References/','02_Syntheses/','03_Articles/','04_Assets/','05_Prototypes/')):
            raise RuntimeError('Unclassified: '+old)
        result[old]=new
    assert len(set(result.values()))==len(result)
    return baseline,result,docs

def rewrite(text, old, new, mapping):
    """Resolve link destinations in the original root before moving them."""
    from urllib.parse import unquote, urlsplit
    def target(value, wiki=False):
        value=unquote(value); file,sep,frag=value.partition('#')
        if not file or urlsplit(file).scheme or file.startswith('//'):return value
        base=ROOT if wiki else (ROOT/old).parent
        p=(base/file).resolve()
        if wiki and not p.suffix:
            candidate=p.with_suffix('.md')
            try:known=candidate.relative_to(ROOT).as_posix() in mapping
            except ValueError:known=False
            if known or candidate.is_file():p=candidate
        try:rel=p.relative_to(ROOT).as_posix()
        except ValueError:return value
        dest=mapping.get(rel)
        if dest is None:return value
        if wiki:
            if not Path(file).suffix and dest.endswith('.md'):dest=dest[:-3]
        else:dest=os.path.relpath(ROOT/dest,(ROOT/new).parent).replace('\\','/')
        return dest+sep+frag
    text=re.sub(r'\[\[([^\]\n]+)\]\]',lambda m:'[['+target(m[1].split('|')[0],True)+('|' +m[1].split('|',1)[1] if '|' in m[1] else '')+']]',text)
    text=re.sub(r'(\]\()<([^>]+)>(\))',lambda m:m[1]+'<'+target(m[2])+'>'+m[3],text)
    text=re.sub(r'(\]\()([^\s<>)]*)(\))',lambda m:m[1]+('<'+target(m[2])+'>' if ' ' in target(m[2]) else target(m[2]))+m[3],text)
    text=re.sub(r'(<img\b[^>]*?\bsrc=")([^"]+)(")',lambda m:m[1]+target(m[2])+m[3],text)
    # Only machine-readable resource paths, not historical prose or external paths.
    for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):
        text=text.replace('"'+a+'"','"'+b+'"')
    return text

def set_field(text,key,value):
    fm,body=text.split('---',2)[1:]
    pattern=rf'^{key}:[^\n]*(?:\n(?:  .*)?)*'
    # YAML list continuation belongs only to the selected field.
    pattern=rf'^{key}:[^\n]*(?:\n[ \t]+[^\n]*)*'
    line=key+': '+value
    if re.search(pattern,fm,re.M):fm=re.sub(pattern,line,fm,flags=re.M)
    else:fm=fm.rstrip()+'\n'+line+'\n'
    return '---'+fm+'---'+body

def prepare():
    data,mp,docs=mapping()
    if STAGE.exists():raise RuntimeError('검증용 사본이 이미 존재함')
    STAGE.mkdir(parents=True)
    records=[]
    for row in data['files']:
        old=row['path'];new=mp[old]
        if old.startswith('99_Archive/') or old.startswith('.obsidian/') or old in ['AGENTS.md','.gitignore']:continue
        p=ROOT/old;q=STAGE/new
        q.parent.mkdir(parents=True,exist_ok=True)
        text=None
        if p.suffix=='.md' and not old.startswith('00_System/02_Logs/') and not any(x.startswith('.') for x in Path(old).parts):
            text=rewrite(p.read_text(encoding='utf-8-sig'),old,new,mp)
            if '---' in text[:5]:text=set_field(text,'updated','"'+DAY+'"')
            for key,(source,dest) in docs.items():
                if old!=source:continue
                if key in ['D01','D02','D03','D04','D05','D08','D09','D11']:
                    text=set_field(text,'title',json.dumps(Path(new).stem,ensure_ascii=False))
                if key=='D11':
                    text=set_field(text,'type','reference');text=set_field(text,'source_check','partial')
                    text=set_field(text,'sources','\n  - "사용자 제공 클로바 노트 TXT: 인력양성_1013_클로바노트.txt, 2026-10-13 실무 미팅"\n  - "사용자 제공 수기 TXT: 인력양성 1013_직접 작성.txt, 2026-10-13 실무 미팅"\n  - "사용자 정정: 2026-10-13 목록 전달일, 도구명과 녹음 시각 등의 확인"')
                    raw=mp[docs['D08'][0]];trans=mp[docs['D09'][0]]
                    footer='\n# 원자료와 검증 범위\n\n- 원자료: 사용자 제공 TXT 2개와 당시 사용자 정정임. 원음 미대조, 불명확한 용어와 발언의 기존 한계 유지함.\n'
                    for label,link in [('원자료 정보',raw),('교정 녹취록',trans)]:footer+=f'- 교정과 검증 자료: [{label}](<{os.path.relpath(ROOT/link,(ROOT/new).parent).replace(chr(92),"/")}>). 기획 근거 채택과 구분함.\n'
                    footer+='- 이번 검토: 보존된 회의록의 역할, 경로와 원자료 식별만 정비함. 원문 발언의 재대조나 새로운 결정 판정은 수행하지 않음.\n'
                    text+=footer
                if key in ['D14','D15']:
                    fm=text.split('---',2)[1]
                    src=re.search(r'^sources:[^\n]*(?:\n[ \t]+[^\n]*)*',fm,re.M)[0].replace('sources:','related_documents:',1)
                    text=set_field(text,'sources','[]');text=set_field(text,'related_documents',src.split(':',1)[1].rstrip())
                    text=set_field(text,'planning_role','detail' if key=='D14' else 'foundation')
                    text=set_field(text,'approval_status','unverified')
                    note='\n> 구조 전환 기록: 아래 기존 본문과 참고 인용은 이전 초안의 검토 맥락으로 보존함. `related_documents`는 기준 후보와 이전 분석의 추적용 연결이며 기획 적용 승인을 의미하지 않음. 채택된 기획 기준과 콘셉트 승인은 미확인임.\n'
                    a,b,c=text.split('---',2);text=a+'---'+b+'---'+note+c
                if key=='D16':
                    text=set_field(text,'target_folder','08_산출물')
                    text+= '\n<!-- 구조 전환: 현재 편집 기준인 피드백 초안. 같은 이름의 과거 작업본과 구분하여 보존함. 전달용 파일은 아직 별도로 작성하지 않았음. -->\n'
                if key=='D17':
                    text+='\n<!-- 구조 전환: 사용자 교체본의 본문 보존. 임시 이미지 10개 실물 부재는 이전부터의 결손이며 복구 미완료임. 전달용 정본 확정은 별도임. -->\n'
                if key=='D10':
                    text+='\n<!-- 구조 전환: 최초 제공 위치와 05번 파일 부재는 2026-10-23 당시 기록임. 2026-11-04 전환 시 기존 제공 폴더의 15개는 작업 공간의 제공 원본에 보존함. 05번은 기존 14개 분석 범위에 추가하지 않음. -->\n'
            # Keep temporary work artifacts distinct from adopted planning sources.
            if new.startswith('90_작업 공간/') and 'target_folder: 02_Syntheses' in text:
                text=text.replace('target_folder: 02_Syntheses','target_folder: 05_참고 자료')
            if new.startswith('90_작업 공간/') and 'target_folder: 03_Articles' in text:
                text=text.replace('target_folder: 03_Articles','target_folder: 08_산출물')
            if text is not None:write(q,text)
        if text is None:shutil.copy2(p,q)
        records.append({'old':old,'new':new,'reason':next((k for k,(a,b) in docs.items() if a==old),'동봉 파일 또는 운영 및 작업 자료'),
                        'before_sha256':sha(p),'after_sha256':sha(q),'bytes_preserved':sha(p)==sha(q)})
    # Copy the frozen rule/tool snapshot; never a changing live source.
    backup=ROOT/data['backup']
    for row in data['latest_sources']:
        if row['path']=='.gitignore' or '번역 검수' in row['path']:continue
        source=ROOT/row['snapshot'];dest=STAGE/row['path']
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    for folder in ['02_기획 근거','07_프로토타입','08_산출물']:
        (STAGE/folder).mkdir(exist_ok=True)
        (STAGE/folder/'.gitkeep').touch(exist_ok=True)
    write(STAGE/'.gitignore',(ROOT/'.gitignore').read_text(encoding='utf-8').replace('/99_Archive/','/99_보관소/')+'\n# Temporary verification work\n/90_작업 공간/위키 구조 전환/검증용 위키/\n')
    save(WORK/'파일별 이관 목록.json',{'prepared_at':NOW(),'files':records,'mapping':mp,'documents':docs})
    print(json.dumps({'staged_files':len(records),'documents':len(docs),'stage':str(STAGE)},ensure_ascii=False))

def seal():
    """Freeze the reviewed stage; stage files are not regenerated here."""
    manifest=WORK/'파일별 이관 목록.json';data=json.loads(manifest.read_text(encoding='utf-8'))
    for row in data['files']:
        p=STAGE/row['new']
        if p.is_file():
            row['after_sha256']=sha(p)
            if p.suffix=='.md':
                old=(ROOT/row['old']).read_text(encoding='utf-8-sig');new=p.read_text(encoding='utf-8-sig')
                fields=lambda t:dict(re.findall(r'^(type|status|source_check|approval_status|planning_role|created):\s*([^\n]*)',t.split('---',2)[1],re.M))
                row['before_state']=fields(old);row['after_state']=fields(new)
    data['sealed_at']=NOW();save(manifest,data)
    # Synchronize agent-created records after stage review.
    for p in WORK.iterdir():
        if not p.is_file():continue
        target=STAGE/'90_작업 공간/위키 구조 전환'/p.name
        if p.suffix=='.md':
            write(target,rewrite(p.read_text(encoding='utf-8'),p.relative_to(ROOT).as_posix(),target.relative_to(STAGE).as_posix(),data['mapping']))
        else:
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    for row in data['files']:
        p=STAGE/row['new']
        if p.is_file():row['after_sha256']=sha(p)
        if row['old']=='90_Workspace/위키 구조 전환/전환.py':
            row['policy']='agent_tool';row['source_at_seal_sha256']=sha(WORK/'전환.py')
    save(manifest,data)
    shutil.copy2(manifest,STAGE/'90_작업 공간/위키 구조 전환/파일별 이관 목록.json')
    rows=[]
    for p in STAGE.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts:continue
        rows.append({'path':p.relative_to(STAGE).as_posix(),'sha256':sha(p)})
    save(WORK/'적용 목록.json',{'sealed_at':NOW(),'files':rows})
    print('SEALED',len(rows))

def apply():
    """Apply reviewed files while retaining original active directories locally."""
    if not STAGE.is_dir():raise RuntimeError('검증 사본 없음')
    validation=json.loads((WORK/'검증 결과.json').read_text(encoding='utf-8'))
    if validation['errors']:raise RuntimeError('검증 미통과')
    base=json.loads((WORK/'기준 목록.json').read_text(encoding='utf-8'))
    agent_files={'90_Workspace/위키 구조 전환/전환.py','90_Workspace/위키 구조 전환/AX 위키 구조 전환 실행 계획.md'}
    for row in base['files']:
        if row['path'] in agent_files or '__pycache__' in Path(row['path']).parts:continue
        p=ROOT/row['path']
        if not p.is_file() or sha(p)!=row['sha256']:raise RuntimeError('기준 이후 원본 변경: '+row['path'])
    staged=json.loads((WORK/'적용 목록.json').read_text(encoding='utf-8'))['files']
    for row in staged:
        p=STAGE/row['path']
        if sha(p)!=row['sha256']:raise RuntimeError('검증 사본 변경: '+row['path'])
    moves=[]
    def move(source,dest):
        a=source.resolve();b=dest.resolve()
        if not a.is_relative_to(ROOT) or not b.is_relative_to(ROOT) or a==ROOT or b==ROOT:
            raise RuntimeError('작업 루트 경계 위반')
        if dest.exists():raise RuntimeError('이동 대상 충돌: '+str(dest))
        dest.parent.mkdir(parents=True,exist_ok=True);source.rename(dest)
        moves.append({'old':str(a),'new':str(b)})
    move(ROOT/'99_Archive',ROOT/'99_보관소')
    history=ROOT/'99_보관소/종료 작업/구조 전환 전 활성 폴더'
    for name in ['00_System','01_References','02_Syntheses','03_Articles','04_Assets','05_Prototypes']:
        move(ROOT/name,history/name)
    move(ROOT/'90_Workspace',ROOT/'90_작업 공간')
    work=ROOT/'90_작업 공간/위키 구조 전환';stage=work/'검증용 위키'
    for row in staged:
        source=stage/row['path'];dest=ROOT/row['path']
        if not dest.resolve().is_relative_to(ROOT):raise RuntimeError('복사 대상 경계 위반')
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        if sha(dest)!=row['sha256']:raise RuntimeError('적용 후 해시 불일치: '+row['path'])
    for name in ['02_기획 근거','07_프로토타입','08_산출물']:(ROOT/name).mkdir(exist_ok=True)
    save(work/'적용 기록.json',{'applied_at':NOW(),'moves':moves,'files_verified':len(staged)})
    print(json.dumps({'applied_files':len(staged),'retained_directories':len(moves),'new_work':str(work)},ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='baseline': baseline()
    elif sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='seal':seal()
    elif sys.argv[1]=='apply':apply()
