"""Prepare reviewable corrections in Workspace; never edit external inputs."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
STAGE=WORK/'.staging'
DATE='2026-10-13'
sys.path.insert(0,str(ROOT/'00_System/03_Tools'))
import heading_numbers as hn

before=json.loads((WORK/'before.json').read_text(encoding='utf-8'))['files']
texts={p:v['text'] for p,v in before.items()}
changed=set()
events=[]
source_dir=ROOT.parent/'00_KOCCA_AX_Wiki/assets'
code_dir=ROOT.parent/'02_Client/00_Caveball/Assets/Scripts/CaveBall'
ref_paths=sorted(p for p in texts if p.startswith('01_References/00_프로젝트/02_연구개발계획서/'))
analysis='02_Syntheses/CaveBall 클라이언트 코드 구조 분석.md'
flow='02_Syntheses/CaveBall 계층형 플로우.md'
plan='03_Articles/기획서/Cave Super Ball 기획서.md'
draft='03_Articles/기획서/Cave Super Ball 기획서 초안.md'
meeting='01_References/90_회의록/2026-07-15 컨소시엄 킥오프 회의록.md'
extract='90_Workspace/CaveSuperBall/Cave Super Ball 개요 근거 추출.md'
code_ref='01_References/01_CaveBall/CaveBall 클라이언트 코드 원자료.md'
asset_ref='04_Assets/01_Images/이관 이미지 관리 기록.md'

def write_stage(p,text):
    dest=STAGE/p
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(text,encoding='utf-8')

def front(text):
    match=re.match(r'^---\n(.*?)\n---\n',text,re.S)
    assert match
    return match.group(1),text[match.end():]

def yaml_list(name,items):
    return name+':'+ ('\n'+ '\n'.join('  - '+json.dumps(i,ensure_ascii=False) for i in items) if items else ' []')

def metadata(p,kind,sources=None,extra=None):
    fm,body=front(texts[p])
    fields=dict(re.findall(r'^([a-z_]+): *(.*)$',fm,re.M))
    created=re.match(r'\d{4}-\d{2}-\d{2}',fields['created']).group(0)
    lines=['title: '+json.dumps(Path(p).stem,ensure_ascii=False), 'type: '+kind,
           'created: '+json.dumps(created),'updated: '+json.dumps(DATE)]
    if kind!='system':
        lines+=['status: '+fields.get('status','draft')]
    if 'tags' in fields:
        lines+=['tags: '+fields['tags'].replace('reference, locked,','reference,')]
    if sources is not None:
        lines+=[yaml_list('sources',sources)]
    if extra:
        lines+=extra
    if 'revision_note' in fields:
        lines+=['revision_note: '+fields['revision_note']]
    texts[p]='---\n'+'\n'.join(lines)+'\n---\n'+body

def rootlink(p):
    return '[['+p.removesuffix('.md')+']]'

checks=[
    '기술 현황의 Genie 표기와 출력 수치, 인력양성 인원표 및 그림 03의 표시값 일부 대조함. 특허, 시장 조사 원보고서와 교수별 실적의 사실성은 미확인임.',
    '최종 성능지표 표, 연차별 셀빅 목표와 콘텐츠 개발 범위 일부 대조함. 전체 표와 원문 이미지 34개의 완전성은 미확인임.',
    '기관별 역할과 월별 추진일정 표 5~7의 월 셀을 XML 셀 주소와 borderFill 값으로 대조함. 다른 계획 문서와의 일정 충돌은 남아 있음.',
    '3개 연차 마일스톤의 주요 일정과 원문 오류 표기 일부 대조함. 역전된 연도와 미완성 셀은 원자료 표기로 보존함.',
    '기술, 콘텐츠 활용 계획 및 사업화 전략의 일부 문구 대조함. 추가된 이미지 설명, 실제 계약과 매출 및 기관별 사업 실적은 미확인임.'
]
for n,p in enumerate(ref_paths,1):
    metadata(p,'reference',[str(source_dir/f'{n}.hwpx')],['source_check: partial'])
    fm,body=front(texts[p])
    body=re.sub(r'^# .*$', '# 원문 사본',body,count=1,flags=re.M)
    # Old chapter numbers are citation locations, not current wiki numbering.
    body=re.sub(r'^(##) [1-5]-\d+\.\s+(.*)$',r'\1 \2',body,flags=re.M)
    # Preserve the actual stage identifier when a title begins with a digit.
    body=re.sub(r'^### ([123]) 단계$',r'### \1단계',body,flags=re.M)
    if n==1:
        body=body.replace('# 원문 사본\n','# 원문 사본\n\n- 이미지 캡션은 이관 과정에서 작성된 시각 해석임. 이번 직접 대조한 그림 03의 표시값 외 캡션의 정확성은 미확인임.\n',1)
    if n==5:
        body=body.replace('> 시각 정보 요약','> 시각 해석, 미확인')
    body+='\n# 대조 범위와 한계\n\n- 2026-10-13 점검: '+checks[n-1]+'\n- 작성 경위: 다른 위키에서 이관한 HWPX 변환본임. 원문 텍스트, 변환 설명과 이미지 해석이 함께 포함되어 있음.\n- 과거 대조 이력은 이관 당시 기록임. 이번 점검의 전체 원문 검증 완료로 해석하지 않음.\n- 본문의 원문 장절 번호와 과거 행 번호는 이관 당시 기준임. 운영 헤더 번호와 구분함.\n'
    texts[p]='---\n'+fm+'\n---\n'+body

metadata(meeting,'reference',[str(ROOT.parent/'인력양성 컨소회의 회의록.txt')],['source_check: partial'])
texts[meeting]=texts[meeting].replace('- **일시**: 2026-07-15 (녹취록 헤더의 2026-07-16 10:17 표기는 녹취 기록 생성 시각)',
    '- **일시**: 이관본의 회의일은 2026-07-15임. 원녹취 헤더에는 `2026.07.16 목 오전 10:17`이 표시됨. 실제 회의일과 헤더 시각의 의미는 미확인임')
texts[meeting]=texts[meeting].replace('- **실시간 인터랙션 종류 4가지**:', '- **실시간 인터랙션 후보 4가지, 적용 연차 미확인**: 녹취 29:35의 검토 후보임. 1차년도 확정 목표 4종으로 해석하지 않음\n')
texts[meeting]+='\n# 대조 범위와 한계\n\n- 다른 위키에서 이관한 녹취 요약임. 셀빅의 상호작용 후보와 공인시험 연차 확인 발언을 원녹취 28:36~29:35 구간과 일부 대조함.\n- 회의일, 행정 규정, 인정 실적과 컨설팅 요구의 최종 확정 여부는 미확인임. 발언 요약을 현재 운영 규정으로 사용하지 않음.\n'

metadata(analysis,'synthesis',[rootlink(code_ref)])
texts[analysis]=texts[analysis].replace('## 1.2 분절 기준\n','## 1.2 분절 기준\n')
texts[analysis]=texts[analysis].replace('- **콘텐츠 생명주기**:', '### 생명주기와 게임 조정\n\n- **콘텐츠 생명주기**:',1)
texts[analysis]=texts[analysis].replace('- **상호작용 입력**:', '### 입력과 피드백\n\n- **상호작용 입력**:',1)
texts[analysis]=texts[analysis].replace('- **출력**:', '### 출력과 경기장\n\n- **출력**:',1)
texts[analysis]=texts[analysis].replace('- **공과 라운드**:', '### 게임과 입력\n\n- **공과 라운드**:',1)
texts[analysis]=texts[analysis].replace('- **피드백**: 벽돌 효과 풀', '### 피드백 설정\n\n- **피드백**: 벽돌 효과 풀',1)
texts[analysis]=texts[analysis].replace('- **최대 속도 보정 순서**:', '### 물리와 점수 경계\n\n- **최대 속도 보정 순서**:',1)
texts[analysis]=texts[analysis].replace('- **구독 해제 경로**:', '### 수명주기와 표시 경계\n\n- **구독 해제 경로**:',1)
texts[analysis]=texts[analysis].replace('- **색 변경음 호출 범위**:', '### 소리와 접촉 목록\n\n- **색 변경음 호출 범위**:',1)
texts[analysis]+='\n# 원자료 연결과 이번 대조 범위\n\n- 직접 근거는 '+rootlink(code_ref)+'의 원문 코드 사본임. 외부 코드 16개와 어셈블리 정의 1개를 해시 대조하여 보관함.\n- 이번 점검은 콘텐츠 초기화 실패 경로, `StartGame`의 공 존재 검사, 손 색 조건, 바닥의 메시지 수신과 프레임 갱신 분리, 벽돌 득점 및 라운드 점수 초기화를 정적으로 대조함.\n- 분석 당시의 전체 검토 이력을 이번 실행 검증으로 대체하지 않음. Unity 실행, 실제 설정, 센서와 프리팹 구성은 이번에도 미검증임.\n'

metadata(flow,'synthesis',[rootlink(code_ref)])
texts[flow]=texts[flow].replace('코드 근거와 정적 분석의 한계는 [[CaveBall 클라이언트 코드 구조 분석]]을 따름.',
    '직접 코드 근거는 '+rootlink(code_ref)+'임. [[CaveBall 클라이언트 코드 구조 분석]]은 관련 해설이며 이 문서의 독립 출처로 사용하지 않음.')
texts[flow]=texts[flow].replace('편집 가능한 원본은 [CaveBall 계층형 플로우 FigJam]', '이관 당시 편집 원본 링크는 [CaveBall 계층형 플로우 FigJam]')
texts[flow]=texts[flow].replace('각 Mermaid 바로 아래의 네 PNG는 같은 FigJam의 내보내기 영역에서 생성한 정적 사본임.',
    '이번 코드 대조 후 현재 흐름은 아래 Mermaid를 기준으로 함. FigJam의 갱신 여부는 미확인임. 콘텐츠 준비와 바닥 입력 PNG는 수정 전 사본으로 분리함.')
texts[flow]=texts[flow].replace('    ballError --> pInitStop','    ballError --> loadDialog')
texts[flow]=texts[flow].replace('    startGame --> pInitOut(["P-INIT 출력: 게임 실행 중"])',
    '    startGame --> startBallExists{"공 인스턴스 있음?"}\n    startBallExists -->|"아니요"| startNoop(["P-INIT 출력: 시작 호출 무효"])\n    startBallExists -->|"예"| pInitOut(["P-INIT 출력: 게임 실행 중"])')
texts[flow]=texts[flow].replace('class pInitStop,bgError,ballError failure','class pInitStop,startNoop,bgError,ballError failure')
texts[flow]=texts[flow].replace('게임 실행 중 또는 준비 중단 |','게임 실행 중, 준비 중단 또는 시작 호출 무효 |')
texts[flow]=texts[flow].replace('공을 찾지 못하면 게임 관리자가 초기화를 실패 처리하지만 상위 콘텐츠는 반환값을 사용하지 않음',
    '공이 없으면 게임 관리자 초기화는 실패함. 상위 콘텐츠는 반환값을 확인하지 않아 후속 진입 호출은 가능하나, `StartGame`의 공 존재 검사에서 게임 시작이 무효 처리됨')
floor_start=texts[flow].index('```mermaid',texts[flow].index('# 4. 사전 프로세스 C'))
floor_end=texts[flow].index('```',floor_start+10)+3
floor_mermaid='''```mermaid
flowchart TD
    pFloorIn(["P-FLOOR 입력: 수신 시작"]) --> subscribeOsc[OSC 점 구독]
    subscribeOsc --> receivePoint[메시지 콜백: 접촉점 수신]
    receivePoint --> pointValid{"센서와 데이터 유효함?"}
    pointValid -->|"아니요"| receivePoint
    pointValid -->|"예"| normalizePoint[접촉점 정규화]
    normalizePoint --> nearbyTouch{"가까운 접촉 있음?"}
    nearbyTouch -->|"예"| updateTouch[기존 접촉 갱신]
    nearbyTouch -->|"아니요"| addTouch[새 접촉 추가]
    updateTouch --> touchStore[(활성 접촉 목록)]
    addTouch --> touchStore
    updateTouch --> receivePoint
    addTouch --> receivePoint

    frameTick(["Update: 수신 중 매 프레임"]) --> removeExpired[만료 접촉 제거]
    touchStore -.-> removeExpired
    removeExpired --> editorInput[에디터에서 마우스 입력 갱신]
    editorInput --> bounceGate{"활성 접촉, 바닥 높이, 대기 시간 통과?"}
    bounceGate -->|"아니요"| debugUpdate[디버그 표시 갱신]
    bounceGate -->|"예"| projectBall[공 바닥 영역 계산]
    projectBall --> touchOverlap{"접촉 영역과 겹침?"}
    touchOverlap -->|"아니요"| debugUpdate
    touchOverlap -->|"예"| chooseNearest[가장 가까운 접촉 선택]
    chooseNearest --> calculateDirection[접촉점에서 공 중심 방향 계산]
    calculateDirection --> applyBounce[공 반사 요청과 대기 시각 기록]
    applyBounce --> pFloorOut(["P-FLOOR 출력: 반사 요청"])
    pFloorOut --> debugUpdate
    debugUpdate --> frameTick

    classDef input fill:#DCCCFF,stroke:#874FFF
    classDef success fill:#CDF4D3,stroke:#66D575
    class pFloorIn,frameTick input
    class pFloorOut success
```'''
texts[flow]=texts[flow][:floor_start]+floor_mermaid+texts[flow][floor_end:]
texts[flow]=texts[flow].replace('![[CaveBall P-INIT 콘텐츠 준비.png]]','수정 전 PNG는 관련 자료의 이전 사본 항목에서 관리함.')
texts[flow]=texts[flow].replace('![[CaveBall P-FLOOR 바닥 입력 처리.png]]','수정 전 PNG는 관련 자료의 이전 사본 항목에서 관리함.')
texts[flow]=texts[flow].replace('모든 조건을 통과한 가장 가까운 접촉점이 반사 방향의 기준이 됨.',
    '메시지 콜백은 접촉 목록만 갱신하며, 만료 제거와 반사 판정은 수신 중인 매 프레임의 `Update`에서 독립적으로 수행함. 모든 조건을 통과한 가장 가까운 접촉점이 반사 방향의 기준이 됨.')
texts[flow]+='\n## 수정 전 정적 사본\n\n- [콘텐츠 준비의 이전 PNG](<../04_Assets/01_Images/예시 이미지/CaveBall P-INIT 콘텐츠 준비.png>): 공 누락 경로가 현재 코드와 다름. 현재 흐름 판단에 사용하지 않음.\n- [바닥 입력의 이전 PNG](<../04_Assets/01_Images/예시 이미지/CaveBall P-FLOOR 바닥 입력 처리.png>): 메시지 수신과 매 프레임 처리가 직렬로 표현되어 있음. 현재 흐름 판단에 사용하지 않음.\n'
texts[flow]=texts[flow].replace('근거 범위는 [[CaveBall 클라이언트 코드 구조 분석','관련 해설은 [[CaveBall 클라이언트 코드 구조 분석')
texts[flow]=texts[flow].replace('## 2.1 콘텐츠 준비의 경계', '원문 근거: '+rootlink(code_ref)+'의 `CaveBallContent.cs:28-50, 68-76`과 `CaveBallGameManager.cs:30-39, 62-67`임.\n\n## 2.1 콘텐츠 준비의 경계')
texts[flow]=texts[flow].replace('## 3.1 손 입력의 계약', '원문 근거: '+rootlink(code_ref)+'의 `CaveBallMLInteraction.cs:143-225`와 `Core/CaveBallRules.cs:19-29`임.\n\n## 3.1 손 입력의 계약')
texts[flow]=texts[flow].replace('## 4.1 바닥 입력의 계약', '원문 근거: '+rootlink(code_ref)+'의 `CaveBallFloorInteraction.cs:56-76, 84-176`임.\n\n## 4.1 바닥 입력의 계약')

metadata(draft,'article',[rootlink(analysis)]+[rootlink(p) for p in ref_paths]+[rootlink(meeting)])
metadata(plan,'article',[rootlink(analysis),rootlink(flow)])
texts[plan]=texts[plan].replace('# 1. 개요','> 이관된 기획 초안임. 코어 시스템은 코드 분석과 계층형 플로우를 참고함. 디바이스 수치와 실제 설치 구성을 확정한 근거는 미확인임.\n\n# 1. 개요',1)
texts[plan]=texts[plan].replace('- **공간**','- 디바이스 사양의 상태: 아래 크기와 장비 수량은 이관된 예상안임. 현재 설치값과 일치하는지 미확인임.\n\n- **공간**',1)

# The extraction sheet explicitly calls itself a temporary work record, not primary evidence.
metadata(extract,'system',None,[yaml_list('consulted_documents',[rootlink(analysis)]+[rootlink(p) for p in ref_paths]+[rootlink(meeting)])])
texts[extract]=texts[extract].replace('`02_References/_locked/`의 `ref 1`부터 `ref 5`까지 전체 문서',
    '`01_References/00_프로젝트/02_연구개발계획서/`의 1장부터 5장까지 전체 문서')
texts[extract]+='\n# 작업 기록의 역할\n\n- 기획 초안 작성의 근거 추출 과정 기록이며 정식 지식의 독립 출처가 아님. 검증은 연결된 원자료에서 수행함.\n- 표의 행 번호는 이관 당시 위치 정보임. 현재 파일의 행 번호와 구분함.\n'

# Normalize body links without inventing missing entity documents.
aliases={Path(p).stem:p for p in texts}
for n,p in enumerate(ref_paths,1):
    aliases['ref '+str(n)+'. '+Path(p).stem.split('_',1)[1]]=p
aliases['ref 3. 연구개발의 추진전략·방법 및 추진일정']=ref_paths[2]
files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x.startswith('.') or x in {'99_Archive','node_modules','__pycache__'} for x in p.relative_to(ROOT).parts)]
by_name={}
for p in files:
    by_name.setdefault(p.name,[]).append(p.relative_to(ROOT).as_posix())
removed=[]
old_to_new={}
for p,text in texts.items():
    if p=='00_System/02_Logs/log.md':
        continue
    in_code=False
    lines=[]
    for line in text.splitlines(keepends=True):
        if re.match(r'^\s*```',line):
            in_code=not in_code
        if in_code:
            lines.append(line);continue
        def wiki(m):
            target,sep,label=m.group(1).partition('|')
            name,hash_,frag=target.partition('#')
            mapped=aliases.get(name)
            if mapped:
                return '[['+mapped.removesuffix('.md')+(('#'+frag) if hash_ else '')+(('|'+label) if sep else '')+']]'
            if not name:
                return m.group(0)
            if len(by_name.get(name,[]))==1:
                return '[['+by_name[name][0]+(('#'+frag) if hash_ else '')+(('|'+label) if sep else '')+']]'
            if '/' not in name and not hash_ and not Path(name).suffix:
                removed.append({'path':p,'target':name})
                return label if sep else name
            return m.group(0)
        line=re.sub(r'\[\[([^\]]+)\]\]',wiki,line)
        def image(m):
            old=m.group(1);name=Path(old).name
            found=by_name.get(name,[])
            if len(found)==1:
                relative=os.path.relpath(ROOT/found[0],(ROOT/p).parent).replace('\\','/')
                return m.group(0).replace(old,relative)
            return m.group(0)
        line=re.sub(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>',image,line)
        def markdown(m):
            label,dest=m.group(1),m.group(2)
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',dest):return m.group(0)
            bare=unquote(dest.strip('<>'))
            base,hash_,fragment=bare.partition('#')
            if base and Path(base).name in by_name and len(by_name[Path(base).name])==1:
                rel=os.path.relpath(ROOT/by_name[Path(base).name][0],(ROOT/p).parent).replace('\\','/')
                bare=rel+(('#'+fragment) if hash_ else '')
            return '['+label+'](<'+bare+'>)'
        # Existing ordinary links with parentheses in destination are not transformed here.
        line=re.sub(r'\[([^\]\n]*)\]\((<?[^)\n]+>?)\)',markdown,line)
        lines.append(line)
    texts[p]=''.join(lines)

# Capture original code bytes; this is a primary source snapshot, not an LLM summary.
code_files=sorted(list(code_dir.rglob('*.cs'))+list(code_dir.rglob('*.asmdef')))
code_rows=[]
for p in code_files:
    dest=STAGE/'01_References/01_CaveBall/원문 코드'/p.relative_to(code_dir)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(p.read_bytes())
    code_rows.append({'file':p.relative_to(code_dir).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
texts[code_ref]='---\ntitle: "CaveBall 클라이언트 코드 원자료"\ntype: reference\ncreated: "'+DATE+'"\nupdated: "'+DATE+'"\nstatus: review\n'+yaml_list('sources',[str(code_dir)])+'\nsource_check: verified\n---\n\n# 자료 개요\n\n- 외부 CaveBall 클라이언트의 C# 16개와 어셈블리 정의 1개를 변경 없이 보관한 원문 코드 자료임.\n- 직접 입력은 외부 소스 파일임. 코드 분석 문서에서 원문을 재구성하지 않음.\n\n# 출처와 보관 방식\n\n- 원본 위치: `'+str(code_dir)+'`.\n- 보관일: '+DATE+'. 원본과 사본의 SHA-256 해시 일치 확인함.\n- 외부 프로젝트를 수정하지 않음. 프리팹, JSON 설정, 외부 패키지와 실행 결과는 포함하지 않음.\n\n# 파일과 해시\n\n| 원문 파일 | SHA-256 |\n|---|---|\n'+'\n'.join('| ['+r['file']+'](<원문 코드/'+r['file']+'>) | `'+r['sha256']+'` |' for r in code_rows)+'\n\n# 확인 범위와 한계\n\n- `source_check: verified`는 이 자료에 열거한 원문 파일의 바이트 일치를 의미함. Unity 실행과 동작의 검증을 의미하지 않음.\n- 다른 위키의 분석 시점 이후 코드 변경 여부와 전체 프로젝트 리소스의 일치 여부는 미확인임.\n'

image_rows=[]
for p in sorted((ROOT/'04_Assets/01_Images').rglob('*.png')):
    data=p.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack('>II',data[16:24])
    image_rows.append({'path':p.relative_to(ROOT).as_posix(),'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest()})
texts[asset_ref]='---\ntitle: "이관 이미지 관리 기록"\ntype: asset\ncreated: "'+DATE+'"\nupdated: "'+DATE+'"\nstatus: draft\nsources: []\n'+yaml_list('asset_files',[r['path'] for r in image_rows])+'\n---\n\n# 용도와 상태\n\n- 현재 이관된 PNG '+str(len(image_rows))+'개의 파일 경로, 규격과 해시를 관리함.\n- `sources: []` 사유: 이번 기록은 기존 파일의 관리 목록임. 이미지별 실제 생성 입력과 프롬프트를 확인한 제작 기록이 없어 출처를 임의 보충하지 않음.\n- 연구개발계획서의 표시용 첨부 이미지와 CaveBall 예시 이미지를 포함함. 제작 방식과 최종 채택 상태는 미확인임.\n\n# 파일과 규격\n\n| 파일 | 픽셀 규격 | SHA-256 | 상태 |\n|---|---|---|---|\n'+'\n'.join('| ['+Path(r['path']).name+'](<'+os.path.relpath(ROOT/r['path'],(ROOT/asset_ref).parent).replace('\\','/')+'>) | '+str(r['width'])+' × '+str(r['height'])+' | `'+r['sha256']+'` | '+('수정 전 흐름도' if 'P-INIT' in r['path'] or 'P-FLOOR' in r['path'] else '이관본, 채택 미확인')+' |' for r in image_rows)+'\n\n# 기존 자료와 이번 관리 작업\n\n- 기존 생성과 검수 이력은 이관 로그에 남아 있으나 이미지별 실제 프롬프트와 전사본은 현재 파일에서 확인되지 않음. 과거 이력을 새 시각 검수 완료로 처리하지 않음.\n- 이번 작업은 파일 목록, PNG 헤더 규격, 해시와 삽입 경로 확인임. 이미지 파일은 변경하지 않음.\n\n# 검토 결과와 한계\n\n- 콘텐츠 준비와 바닥 입력의 PNG는 현재 코드와 차이가 있어 이전 사본으로 표시함. 현재 설명은 Mermaid를 사용함.\n- PNG 29장 전체의 문구와 의미를 전수 시각 검수하지 않음. 이번 직접 확인 대상은 콘텐츠 준비, 바닥 입력과 세계 실감미디어 시장 이미지 3개임.\n- 이미지 생성 입력, 도구 설정, 블라인드 전사와 기계 대조가 없는 항목은 미확인 상태임.\n'

# Rebuild the index from existing files, preserving operating-document identities.
texts['00_System/00_Index/Index.md']='''---
title: "위키 색인"
type: system
created: "2026-10-06"
updated: "2026-10-13"
---

# 목적

- Cave Super Ball과 실감 AX 연구개발 자료의 탐색 진입점임.
- 현재 파일과 프론트매터의 상태를 기준으로 안내함. 폴더에 있다는 이유만으로 확정 상태로 해석하지 않음.

# 운영 문서

## 지침과 규정

- [위키 작업 지침](../../AGENTS.md)
- [문서 작성 규칙](<../01_Rules/문서 작성 규칙.md>)
- [문서 형식](<../01_Rules/문서 형식.md>)
- [위키 작업 절차](<../01_Rules/위키 작업 절차.md>)
- [이미지 생성 규칙](<../01_Rules/이미지 생성 규칙.md>)

## 기록과 도구

- [2026년 10월 작업 로그](../02_Logs/2026-10.md)
- [이관된 과거 작업 기록](../02_Logs/log.md): 이관 전 경로와 당시 절차가 포함된 과거 기록임. 현재 지침으로 사용하지 않음.
- [헤더 번호 적용과 검증 도구](../03_Tools/heading_numbers.py)
- [헤더 번호 도구 검증 코드](../03_Tools/test_heading_numbers.py)
- [이미지 통합 기록 검증 도구](../03_Tools/image_record_check.py)

# 폴더 안내

| 경로 | 역할 |
|---|---|
| `00_System` | 운영 규정, 색인, 로그와 도구 |
| `01_References` | 연구개발계획서, 회의 녹취 요약과 원문 코드 |
| `02_Syntheses` | References의 종합과 분석 |
| `03_Articles` | 기획 문서. 현재 이관된 두 문서는 draft 상태임 |
| `04_Assets` | 이미지와 리소스 관리 기록 |
| `05_Prototypes` | 검토한 실행 가능한 프로토타입. 현재 등록된 프로젝트 없음 |
| `90_Workspace` | 작업 문서, 수정과 검증 및 점검 보고서 |
| `99_Archive` | 미사용 중간 산출물의 로컬 보관. 정식 출처로 사용하지 않음 |

# 자료와 산출물

## References

### 연구개발계획서

'''+ '\n'.join('- ['+Path(p).stem+'](<../../'+p+'>): 원자료 일부 대조 상태의 이관본.' for p in ref_paths)+'''

### 회의록과 원문 코드

- [2026-07-15 컨소시엄 킥오프 회의록](<../../'''+meeting+'''>): 원녹취 일부 대조 상태. 실제 회의일은 추가 확인 필요함.
- [CaveBall 클라이언트 코드 원자료](<../../'''+code_ref+'''>): C# 16개와 어셈블리 정의 1개의 바이트 일치를 확인한 원문 사본.

## Syntheses

- [CaveBall 클라이언트 코드 구조 분석](<../../'''+analysis+'''>): 정적 코드 분석 초안. 실행과 설치 구성은 미검증임.
- [CaveBall 계층형 플로우](<../../'''+flow+'''>): 코드 근거의 Mermaid 초안. 콘텐츠 준비와 바닥 입력의 이전 PNG 구분함.

## Articles

- [Cave Super Ball 기획서](<../../'''+plan+'''>): 코어 시스템과 디바이스 예상안을 담은 이관 초안. 개요 일부 미작성임.
- [Cave Super Ball 기획서 초안](<../../'''+draft+'''>): 콘텐츠 정의와 개발 목적 초안. 진행, 디바이스, 코어 시스템과 게임 플레이 미작성임.

## Assets

- [이관 이미지 관리 기록](<../../'''+asset_ref+'''>): PNG 29개 목록과 규격, 해시 및 미확인 제작 이력 관리함.

# Workspace

- [Cave Super Ball 개요 근거 추출](<../../'''+extract+'''>): 초안 작성 과정의 작업 기록. 독립 지식 출처가 아님.
- [위키 정합성 점검 보고서](<../../90_Workspace/위키 정합성 점검/위키 정합성 점검 보고서.md>): 명백한 오류의 수정 결과와 판단이 필요한 잔여 항목.
'''
texts[asset_ref]=texts[asset_ref].replace('PNG 29장', 'PNG '+str(len(image_rows))+'장')
texts['00_System/00_Index/Index.md']=texts['00_System/00_Index/Index.md'].replace('PNG 29개', 'PNG '+str(len(image_rows))+'개')

# Recalculate via the mandated tool API, then use its CLI for application/checking.
for p,text in texts.items():
    if p=='00_System/02_Logs/log.md':continue
    doc=hn.parse((ROOT/p).resolve(),text,ROOT)
    numbered,issues=hn.numbered(doc,'numbered')
    if issues:raise RuntimeError((p,issues))
    newdoc=hn.parse((ROOT/p).resolve(),numbered,ROOT)
    old=hn.parse((ROOT/p).resolve(),before.get(p,{'text':text})['text'],ROOT)
    # Match by semantic heading titles, including old source chapter numbering.
    def semantic(t):
        t=re.sub(r'^(?:\(\d+\)|\d+(?:\.\d+)*[.)]?)\s+','',t)
        t=re.sub(r'^\d+-\d+\.\s*','',t)
        t=re.sub(r'\[\[([^\]]+)\]\]',r'\1',t)
        return t
    for h in old.headings:
        matches=[x for x in newdoc.headings if semantic(x.text)==semantic(h.text)]
        if len(matches)==1:
            old_to_new[(p,h.text)]=matches[0].text
    write_stage(p,text)

def rewrite_frag(dest,source,wiki=False):
    target,sep,frag=unquote(dest).partition('#')
    if not sep or not frag or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',dest):return dest
    if not target:p=source
    elif wiki:p=target if target.endswith('.md') else target+'.md'
    else:
        resolved=(ROOT/source).parent/target
        p=resolved.resolve().relative_to(ROOT).as_posix()
    new=old_to_new.get((p,frag))
    if not new:
        for (q,old),value in old_to_new.items():
            if q==p and hn.slug(old)==frag:new=hn.slug(value);break
    return target+'#'+(new or frag)

for p,text in texts.items():
    if p=='00_System/02_Logs/log.md':continue
    def wiki_fragment(m):
        dest,sep,label=m.group(1).partition('|')
        new=rewrite_frag(dest,p,True)
        return '[['+new+(sep+label if sep else '')+']]'
    text=re.sub(r'\[\[([^\]]+)\]\]',wiki_fragment,text)
    def md_fragment(m):
        return '['+m.group(1)+'](<'+rewrite_frag(m.group(2),p)+'>)'
    text=re.sub(r'\[([^\]\n]*)\]\(<([^>\n]+)>\)',md_fragment,text)
    # Link-only changes to operating documents also require an updated date.
    if p in before and text!=before[p]['text']:
        doc=hn.parse((ROOT/p).resolve(),text,ROOT)
        text=hn.update_date(text,doc.front_end,DATE)
    texts[p]=text
    write_stage(p,text)

(WORK/'stage_manifest.json').write_text(json.dumps({'removed_missing_entity_links':removed,'code':code_rows,'images':image_rows,'paths':list(texts)},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'staged_documents':len(texts),'entity_links_converted_to_text':len(removed),'code_files':len(code_rows),'images':len(image_rows)},ensure_ascii=False))
