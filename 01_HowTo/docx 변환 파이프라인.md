---
title: HWPX/DOCX 변환 파이프라인
type: howto
status: stable
tags: [howto, pipeline, hwpx, docx, pandoc, ingest]
created: 2026-05-11
updated: 2026-08-23
---

> 제안서/보고서 등 한컴 HWPX 또는 Word DOCX 문서를 LLM Wiki에 통합 가능한 MD로 변환하는 표준 절차. AI 에이전트가 후속 작업에서 환각 없이 인용할 수 있는 수준의 구조 보존이 목표.
> **HWPX 직접 변환을 권장**. 한컴 export 단계 없이 헤딩/표/이미지 모두 자동 보존.

# 1. 한눈에 보는 절차

```
HWPX 원본 (또는 DOCX)
  ↓ (사용자: /import-doc <파일 경로>)
[스크립트 자동 실행]
  ├─ HWPX → Python 파서 (assets/extract_hwpx.py)
  │    - paragraph 텍스트 + paraPr.heading.idRef로 bullet 들여쓰기
  │    - 텍스트 패턴 (N-M.)으로 H2/H3 자동 부여
  │    - <hp:tbl> → 분류(bold 라벨/정의 목록/pipe_table)
  │    - BinData/* → _figures/<name>/ 추출, <hp:pic> binaryItemIDRef로 본문 매핑
  ├─ DOCX → Pandoc
  │    - 헤딩 스타일이 있을 때만 H1~H6 복원 (한컴 export 시 손실 가능)
  │    - 표는 grid_table 보존
  │    - 미디어는 _figures/<name>/ 추출 (이미지 경로 상대화 후처리)
  └─ 공통: frontmatter 주입(converted/), 검수 큐 사이드카(_reviews/) 생성
  ↓
[작성자 후속 작업]
  - MOC에 변환본 등록
  - log.md에 ingest 항목 추가
  ↓
[사용자 검수]
  - 사이드카 체크리스트 확인 (헤딩 / 표 / 이미지 / 본문 일관성)
  - 완료 후 사이드카 삭제
```

# 2. 출력 위치

자산 수명/역할별로 폴더 분리: `converted/`는 1차 탐색 대상(본문만), `_figures/`/`_reviews/`는 부속 자산:

```
02_References/
├── _sources/<name>.<ext>           (원본 보존, 영구, 수정 금지)
├── _figures/<name>/                (추출 이미지, 영구)
│   ├── image1.png
│   └── ...
├── _reviews/<name>.review.md       (검수 큐 사이드카, 일시: 검수 완료 후 삭제)
├── _locked/                         (정본 마크다운, 영구, 수정 금지)
└── converted/<name>.md             (변환 본문, 1차 인용 대상)
```

본문 내 이미지 link는 `![](../_figures/<name>/imageN.<ext>)` (MD 기준 상대경로).
사이드카 wikilink는 `[[<name>.review]]` (Obsidian이 위치 무관 해석).

# 3. 사전 준비

- **HWPX 경로**: Python 3 (표준 라이브러리만 사용, 추가 패키지 불필요)
- **DOCX 경로**: Pandoc (`winget install --id JohnMacFarlane.Pandoc`, 설치 후 새 셸에서 `pandoc --version` 확인)
- Node.js (둘 다 공통)

# 4. 사용법

## 4.1 HWPX 경로 (권장)

```
/import-doc "D:/path/to/제안서.hwpx"
```

또는 이미 `_sources/`에 두었다면:

```
/import-doc "02_References/_sources/제안서.hwpx"
```

## 4.2 DOCX 경로

HWPX 원본이 없을 때만:

```
/import-doc "D:/path/to/제안서.docx"
```

# 5. 결과 확인

스크립트가 다음을 stdout으로 JSON 출력:

- 변환 백엔드 (`python (extract_hwpx.py)` 또는 `pandoc (...)`)
- 변환된 MD 경로 / 검수 큐 사이드카 경로
- 자동 통계 (H2/H3 헤딩 수, 표 N개, 이미지 N개)
- 변환기 경고가 있으면 그대로 표시

작성자는 추가로:

- MOC에 신규 변환본 등록
- log.md에 `ingest` 항목 추가

# 6. HWPX 파싱 정책 (V2 파서)

## 6.1 Section 처리 (다중 section 지원)

HWPX 본문은 `Contents/section0.xml`, `section1.xml`, ... N개의 section 파일로 분리될 수 있음. V2는 모든 `Contents/section*.xml`을 ZIP에서 발견 → 숫자 정렬 → 순서대로 walk. section 경계에서는 list block을 끊어(`last_bullet_indent = -1`) 다음 section 첫 paragraph가 직전 bullet 흐름에 종속되지 않게 함.

stats에 `sections` 수 보고. section0만 하드코딩하면 multi-section 문서에서 section1+ 콘텐츠가 silent data loss됨 ([[#8.11 패턴 12: 다중 section HWPX silent data loss]] 참고).

## 6.2 헤딩 자동 부여

HWPX의 paragraph는 대부분 `styleIDRef="0"` (Normal): 한컴 원본이 Word `Heading 1/2` 같은 명시적 헤딩 스타일을 쓰지 않음. 따라서 헤딩은 **텍스트 패턴**으로 식별:

| 패턴 | 매핑 |
|---|---|
| `^\d+-\d+\.\s` | `#` (H1): 예: "1-1. 연구개발의 개요" |
| `^\d+-\d+-\d+\.\s` | `##` (H2) |
| `^[가-하]-\d+\.\s` | `##` (H2): 예: "가-1. 결과물의 성능지표" (한글 라벨, RFP에서 H1 하위 섹션) |

**구조 기반 헤딩 승격** (텍스트 패턴 외):
표 직전 line이 **isolated 1단 bullet 짧은 라벨**이면 자동으로 H2 승격 + 표를 bullet block 밖(pipe_table 등)으로 emit. 조건 모두 만족 시 적용:

- `- text` 형태 (1단 bullet, 들여쓰기 0)
- text 길이 ≤ 25자
- text가 `:` 로 끝나지 않음 (콜론 끝 = 부모-자식 본문 패턴)
- text가 시각 마커(○/●/◇/■/-)로 시작 안 함
- 그 위 paragraph가 bullet이 아님 (nested 자식 보호: `시너지 효과` 같은 라벨 잘못 승격 방지)

예: `- 기술적 차별성` + 표 → `## 기술적 차별성` + pipe_table

원본 RFP를 H1별로 분리한 5개 HWPX 가정: 각 파일이 1챕터(`N. 챕터제목`). 그래서 파일 내부의 `N-M.`이 H1, `N-M-K.`가 H2.

본문 첫 비어있지 않은 줄이 `**N / 챕터제목**` 형태의 bold 단락(한컴 원본의 1행 표 챕터 헤더)이면 후처리 단계에서 제거: 파일명 + frontmatter title과 중복.

`^[○●◇■]\s` 패턴은 헤딩이 아니라 **1단 bullet**으로 처리 (이유는 [[#8. 문제 패턴 사전]] 참고).

## 6.3 Bullet 들여쓰기

`<hh:paraPr>` 의 `<hh:heading type="BULLET" idRef="N">` 값으로 자동 결정:

- idRef=1 → `- text` (1단)
- idRef=2 → `\t- text` (2단)
- idRef=3 → `\t\t- text` (3단)

## 6.4 표 처리

`<hp:tbl>` (paragraph 내부에 중첩되어도 추출) → 위치별 / 분류별 분기:

**bullet block 안 표** (last_bullet_indent ≥ 0):

- 셀 단위 cross-product 평탄화 (들여쓰기된 pipe_table을 Obsidian이 렌더 안 함 + AI 부분 인용 안전성 확보)
- 각 셀을 `row_label / col_label: value` 한 줄로 self-contained 출력
  - 예: `- 특성 / 택견(K-Motion): 개인 수련 중심`
  - AI 에이전트가 한 줄만 인용해도 row 라벨 + 컬럼 라벨 + 값 모두 추출 가능
- rowSpan 후속 row의 첫 컬럼이 비어있으면 직전 row 라벨 자동 상속 (한컴 셀 병합 의미 보존)
  - 예: 택견 rowSpan=3 표 → `- 택견 / 종목: 기본동작`, `- 택견 / 종목: 홀새김`, ...
- 빈 셀은 출력 생략 (정보 손실 없음)
- 표 전체는 부모 bullet의 자식 들여쓰기로 inline

**bullet block 밖 표** (3가지 분류):

1. **1행 짧은 셀들** (모든 셀 ≤30자) → `**text**` bold 라벨 (섹션 구분용)
2. **라벨↔내용 정의식 표** → `**label**` + bullet list. 판정 조건 완화:
   - 비어있지 않은 셀이 정확히 2개인 row (끝 빈 컬럼 허용: 3열 표지만 의미상 2열)
   - 좌측(라벨) 텍스트 ≤30자
   - 우측(내용) **paragraph 수 ≥3** 또는 **합산 텍스트 ≥100자**
   - 카테고리 마커(`[xxx]` 시작 paragraph) 다음 paragraph는 자동 2단 들여쓰기
   - **셀 내 paragraph hierarchy 보존**: paraPr `heading.type=NONE`이면 부모(1단), `heading.type=BULLET`이면 자식(2단). 예: `□` 부모 + `•` 자식 4개 = 1+4 계층 그대로 변환
   - **헤더 row 자동 생략**: 첫 row의 우측 셀이 ≤50자면 헤더로 간주, 출력 생략. H2 헤딩이 이미 컨텍스트를 주므로 헤더 라벨 중복 표시 불필요
3. **데이터 표** (위 둘에 해당 안 됨) → GFM pipe_table:

   ```
   | 헤더 | ... |
   |---|---|
   | 셀 | ... |
   ```

   셀 내 줄바꿈은 `<br>`, 셀 내 `|`는 `\|` 이스케이프.

**의미 보존 불가 표** (colCnt ≥ 12, 월별 그리드 등): 어느 위치든 메모로 대체:

- `> **변환 한계**: 원본의 N×M 표(월별 그리드 등)는 텍스트 추출 시 셀 위치 정보 손실...`
- 인용은 원본 HWPX 직접 참조

## 6.5 이미지

- `BinData/image*` 전체를 `_figures/<name>/`로 복사 (V2 분리 구조)
- 본문 위치: `<hp:pic>` 의 `<hc:img binaryItemIDRef="imageN">` → `![](../_figures/<name>/imageN.<ext>)` (MD 기준 상대경로 자동 계산)
- 캡션 패턴 (align=CENTER + 다음 4종 prefix): `[그림]`, `[표]`, `[도표]`, `[사진]` → `*텍스트*` 이탤릭
- bullet block 안 이미지/캡션은 마지막 bullet의 자식 들여쓰기로 inline 출력

## 6.6 시각 마커 처리

paragraph/셀 텍스트 시작의 시각 bullet 마커는 의미가 아니라 한컴 원본의 시각적 들여쓰기 표지. 제거 대상:

- 제거 패턴: `^\s*[○●◇◆■□▶▸▣•]\s*`
- 적용: handle_paragraph + extract_cells (셀 안 paragraph)
- 텍스트 시작 위치만 제거. 텍스트 내부 기호는 보존 (의미 가능성)

## 6.7 Frontmatter 형식

```
---
title: <파일명>
tags: [reference, converted, hwpx]
source: <원본 경로>
converted: YYYY-MM-DD
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
<본문 첫 줄>
```

frontmatter `---` 종료 직후 빈 줄 없이 본문 시작 (변환물 일관성).

## 6.8 자동 해석 OFF

- 이미지 Vision 해석: **OFF** (환각 방지)
- 표 의미 추론: **OFF** (셀 텍스트만 충실 전사)
- 본문 의역/요약: **OFF**

# 7. 설계 원칙

이 파이프라인은 5종 RFP 문서 변환 과정에서 다음 원칙을 검증했음. 다른 형식(PDF, RTF 등) 변환기 작성 시에도 적용 가능.

1. **표준 마크다운 문법으로 출력**: Pandoc 확장 문법(grid_table 등)은 Pandoc 외 뷰어(Obsidian, GitHub, VS Code)가 raw text로 표시. 모든 변환기는 GFM/CommonMark 표준 문법만 출력
2. **결정론적 파싱**: 변환 단계에 LLM 호출 없음. AI 에이전트는 산출물 통합/안내 단계에만 관여. 변환에 AI가 끼면 인용 신뢰성 무너짐
3. **원본 충실 전사**: 가운뎃점, 괄호, 특수문자 보존. 의역/요약은 검수 단계 또는 별도 명령에서
4. **시각 콘텐츠는 파일 보존만**: 도표/차트는 figures/로 추출, 자동 해석 금지
5. **변환물은 정본 아님**: `converted/`는 사본. 인용 기준은 `_sources/`/`_locked/`
6. **추출 단계에서 메타데이터 폐기 금지**: 텍스트 옆의 구조 정보(스타일, 들여쓰기, 정렬, 셀 병합 등)는 출력 단계에서 안 쓰더라도 추출 결과에 보존. 추후 단순화는 출력 단계 책임. 한 번 폐기된 메타데이터는 복원 불가 ([[#8.8 패턴 8: 표 셀 병합 무시로 row 한 칸씩 밀림 (인용 신뢰성 fatal)]]/차 사례)
7. **AI 인용 안전성**: 변환물의 한 줄을 떼어내 다른 문서에 붙여넣어도 의미가 살아 있도록 self-contained 구조 우선. cross-product 평탄화([[#8.7 패턴 7: bullet block 안 pipe_table 미렌더 + AI 인용 안전성]]), 변환 한계 메모([[#8.9 패턴 9: 의미 보존 불가능한 표(월별 그리드 등) 자동 메모 처리]]), hierarchy 보존([[#8.10 패턴 10: 셀 안 paragraph hierarchy 손실 (paraPr 메타데이터 폐기)]]) 모두 같은 원리에서 도출
8. **fail-safe 휴리스틱**: 문서마다 다른 구조적 가정(헤딩 패턴 등)은 가정 실패 시 정보 손실보다 약간의 노이즈가 낫다 ([[#8.6 패턴 6: 헤딩 패턴 부재 문서에서 본문 전체 삼킴]] 사례)

# 8. 문제 패턴 사전

같은 류의 변환 작업에서 재발할 수 있는 패턴들. 진단/대처 기록.

## 8.1 패턴 1: 헤딩 손실 (한컴 export 경유 시)

- **증상**: H2/H3가 모두 `**볼드 단락**`으로만 나옴. `## 1-1.` 형태가 없음
- **원인**: 한컴 HWPX→DOCX export 시 paragraph 스타일이 Word `Heading 1/2`로 매핑 안 됨. Pandoc은 DOCX heading 스타일에 의존하므로 복원 불가
- **대처**: HWPX 직접 파싱 (V2 경로). DOCX 경로를 어쩔 수 없이 써야 하면 텍스트 패턴 정규식 후처리 (`^\*\*\d+-\d+\.` → `## `): 단 한컴이 부여한 볼드 패턴이 케이스별로 다를 수 있어 100% 보장 안 됨

## 8.2 패턴 2: grid_table 정렬 깨짐 + raw text 표시 (Obsidian 등)

- **증상**: 표가 표로 안 보이고 `+---+---+` 행 구분선이 그냥 텍스트로 나옴. 한글이 섞인 표는 정렬도 어긋남
- **원인**: Pandoc grid_table(`+---+`)은 Pandoc 확장. Obsidian/GitHub/VS Code 마크다운 프리뷰는 pipe_table만 지원. 또 셀 너비 계산을 문자 수(`len(s)`)로 하면 한글이 시각적으로 2-width라 정렬 어긋남
- **대처**: 모든 표를 pipe_table(`| a | b |`)로 출력. 셀 내 줄바꿈은 `<br>` (GFM 표준 지원). 셀 내 `|`는 `\|` 이스케이프

## 8.3 패턴 3: list block 끊김 (들여쓰기 bullet이 raw text로 표시)

- **증상**: bullet 자식이 부모와 분리되어 raw text(들여쓰기 + dash 그대로)로 표시. Obsidian이 코드 블록 또는 들여쓰기 텍스트로 인식
- **원인**: 마크다운 list는 같은 paragraph 흐름 안에서만 부모-자식 관계 유지. 빈 줄 + 들여쓰기 0 콘텐츠(이미지, 평문)가 사이에 끼면 list 끊김. 이후 들여쓰기된 bullet은 부모 없는 들여쓰기가 되어 마크다운 파서가 별도 블록으로 처리
- **대처**: list block 상태 추적(`last_bullet_indent` 등).
  - **이미지/캡션/빈 paragraph**: 마지막 bullet의 자식 들여쓰기로 inline. last_bullet_indent 보존
  - **표**: [[#8.7 패턴 7: bullet block 안 pipe_table 미렌더 + AI 인용 안전성]] 참고 (들여쓰기된 pipe_table은 렌더 안 되므로 별도 처리)
  - **헤딩/평문 paragraph**: list block 명시적 끊음(last_bullet_indent = -1): 의미적 단위 분리가 필요한 경우만

## 8.4 패턴 4: "라벨 ↔ 긴 내용" 표가 grid에 욱여넣어짐

- **증상**: 한 셀에 paragraph 수십 개가 `<br>` join으로 들어가 표 폭이 페이지 폭 초과
- **원인**: 한컴 원본이 데이터 표가 아니라 정의 목록(라벨 + 긴 내용)을 표 형태로 그림. 셀 병합도 없음 (colSpan=1, rowSpan=1)
- **대처**: 표 분류 휴리스틱: 2열/좌측 짧음/우측 paragraph 다수면 정의 목록(`**label**` + bullet list)으로 변환. 진짜 데이터 표는 pipe_table 유지

## 8.5 패턴 5: ○/●/◇/■ 라벨 처리

- **증상**: ○를 H3 헤딩으로 만들면 그 아래 자식 bullet들이 paraPr 기반 들여쓰기(2/3단)로 시작 → H3 직후 부모 없는 들여쓰기 bullet으로 깨짐
- **원인**: 원본 한컴에서 ○가 헤딩이 아니라 시각적 1단 라벨로 쓰임. 자식 paragraph들의 paraPr idRef가 1단(`○ 자체`)을 건너뛰고 2단부터 시작
- **대처**: ○/●/◇/■ 시작 paragraph는 paraPr와 무관하게 강제 1단 bullet으로 변환. ○ 마크는 원본 보존

## 8.6 패턴 6: 헤딩 패턴 부재 문서에서 본문 전체 삼킴

- **증상**: 변환 결과 통계 모두 0 (H2/표/이미지/bullets 전부). MD 본문이 frontmatter 외 비어 있음
- **원인**: 챕터 제목 흡수 휴리스틱(첫 H2 만날 때까지 paragraph를 frontmatter title로 흡수)이 문서별 헤딩 패턴 차이를 가정 못 함. `N-M.` 패턴 H2가 없는 문서(예: 4.hwpx: 마일스톤 표 모음, `1 단계(1차연도)` 같은 다른 패턴)는 게이트가 영원히 열리지 않아 본문 281개 paragraph 전체가 삼켜짐
- **대처**: 챕터 제목 흡수 게이트 제거. 모든 paragraph는 본문 출력. frontmatter title은 파일명에서 자동 생성되므로 챕터 헤더 문구(`1 / 연구개발의 필요성` 등)가 본문 상단에 한 줄 추가되는 정도의 cosmetic 영향만 있음
- **일반 원리**: 헤딩 패턴 같이 "문서마다 다를 수 있는 구조적 가정"은 fail-safe 방향으로: 가정 실패 시 정보 손실보다는 약간의 노이즈가 낫다

## 8.7 패턴 7: bullet block 안 pipe_table 미렌더 + AI 인용 안전성

- **증상**: bullet 부모 아래 들여쓰기된 pipe_table이 raw text(`| 헤더 | ... |` 그대로)로 표시. Obsidian이 들여쓰기를 list item continuation으로 해석해서 표 문법이 무효화됨. 추가로 평탄화한 표여도 헤더-본문 분리 인용 시 매핑 잃음
- **원인**: GFM pipe_table은 들여쓰기 0에서만 동작이 보장됨. 들여쓰기된 표는 Obsidian이 인식 못 함. row 단위 평탄화도 헤더 위치 매핑이 부분 인용에서 깨짐
- **대처**: bullet block 안 표는 **셀 단위 cross-product 평탄화**. 각 셀을 `row_label / col_label: value` 한 줄로 self-contained 출력. 부분 인용에서도 모호성 0
- **rowSpan 처리**: 후속 row 첫 컬럼이 비어있으면 직전 row 라벨 자동 상속 (한컴 셀 병합 의미 보존)
- **트레이드오프**: 시각적 표 격자 손실 + 같은 row 라벨이 반복 등장. 대신 AI 에이전트가 본문 한 줄만 인용해도 의미 정확히 복원

## 8.8 패턴 8: 표 셀 병합 무시로 row 한 칸씩 밀림 (인용 신뢰성 fatal)

- **증상**: 마일스톤 표 같은 rowSpan/colSpan 병합이 있는 표에서 후속 row의 첫 컬럼이 비어 있어야 하는데 V2가 그 자리에 다음 셀 값을 넣어버려 모든 컬럼이 한 칸씩 밀림. 결과적으로 잘못된 컬럼-값 매핑
- **원인**: 단순히 `<hp:tc>` 자식만 순서대로 수집하면 한컴 표의 cellAddr/cellSpan 의미 잃음. row마다 `<hp:tc>` 개수가 일정하지 않은 표(병합 영역의 후속 row는 셀 수가 적음)에서 발생
- **대처**: `<hp:cellAddr colAddr rowAddr>` + `<hp:cellSpan rowSpan colSpan>` 활용. rowCnt × colCnt grid 만들고 각 셀을 `(rowAddr, colAddr)` 위치에 배치. 병합 영역의 후속 위치는 빈 셀로 점유 표시. row-major 출력 시 컬럼이 정확히 정렬됨

## 8.9 패턴 9: 의미 보존 불가능한 표(월별 그리드 등) 자동 메모 처리

- **증상**: 월별 셀 마킹 그리드 표(N×13, 셀 안에 색칠/마킹만 있음)가 텍스트 추출 후 의미 없는 row의 나열로 변환됨. 인용 시 환각 위험만 증가
- **원인**: 한컴 원본은 셀 마킹/색상으로 시각적 정보를 전달. HWPX → 텍스트 변환은 이런 시각 정보를 보존 못 함
- **대처**: `col_cnt ≥ 12`인 표는 자동으로 의미 보존 불가로 판정 → `> **변환 한계**: 원본의 N×M 표(월별 그리드 등)는 텍스트 추출 시 셀 위치 정보가 손실되어 의미 보존이 어려움. 인용 시 원본 HWPX 직접 참조 필요.` 메모로 대체
- **일반 원리**: 텍스트로 의미를 보존할 수 없는 콘텐츠는 가짜로 변환하기보다 명시적으로 "변환 한계"임을 알리는 메모로 대체. 환각 방지 원칙 일관

## 8.10 패턴 10: 셀 안 paragraph hierarchy 손실 (paraPr 메타데이터 폐기)

- **증상**: 표 셀에 한컴 원본이 `□` 부모 + `•` 자식 다수 구조를 가지고 있는데, 변환물에서 모두 1단 평탄 bullet으로 떨어짐. 부모-자식 관계 손실
- **원인**: 셀 paragraph를 단순 문자열 리스트로 수집하면 paraPr.heading 메타데이터(부모: type=NONE / 자식: type=BULLET idRef=N)가 폐기됨. 이미 strip_visual_marker로 시각 마커 제거된 상태라 텍스트만으로는 hierarchy 추론 불가
- **대처**: 셀 paragraph를 `(text, indent)` tuple로 추출. paraPr.heading.type을 들여쓰기로 환산(`NONE → 0`, `BULLET idRef=N → max(1, N-1)`). render_definition_list 등 출력 함수가 indent를 사용해 부모/자식 별도 출력
- **일반 원리**: **메타데이터 폐기 금지**. 변환 추출 단계에서 데이터 옆의 구조 정보(스타일, 들여쓰기, 정렬 등)를 함께 보존해야 한다. 출력 단계에서 활용 안 하더라도 일단 추출 결과에 포함시키는 게 안전. 단순화는 출력 단계의 책임
- **재발 가능 케이스**:
  - PDF 변환: 텍스트 + font size/weight 메타데이터를 함께 추출 (heading 추론)
  - HTML 파싱: 태그 의미(`<strong>`, `<em>`)를 텍스트로 통합하지 말고 별도 보존
  - 다른 문서 형식의 표 셀, 인라인 강조, 각주 등

## 8.11 패턴 12: 다중 section HWPX silent data loss

- **증상**: 변환 성공으로 끝나지만 section1.xml 이후의 본문(paragraph, 표, 이미지, 헤딩)이 모두 누락. 통계상 아무 경고 없음
- **원인**: `Contents/section0.xml`을 하드코딩한 채 ZIP의 다른 section 파일을 무시. 본 5종 RFP는 section0만 사용하지만 다른 HWPX는 multi-section 가능
- **대처**: ZIP에서 `Contents/section*.xml` 모두 발견 → 숫자 정렬 → 순서대로 walk. stats에 `sections` 수 보고. section 경계에서는 list block 끊음
- **일반 원리**: 컨테이너 포맷(ZIP, 디렉토리 등)에서 첫 entry만 하드코딩하지 말 것. 패턴 매칭으로 전체 발견 후 정렬/순회. 동일 패턴: PDF 다중 page, DOCX `word/document*.xml`, EPUB chapter 등

## 8.12 패턴 13: 변환 파이프라인이 _sources 원본을 silent overwrite

- **증상**: 같은 basename의 다른 파일을 import하면 기존 _sources 원본이 덮어쓰여 provenance 손실. 변환 성공으로 끝나서 발견이 어려움
- **원인**: `copyFileSync`는 기본 덮어쓰기. `_sources/`가 AGENTS.md상 read-only(추가만 허용, 수정/삭제 금지)인데 코드가 이 정책을 강제 안 함
- **대처**: copy 직전 sourcePath 존재 시 SHA256 비교. 동일 hash면 skip(idempotent), 다른 hash면 fail with explicit error 메시지 + 두 hash 노출. 사용자가 명시적으로 결정하도록 강제
- **일반 원리**: read-only 영역에 쓰는 코드 경로는 모두 동일성 검증 필수. 정책 문서만으로는 강제력 없음: 코드 레벨 guard 필요

## 8.13 패턴 11: 섹션 라벨 1행 표가 직전 bullet 깊이를 잘못 상속

- **증상**: 같은 1×1 라벨 표(`1 단계(1차연도)`, `1 단계(2차연도)`)인데 한 쪽은 bullet block 밖에서 emit되어 들여쓰기 0의 `**라벨**`로 정상 출력, 다른 한 쪽은 bullet block 안에서 emit되어 자식 들여쓰기 4단의 `\\t\\t\\t- **라벨**` 형태로 잘못 출력. 또는 평탄화 함수가 빈 리스트 반환해 아예 누락
- **원인**: emit_table이 last_bullet_indent 상태를 무조건 이어받음. 1행 짧은 셀 표는 의미상 "섹션 라벨"이라 list block 흐름과 무관해야 함
- **대처**: emit_table에서 1행 × 짧은 셀들(`≤30자`) 표는 위치 무관하게 list block 끊고 들여쓰기 0으로 bold 라벨 출력. `last_bullet_indent = -1` reset
- **일반 원리**: **콘텐츠의 의미적 위계**는 시각적 context(직전 paragraph가 무엇이었는지)와 다를 수 있다. 일부 콘텐츠 종류(섹션 라벨, 헤딩, 표 캡션 등)는 항상 list block 흐름을 끊는 게 의미와 일치. context 자동 상속은 일반론으로는 좋지만, 의미가 분명한 라벨류에는 명시적 reset 필요

시각 해석이 필요하면 별도 명령(`/describe-image` 등, 미구현)으로 명시 호출.

# 9. DOCX 파싱 정책 (Pandoc 경로)

| 단계 | 형식 | 적용 조건 | 신뢰도 |
|---|---|---|---|
| 1 | 파이프 테이블 (markdown) | 단순 표 (병합 없음, 단일 헤더) | 높음 |
| 2 | 그리드 테이블 (markdown) | 다중 행 헤더 또는 복잡 구조 | 중간 |
| 3 | HTML 테이블 (raw_html) | rowspan/colspan 셀 병합 | 중간: 사람 검수 권장 |
| 4 | PNG 캡처 + 캡션 인용 | Pandoc도 처리 못 하는 극단적 표 | 낮음: 원본 참조 필수 |

Pandoc은 기본적으로 1~3을 자동 선택. 4는 자동화하지 않음 (수동 보정).

**한컴 export 한계**: 한컴오피스에서 HWPX→DOCX 저장 시 paragraph 스타일이 Word `Heading 1/2`로 매핑되지 않아 헤딩이 볼드 단락으로 떨어진다. HWPX 직접 변환을 권장하는 주요 이유.

# 10. 환각 방지 원칙

이 파이프라인은 **"AI 에이전트가 후속 작업에서 인용해도 안전한 형태"**가 목표:

- **텍스트 콘텐츠 (표 셀, 본문, 캡션)**: 충실 전사. 파서/Pandoc 신뢰
- **시각 콘텐츠 (도표/차트/다이어그램)**: 파일로 보존만, 자동 해석 금지
- **불확실한 변환**: 검수 큐 사이드카에 명시. 사람 검수 전까지 "신뢰도 낮음"으로 취급
- **변환물은 정본이 아님**: `converted/`는 사본. 인용 기준은 항상 `_sources/`의 원본 또는 `_locked/`의 정본
- **변환 단계에 LLM 호출 없음**: 파서는 결정론적 XML 처리. AI 에이전트는 산출물 통합/안내 단계에만 관여

# 11. 검수 큐 처리

`<name>_review_pending.md` 파일의 체크리스트를 항목별 확인:

- **헤딩 구조**: H2가 원본의 절 구분과 1:1 대응되는지, 누락된 헤딩 없는지
- **표**: 모든 표가 원본과 셀 내용 일치, 셀 병합 의미 보존
- **이미지**: 본문 참조 위치 정확, 캡션 보존
- **본문 일관성**: 페이지/문단 누락, 각주, 한자/특수문자 인코딩

문제 없으면 사이드카 파일 삭제. 일부 항목이 손상됐다면 본문 직접 수정 후 사이드카에 수정 내역 기록.

# 12. 트러블슈팅

## 12.1 `python을 찾을 수 없음` (HWPX 경로)

- `python --version` 또는 `python3 --version` 으로 확인
- Windows는 Microsoft Store에서 Python 설치하거나 `winget install Python.Python.3.12`

## 12.2 `pandoc을 찾을 수 없음` (DOCX 경로)

1. 새 PowerShell 창에서 `pandoc --version` 확인
2. 설치되어 있는데도 안 잡히면 PATH 미반영: 셸 재시작 또는 `PANDOC_PATH` 환경변수로 직접 지정
3. 스크립트는 winget 설치 경로를 자동 탐색하므로 보통 자동 해결됨

## 12.3 한글 파일명/경로

- 따옴표로 감쌀 것: `/import-doc "02_References/_sources/연구계획서_v2.hwpx"`
- Windows 경로 구분자(`\`)는 Node.js가 자동 정규화

## 12.4 변환 결과가 깨짐

- 원본이 손상되었을 가능성: 한컴/Word에서 다시 저장
- HWPX가 비밀번호 보호되어 있으면 ZIP 파싱 실패
- 표가 너무 복잡하면 일부 손실 가능: 검수 큐에서 확인 후 수동 보정

## 12.5 헤딩이 잡히지 않음 (HWPX)

V2 파서는 `\d+-\d+\.` 패턴에 의존. 원본이 "제1장", "I.", "가." 등 다른 번호 체계를 쓰면 매칭 안 됨. 필요 시 `assets/extract_hwpx.py` 의 `H2_PAT`/`H3_PAT` 정규식을 케이스별로 확장.

# 13. 관련 문서

- [[CONVENTIONS#2. 디렉토리 구조]] / [[CONVENTIONS#6. 수정 금지 영역]]
- [[AGENTS#2.6 수정 금지 영역 준수]]
- HWPX 파서: `assets/extract_hwpx.py`
- 통합 스크립트: `scripts/import-doc.mjs`
- 슬래시 커맨드: `.claude/commands/import-doc.md`
