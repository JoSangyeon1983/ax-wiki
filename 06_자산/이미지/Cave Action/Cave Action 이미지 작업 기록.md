---
title: "Cave Action 이미지 작업 기록"
type: asset
created: "2026-11-05"
updated: "2026-11-12"
status: review
reviewed: "2026-11-12"
review_note: "개요와 인터랙션 개념도 각 1개의 4:3 비율, 직접 시각 검수, 별도 컨텍스트의 블라인드 전사와 문자열 대조 완료. 인터랙션 개념도는 사용자 제공 4면 이미지와 외형 대조함. 기획 승인과 실제 구현 화면 검증은 포함하지 않음."
sources:
  - "[[03_기반 기획/콘셉트/Cave Action 콘셉트 기획서]]"
  - "사용자 제공: D:/Sangyeon/02_Task/2026/03_KOCCA/AX/02_Resources/00_Image/케이브액션_전개도.png"
  - "사용자 제공: D:/Sangyeon/02_Task/2026/03_KOCCA/AX/02_Resources/00_Image/케이브액션_전경.png"
asset_files:
  - "06_자산/이미지/Cave Action/Cave Action 개요.png"
  - "06_자산/이미지/Cave Action/Cave Action 인터랙션 개념도.png"
---

# 1 용도와 입력

- 요청: 콘텐츠 개요에 사용할 가로 세로 4:3 이미지 생성과 HTML 삽입.
- 입력: [Cave Action 콘셉트 기획서](<../../../03_기반 기획/콘셉트/Cave Action 콘셉트 기획서.md>)의 2026-11-05 본문.
- 핵심 메시지: 두 참여자가 공간 입력으로 공격과 회피를 수행하며 공수를 교대하는 체력 대전 게임.
- 입력 대응: 공수 교대: 1.1 콘텐츠 정의, 1.2 개발 목적과 핵심 경험 및 2.3 공수 교대. 공간 공격: 1.1 콘텐츠 정의와 2.2 공격과 방어 반복. 체력 대결: 2.4 게임 종료와 재시작. 공간과 발판: 3.1 공간과 플레이어 표시.
- 제외 범위: 점프, 레이저와 위험 구역을 동시에 사용하는 장면은 제외하고 벽 터치와 회피 사례만 대표 장면으로 사용함. 인원은 좌우 각 1명이며 세부 수치와 미정인 색상 표준은 확정하지 않음.

# 2 구성과 렌더 문자열

- 구성: 상단에 4면 체험 공간의 대형 실사형 장면, 하단에 핵심 경험의 풀컬러 모티프와 라벨을 배치한 비격자형 정보그래픽.
- 표시 위치: 기획서의 개요 시작 부분, 표시 너비 800 px와 반응형 축소.
- 전체 제목은 생략함. 왼쪽부터 세 정보 묶음을 병렬 배치하며 단계 순서로 표현하지 않음.
- 장소, 인물 외형과 조명은 설명용 시각화이며 실제 설치 사진이나 확정된 공간 규격이 아님.

| 위치 | 헤더 | 보조 캡션 | 횟수 |
|---|---|---|---|
| 하단 왼쪽 | 공수 교대 | 턴마다 바뀌는 공격과 방어 | 각 1회 |
| 하단 중앙 | 공간 공격 | 점프, 벽 터치, 위치 이동 | 각 1회 |
| 하단 오른쪽 | 체력 대결 | 체력 소진으로 게임 종료 | 각 1회 |

# 3 생성과 검수

- 시도 1: 내장 image_gen으로 생성함. transparent_background=false, 4:3 요청. 보정 사유에 따라 현재 사용본에서 제외함.
- 모델: 도구 반환에 모델명 없음. 실제 모델명 미확인. 생성과 편집 모두 내장 image_gen 사용.
- 시도 2: targeted edit로 보정함. 실제 출력 1448 × 1086 px로 두 시도 모두 4:3 확인. 직접 대조와 블라인드 전사 및 기계 대조 후 현재 사용본으로 채택함.

# 4 보정 요청

- 시도 1: 1448 × 1086 px로 4:3 비율 확인. 직접 검수와 별도 컨텍스트의 블라인드 전사 수행함.
- 보정 이유: 한글 6개 문자열은 일치하나 지정하지 않은 느낌표가 경고 모양 안에 추가됨.
- 시도 2: 아래 편집 프롬프트로 해당 부분만 보정함. 기존 라벨과 4:3 구성 유지 요청.

<!-- image-prompt:action-overview-02 -->
```text
Edit this image with one targeted correction only. Remove the exclamation mark and its triangular outline from the center of the red-orange warning circle on the floor. Preserve the circular warning marker as an abstract unlettered projected ring, retaining the laser's endpoint and nearby floor texture. The center must contain no punctuation, character, digit, logo or symbol that resembles text. Keep everything else exactly unchanged: the two people, poses, room, screen graphics, floor platforms, lighting, bottom icons, all six Korean headings and captions, typography and spacing. Do not add or rewrite any text. Preserve the exact 4:3 landscape aspect ratio and the existing full composition.
```

# 5 실제 프롬프트

<!-- image-prompt:action-overview-01 -->
```text
Create a landscape image with an exact width-to-height aspect ratio of 4:3. This is a Korean concept-document overview infographic for a two-person immersive projection game. Use a white open canvas, a large realistic exhibition-room visualization occupying the upper 72%, and three small open editorial annotation clusters along the bottom. No boxed cards, no enclosing infographic border, no overall headline. Photorealistic adult participants, believable room perspective, full-color projected game graphics, subtle soft shadows, and restrained navy Korean sans-serif typography. Keep substantial white margins and make every caption easily readable at 800 pixels display width.

Render only the following six Korean strings, each exactly once, with the exact spelling and punctuation. In the bottom-left cluster, place the bold heading "공수 교대" directly above the smaller caption "턴마다 바뀌는 공격과 방어". In the bottom-center cluster, place "공간 공격" directly above "점프, 벽 터치, 위치 이동". In the bottom-right cluster, place "체력 대결" directly above "체력 소진으로 게임 종료". Do not render any other text, letters, numbers, branding, logo, watermark or title. The room screens and clothing contain no text. Captions must be separate from the hero scene and never obscured.

Show a single immersive projection room from an elevated viewpoint through its open entrance, with the left wall, front wall, right wall and floor all visible as four continuous display surfaces. The floor is clearly divided into left and right play areas by a subtle center line. Exactly two photorealistic adults in neutral unbranded casual sportswear occupy the left and right areas, one person per side, on distinct projected floor platforms. The left participant touches their own left wall with an empty hand; a clearly virtual colored laser effect travels across the projected surfaces toward a warning marker in the opponent's right floor area. The right participant actively sidesteps out of that warning marker, visually showing attack and avoidance. Both people are full-body with natural anatomy. The laser is only screen imagery, never a physical weapon or a harmful beam striking a body. No handheld controllers, no headsets, no physical combat, no balls or brick walls. Show faint motion-tracked silhouettes on the far front wall, a few small asteroid game sprites on the floor, and understated abstract health indicators without digits or letters. Keep the projected interaction legible rather than visually busy. Color choices are illustrative interface colors, not fixed player identities. The installation is a plausible visualization, not a photograph of a finished venue.

In the bottom-left annotation, add a compact full-color icon of two player silhouettes with a pair of opposing curved arrows indicating exchanged roles. In the center annotation, add one compact group of colorful jump, wall-hand-touch and foot-movement motifs, with no additional text. In the right annotation, add a simple game health-bar icon decreasing toward empty, without any numbers or letters. The motifs accompany their respective headings. Use delicate separators between the clusters and generous spacing. Preserve the exact 4:3 landscape canvas; all image content and captions must be inside the margins.
```


# 6 현재 파일과 검수 결과

- 현재 사용본: [Cave Action 개요.png](<Cave Action 개요.png>). 기획서 개요에 HTML img로 삽입함.
- 파일 규격: 1448 × 1086 px, 가로 세로 4:3, 1773047 bytes.
- 직접 검수: 바닥 경고 원의 느낌표와 삼각형 제거 확인. 공격자 측 벽 접촉 위치 부근과 수비자 영역의 경고 원이 광선으로 연결되며 수비자는 경고 원 바깥에 위치함. 라벨의 가독성과 위치, 사람 수, 실존 브랜드와 로고 및 워터마크 부재 확인.
- 블라인드 전사: 별도 컨텍스트의 action_image_blind_review 에이전트가 시도별 이미지 파일을 직접 확인함. 정답 목록은 제공하지 않음. 최종 전사는 아래 데이터에 보존함.
- 기계 대조: 최종 한글 6개 문자열이 각각 1회이며 전사와 일치함. 불확실한 문자열, 지정 외 글자와 수치 없음.

## 6.1 관리 범위와 보관

- 기존 전체 플로우 이미지는 변경하지 않음. 별도 관리 파일로 other_article_images에 경로를 명시하여 개요 이미지와 함께 문서 연결 대조함.
- 검수는 그림의 표현과 문자열 및 파일에 한정함. 실제 설치 장비 수, 화면 색상, 공간 치수와 UI 디자인의 확정 또는 Unity 실행 검증을 의미하지 않음.
- 최초 시도는 보관 작업 ID `2026-11-05 Cave Action 개요 이미지 생성`으로 보존함. 보관 위치: `99_보관소/종료 작업/2026-11-05 Cave Action 개요 이미지 생성`.
- 생성 도구 기본 저장 위치의 원본은 유지함. 작업 공간의 채택 이미지는 자산 정본으로 이동하고 이동 전후 해시 일치 확인.
- 최초 시도 전사: 지정 6개 문구 외에 바닥 경고 원의 느낌표 1개가 추가되어 보정함.

# 7 재검증 데이터

<!-- image-work-record:start -->
```json
{
  "schema": "image-work-record-v1",
  "article_path": "03_기반 기획/콘셉트/Cave Action 콘셉트 기획서.md",
  "article_sha256": "0C93E294BC5794E2E694A29B391B610782B0EED58102E14267DF17B19550AFF1",
  "source_article_sha256_before_insertion": "2B8C880388128DFF1B6D0B1EE489904DC791F0F22ACB9FB2AE6C639143DAA2D5",
  "other_article_images": [
    "06_자산/도표/CaveBall 전체 플로우/Cave Action 전체 플로우.png"
  ],
  "images": [
    {
      "path": "06_자산/이미지/Cave Action/Cave Action 개요.png",
      "spec": {
        "width": 1448,
        "height": 1086,
        "bytes": 1773047,
        "sha256": "6BCC37C2ABB5BE6C8D7EC105A27D1FC752E2F09DD3EA4B9E0F0D32CBAB5B62F6"
      },
      "expected_labels": [
        {
          "text": "공수 교대",
          "count": 1
        },
        {
          "text": "턴마다 바뀌는 공격과 방어",
          "count": 1
        },
        {
          "text": "공간 공격",
          "count": 1
        },
        {
          "text": "점프, 벽 터치, 위치 이동",
          "count": 1
        },
        {
          "text": "체력 대결",
          "count": 1
        },
        {
          "text": "체력 소진으로 게임 종료",
          "count": 1
        }
      ],
      "transcription": [
        {
          "text": "공수 교대",
          "location": "하단 왼쪽 설명 영역의 제목",
          "uncertain": false
        },
        {
          "text": "턴마다 바뀌는 공격과 방어",
          "location": "하단 왼쪽 제목 아래",
          "uncertain": false
        },
        {
          "text": "공간 공격",
          "location": "하단 가운데 설명 영역의 제목",
          "uncertain": false
        },
        {
          "text": "점프, 벽 터치, 위치 이동",
          "location": "하단 가운데 제목 아래",
          "uncertain": false
        },
        {
          "text": "체력 대결",
          "location": "하단 오른쪽 설명 영역의 제목",
          "uncertain": false
        },
        {
          "text": "체력 소진으로 게임 종료",
          "location": "하단 오른쪽 제목 아래",
          "uncertain": false
        }
      ],
      "review_status": "pass",
      "direct_visual_review": true,
      "prompt_ids": [
        "action-overview-01",
        "action-overview-02"
      ],
      "generation_tool": "image_gen",
      "model": "unconfirmed",
      "requested_aspect_ratio": "4:3",
      "transparent_background": false,
      "blind_review_agent": "/root/action_image_blind_review"
    },
    {
      "path": "06_자산/이미지/Cave Action/Cave Action 인터랙션 개념도.png",
      "spec": {
        "width": 1448,
        "height": 1086,
        "bytes": 1976368,
        "sha256": "160E5EA7D54400EAC7CAEBED83B83D73F1CE254ABD271A9BF661D8089437FD70"
      },
      "expected_labels": [
        {
          "text": "공격",
          "count": 1
        },
        {
          "text": "방어",
          "count": 1
        },
        {
          "text": "공수 교대",
          "count": 1
        },
        {
          "text": "점프 공격",
          "count": 1
        },
        {
          "text": "스캔라인을 넘는 점프 회피",
          "count": 1
        },
        {
          "text": "벽면 터치",
          "count": 1
        },
        {
          "text": "공격 예고 후 위치 회피",
          "count": 1
        },
        {
          "text": "위치 이동",
          "count": 1
        },
        {
          "text": "상대 영역의 위험 구역 이동",
          "count": 1
        }
      ],
      "transcription": [
        {
          "text": "공수 교대",
          "location": "상단 오른쪽 교대 화살표 아래",
          "uncertain": false
        },
        {
          "text": "공격",
          "location": "상단 큰 그림 왼쪽 사용자 연결선 옆",
          "uncertain": false
        },
        {
          "text": "방어",
          "location": "상단 큰 그림 오른쪽 사용자 연결선 옆",
          "uncertain": false
        },
        {
          "text": "점프 공격",
          "location": "하단 왼쪽 예시의 제목",
          "uncertain": false
        },
        {
          "text": "스캔라인을 넘는 점프 회피",
          "location": "하단 왼쪽 제목 아래",
          "uncertain": false
        },
        {
          "text": "벽면 터치",
          "location": "하단 가운데 예시의 제목",
          "uncertain": false
        },
        {
          "text": "공격 예고 후 위치 회피",
          "location": "하단 가운데 제목 아래",
          "uncertain": false
        },
        {
          "text": "위치 이동",
          "location": "하단 오른쪽 예시의 제목",
          "uncertain": false
        },
        {
          "text": "상대 영역의 위험 구역 이동",
          "location": "하단 오른쪽 제목 아래",
          "uncertain": false
        }
      ],
      "review_status": "pass",
      "direct_visual_review": true,
      "prompt_ids": [
        "action-interaction-01"
      ],
      "generation_tool": "image_gen",
      "model": "unconfirmed",
      "requested_aspect_ratio": "4:3",
      "transparent_background": false,
      "blind_review_agent": "/root/action_interaction_blind_review",
      "use_location": "보고서와 기획 자료에 재사용할 독립 이미지 자산. 기획서 본문 미삽입.",
      "reference_files": [
        {
          "path": "D:/Sangyeon/02_Task/2026/03_KOCCA/AX/02_Resources/00_Image/케이브액션_전개도.png",
          "sha256": "3E2D8B6BB440AFD654C1541945E54F3C3F69E9F3C48CE8AC4E22B968BCF47EAB"
        },
        {
          "path": "D:/Sangyeon/02_Task/2026/03_KOCCA/AX/02_Resources/00_Image/케이브액션_전경.png",
          "sha256": "FA4886054DC7D4FD46480B45F4FD42FDB9D1F32496CAE39F69DD10A72AD4E6AA"
        }
      ]
    }
  ],
  "archive_inventory": [
    {
      "archive_path": "99_보관소/종료 작업/2026-11-05 Cave Action 개요 이미지 생성/시도 01.png",
      "bytes": 1749330,
      "sha256": "E0C77271E0B2ACD100E6C9F509AF38782A30FD1652EE894AB685C512D19458BD"
    },
    {
      "archive_path": "99_보관소/종료 작업/2026-11-12 Cave Action 인터랙션 개념도 생성/입력 전개도.png",
      "bytes": 545765,
      "sha256": "3E2D8B6BB440AFD654C1541945E54F3C3F69E9F3C48CE8AC4E22B968BCF47EAB"
    },
    {
      "archive_path": "99_보관소/종료 작업/2026-11-12 Cave Action 인터랙션 개념도 생성/입력 전경.png",
      "bytes": 600084,
      "sha256": "FA4886054DC7D4FD46480B45F4FD42FDB9D1F32496CAE39F69DD10A72AD4E6AA"
    }
  ],
  "standalone_images": [
    "06_자산/이미지/Cave Action/Cave Action 인터랙션 개념도.png"
  ]
}
```
<!-- image-work-record:end -->

# 8 인터랙션 개념도 생성

## 8.1 요청과 입력 범위

- 요청: 2026-11-12 사용자 제공 케이브 4면의 전개도와 전경을 바탕으로 가로 세로 4:3 인터랙션 개념도 생성.
- 입력 화면: 사용자 제공 `D:/Sangyeon/02_Task/2026/03_KOCCA/AX/02_Resources/00_Image/케이브액션_전개도.png`와 `케이브액션_전경.png`. 전개도와 조립 상태의 공간 대응, 우주 배경, 금속 프레임과 연두색 조명 및 보라색 좌우 바닥의 외형 참고용임.
- 입력 내용: [Cave Action 콘셉트 기획서](<../../../03_기반 기획/콘셉트/Cave Action 콘셉트 기획서.md>)의 콘텐츠 정의, 공격과 방어 반복, 공수 교대, 공간과 플레이어 표시 및 공수와 공격 방식.
- 핵심 메시지: 두 사용자가 케이브의 벽면과 바닥에서 점프, 터치와 위치 이동으로 공격과 회피를 수행하며 공수를 교대하는 공간형 대전 경험.
- 이미 정의된 세 공격 방식과 공수 교대 구조를 사용함. 새 단계나 기능을 도출하지 않음. 점프 공격, 벽면 레이저와 위험 구역은 서로 다른 예시로 구분함.
- 제외: 운영 수치, 공간 실측 치수, 현장 센서 성능, 고정 진영 색상과 실제 구현 화면의 확정. 승인 대기인 기획의 상태는 유지함.

## 8.2 구성과 라벨

- 사용 목적: 보고서와 기획 자료에 재사용할 인터랙션 설명 자산. 이번 요청에 기획서 본문 삽입은 포함하지 않음.
- 구성: 열린 흰 캔버스의 상단 대형 4면 공간과 하단 세 공격 방식의 병렬 예시. 전체 제목 생략, 벽면 터치를 상단의 대표 장면으로 사용함.
- 정보 유형: 상단은 공간과 공수의 관계, 하단은 기존 세 공격 방식의 나열임. 입력 행동, 화면 반응과 상대의 회피를 연결하여 활동과 대응을 설명함. 하단은 순차 진행 단계로 표시하지 않음.
- 시각 어휘: 참고 이미지 외형을 반영한 3차원 공간과 사실적인 두 사용자, 채움 색이 있는 소형 행동 예시, 얇은 연결선과 의미가 있는 화살표. 원근과 광원 통일.
- 문자열: 아래 표 외의 문자와 수치 및 기호 금지. 표의 각 문자열을 지정 위치에 1회씩 배치함.

| 위치 | 헤더 또는 역할 | 보조 캡션 | 횟수 |
|---|---|---|---|
| 상단 왼쪽 사용자 옆 | 공격 | 없음 | 1회 |
| 상단 오른쪽 사용자 옆 | 방어 | 없음 | 1회 |
| 오른쪽 위 교대 아이콘 아래 | 공수 교대 | 없음 | 1회 |
| 하단 왼쪽 예시 아래 | 점프 공격 | 스캔라인을 넘는 점프 회피 | 각 1회 |
| 하단 가운데 예시 아래 | 벽면 터치 | 공격 예고 후 위치 회피 | 각 1회 |
| 하단 오른쪽 예시 아래 | 위치 이동 | 상대 영역의 위험 구역 이동 | 각 1회 |

## 8.3 생성 시도와 실제 프롬프트

- 시도 1: 생성과 검수 통과, 현재 사용본으로 채택함. 내장 `image_gen`, `transparent_background: false`, 4:3 화면비를 프롬프트로 지정함. 모델과 해상도 및 품질 인자는 제공하지 않음.
- 모델: 호출 결과로 식별되지 않으면 미확인으로 기록함.
- 외형 입력: 전개도와 전경을 모두 참조 이미지로 제공함. 기존 이미지를 덮어쓰지 않는 신규 생성임.
- 검수 계획: 직접 대조, 정답 문자열을 제공하지 않는 별도 컨텍스트의 전사, 문자열과 배정 횟수의 기계 대조 및 파일 규격 확인.

<!-- image-prompt:action-interaction-01 -->
```text
Create one polished Korean interaction concept infographic in an exact landscape 4:3 aspect ratio. Use the two supplied images as spatial and visual references for the same four-surface Cave Action installation: Image 1 is the unfolded display net; Image 2 is the assembled perspective. Use an open white editorial canvas, one dominant three-dimensional cutaway of the installation across the upper two thirds, and three small full-color explanatory illustrations across the bottom third. The room should closely retain the reference imagery, with black metallic sci-fi framing, vivid lime-green illuminated trims, the ringed planet and starfield across the front wall, dark metallic side walls, and the purple starfield floor divided into left and right areas by the central lime strip. This is a clear technical concept illustration for a report, not a generic gaming poster. Use realistic human figures and a clean three-dimensional room rendering, restrained navy typography, crisp colored interaction overlays, and generous white margins. No boxed cards, no uniform rectangular infographic sections, no overall title.

Render only these nine Korean strings, each exactly once, in a legible Korean sans-serif font. In the upper main illustration, place the short role label "공격" next to the left person and "방어" next to the right person, outside the room where necessary with thin unarrowed leader lines. Near the upper right white margin, place "공수 교대" immediately beneath a small icon of two opposing curved arrows exchanging attack and defense roles. These arrows are an explanatory icon, not a path instructing people to exchange floor areas. In the bottom left, place the bold heading "점프 공격" directly beneath its illustration and the smaller caption "스캔라인을 넘는 점프 회피" immediately below it. In the bottom center, place "벽면 터치" beneath its illustration, with "공격 예고 후 위치 회피" immediately below it. In the bottom right, place "위치 이동" beneath its illustration, with "상대 영역의 위험 구역 이동" immediately below it. No other text, numbers, letters, punctuation, logos, brands, watermarks, interface words or pseudo-lettering anywhere, including the room screens, clothing and illustrations. Do not duplicate any label inside an icon. All text must remain outside the perspective surfaces so that it is horizontal, large, unobstructed and readable at a displayed width of 1000 pixels.

The dominant scene must be a single open-front, open-top three-dimensional room viewed from an elevated centered entrance viewpoint, closely matching Image 2. Show exactly four display surfaces: front wall, left wall, right wall, and floor; no ceiling display, rear wall or extra floor plane. The floor remains one continuous plane with two play areas. Keep the front starfield, ringed planet and sci-fi framing recognizably consistent with the supplied imagery. Make the side walls low or sufficiently angled in perspective to see both participants and the interaction. Do not add furniture, physical consoles, headsets, controllers or weapons.

Exactly two full-body adults occupy this main room, one on the left floor half and one on the right. Use neutral unbranded sportswear and believable anatomy, feet correctly contacting the floor. The left attacker reaches to touch their own left side wall with an empty hand. A compact projected light pulse marks the contact point. Show a thin amber virtual attack route drawn on the wall and floor surfaces toward a circular warning target in the opponent's right floor area. Make the route clearly screen imagery on the surfaces rather than a physical floating beam through either person. The right defender is visibly sidestepping away from that target with their projected footprint platform also outside it; a short curved cyan movement arrow may show this avoidance. Retain one small projected platform under each person's current feet. The main scene depicts the wall-touch mode only: no jumping or moving hazard rectangle at the same time. A few small unlettered asteroid sprites may appear on the floor without obscuring the players, target or route. The planet in the front-wall artwork is background imagery, never a shared gameplay ball.

The three bottom illustrations explain alternative attack modes, not sequential steps and not simultaneous attacks. Separate the three open clusters with two fine light-gray vertical hairline dividers only. Each has a miniature pair of full-color human figures on a simple purple floor strip with a subtle central division, using the same perspective, lighting, colored overlays and visual language as the main scene. These are explanatory examples in addition to the two people in the main scene; do not place these extra illustrative figures inside the main room.

For the bottom-left example, show the left figure jumping with a short upward arrow and an emitted scanline crossing the right floor half. Show the right figure jumping over that line, with visible air below both feet, to communicate timed avoidance. For the bottom-center example, show a left hand touching a small fragment of the matching side wall, a projected attack route toward a fixed circular warning target on the right floor, and the right figure stepping away from the target. For the bottom-right example, show the left figure shifting their footprint platform, with a subtle dashed correspondence arrow to a small orange rectangular hazard on the right half at the mirrored position. Show the right figure moving clear of that rectangle. The hazard follows the attacker's mirrored movement, not the defender. Make each cause and response visible through a small number of meaningful arrows, with no decorative connector lines. Preserve clear hierarchy: the actual referenced room is dominant; the lower examples are compact supporting explanations. Keep the exact 4:3 canvas, all figures and all nine text strings fully inside safe margins.
```

## 8.4 현재 파일과 검수 결과

- 현재 사용본: [Cave Action 인터랙션 개념도.png](<Cave Action 인터랙션 개념도.png>).
- 파일 규격: PNG, 1448 × 1086 px, 가로 세로 정확히 4:3, 1976368 bytes.
- SHA-256: `160E5EA7D54400EAC7CAEBED83B83D73F1CE254ABD271A9BF661D8089437FD70`.
- 직접 검수: 정면, 좌측 벽, 우측 벽과 바닥의 연결 및 참고 이미지의 금속 프레임, 연두색 조명, 우주 배경과 좌우 바닥 구분 대조. 큰 장면에 두 사용자만 배치하고 왼쪽 벽 터치, 바닥 공격 경로, 오른쪽 표적 바깥의 방어자 위치와 이동 화살표 확인. 하단 예시와 한글 라벨의 판독, 철자와 배정 위치 및 실존 브랜드, 로고와 워터마크 부재 확인.
- 블라인드 전사: 별도 컨텍스트의 `/root/action_interaction_blind_review` 에이전트에게 이미지 파일만 제공함. 정답 문자열 미제공. 한글 9개를 각각 1회 전사했고 판독 불가, 애매한 문자, 별도 작은 글자와 수치, 로고 및 워터마크 없음으로 보고함. 최종 전사는 재검증 데이터에 보존함.
- 기계 대조: 확정 문자열 9개와 전사 문자열의 철자 및 횟수 일치, 누락과 초과 및 불확실 전사 없음. 파일 헤더, 바이트 수, SHA-256과 4:3 비율 대조.
- 형태 관찰: 정면 아래의 수평 금속 띠는 입력 전경과 전개도에 포함된 배경 그림의 하부 표현임. 별도 표시 면이나 실제 계단을 추가하는 의미로 사용하지 않음. 표적에서 방어자의 현재 위치로 향하는 청록색 화살표는 표적 밖 이동을 나타냄. 공수 교대 아이콘은 역할 교대이며 사용자 바닥 영역을 교환하는 지시가 아님.
- 검수 한계: 현재 콘셉트 초안을 설명한 시각화임. 현장 치수, 실제 센서 인식, 게임 실행과 사용자 회피 시간 및 확정 사용자 인터페이스 검증은 수행하지 않음.

## 8.5 파일 관리와 재검증

- 정본은 자산 폴더의 인터랙션 개념도 1개임. 생성 도구 기본 경로의 원본은 유지함. 작업 공간의 검수 통과 파일을 자산 폴더로 이동하고 SHA-256 일치 확인.
- 입력 원본 두 파일은 변경하지 않음. 작업 중 보존한 사본은 원본과 바이트 일치 확인 후 작업별 폴더째 보관함.
- 보관 작업 ID: `2026-11-12 Cave Action 인터랙션 개념도 생성`. 보관 경로: `99_보관소/종료 작업/2026-11-12 Cave Action 인터랙션 개념도 생성`. 보관 파일의 해시와 크기는 재검증 데이터에 기록함. 보관소 내부로 연결하는 링크는 만들지 않음.
- 개요 이미지는 기존 파일을 유지하며 해당 2026-11-05 프롬프트와 전사 결과를 보존함. 새 개념도를 기획서 본문에 삽입하지 않으며 기획서 SHA-256은 기존 스냅샷과 같음.
- 재검증 데이터의 `standalone_images`에 기획서 본문 미삽입 자산을 명시함. 검증 도구에 해당 목록의 중복, 관리 파일 소속과 본문 삽입 여부를 검증하는 선택 항목을 추가함. 기존 문서의 이미지 연결 전수 대조는 유지함.
