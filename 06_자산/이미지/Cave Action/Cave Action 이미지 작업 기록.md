---
title: "Cave Action 이미지 작업 기록"
type: asset
created: "2026-11-05"
updated: "2026-11-05"
status: review
reviewed: "2026-11-05"
review_note: "4:3 비율, 직접 시각 검수, 별도 컨텍스트의 블라인드 전사와 문자열 대조 완료. 개요용 콘셉트 시각화이며 기획 승인과 실제 구현 화면 검증은 포함하지 않음."
sources:
  - "[[03_기반 기획/콘셉트/Cave Action 콘셉트 기획서]]"
asset_files:
  - "06_자산/이미지/Cave Action/Cave Action 개요.png"
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
    }
  ],
  "archive_inventory": [
    {
      "archive_path": "99_보관소/종료 작업/2026-11-05 Cave Action 개요 이미지 생성/시도 01.png",
      "bytes": 1749330,
      "sha256": "E0C77271E0B2ACD100E6C9F509AF38782A30FD1652EE894AB685C512D19458BD"
    }
  ]
}
```
<!-- image-work-record:end -->
