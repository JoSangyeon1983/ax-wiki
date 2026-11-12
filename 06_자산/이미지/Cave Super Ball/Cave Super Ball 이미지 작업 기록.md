---
title: "Cave Super Ball 이미지 작업 기록"
type: asset
created: "2026-11-05"
updated: "2026-11-12"
status: review
reviewed: "2026-11-05"
review_note: 4:3 비율, 직접 시각 검수, 별도 컨텍스트의 블라인드 전사와 문자열 대조 완료. 개요용 콘셉트 시각화이며 기획 승인과 실제 구현 화면 검증은 포함하지 않음.
sources:
  - "[[03_기반 기획/콘셉트/Cave Super Ball 콘셉트 기획서]]"
asset_files:
  - "06_자산/이미지/Cave Super Ball/Cave Super Ball 개요.png"
---

# 1 용도와 입력

- 요청: 콘텐츠 개요에 사용할 가로 세로 4:3 이미지 생성과 HTML 삽입.
- 입력: [Cave Super Ball 기획서 초안](<../../../03_기반 기획/콘셉트/Cave Super Ball 콘셉트 기획서.md>)의 2026-11-05 본문.
- 핵심 메시지: 손과 바닥 입력으로 하나의 공을 조작하여 벽돌을 파괴하는 다면 공간 게임.
- 입력 대응: 손 색 변경: 1.1 콘텐츠 정의, 1.2 개발 목적과 핵심 경험 및 3.2 참여자 인식과 입력. 바닥 반사와 벽돌 파괴: 1.1 콘텐츠 정의와 1.2 개발 목적과 핵심 경험. 4면 공간과 양측 벽돌: 3.1 공간과 화면.
- 제외 범위: 진영 배정과 승패, 권장 인원 및 세부 수치는 미정이므로 표시하지 않음. 두 인물은 다중 참여의 예시임.

# 2 구성과 렌더 문자열

- 구성: 상단에 4면 체험 공간의 대형 실사형 장면, 하단에 핵심 경험의 풀컬러 모티프와 라벨을 배치한 비격자형 정보그래픽.
- 표시 위치: 기획서의 개요 시작 부분, 표시 너비 800 px와 반응형 축소.
- 전체 제목은 생략함. 왼쪽부터 세 정보 묶음을 병렬 배치하며 단계 순서로 표현하지 않음.
- 장소, 인물 외형과 조명은 설명용 시각화이며 실제 설치 사진이나 확정된 공간 규격이 아님.

| 위치 | 헤더 | 보조 캡션 | 횟수 |
|---|---|---|---|
| 하단 왼쪽 | 손 색 변경 | 왼손 빨강, 오른손 파랑 | 각 1회 |
| 하단 중앙 | 바닥 반사 | 접촉 위치에 따른 공 반사 | 각 1회 |
| 하단 오른쪽 | 벽돌 파괴 | 같은 색 벽돌 파괴와 득점 | 각 1회 |

# 3 생성과 검수

- 시도 1: 내장 image_gen으로 생성함. transparent_background=false, 4:3 요청. 보정 사유에 따라 현재 사용본에서 제외함.
- 모델: 도구 반환에 모델명 없음. 실제 모델명 미확인. 생성과 편집 모두 내장 image_gen 사용.
- 시도 2: targeted edit로 보정함. 실제 출력 1448 × 1086 px로 두 시도 모두 4:3 확인. 직접 대조와 블라인드 전사 및 기계 대조 후 현재 사용본으로 채택함.

# 4 보정 요청

- 시도 1: 1448 × 1086 px로 4:3 비율 확인. 직접 검수와 별도 컨텍스트의 블라인드 전사 수행함.
- 보정 이유: 한글 6개 문자열은 일치하나 바닥 반사 궤적의 접점과 신발의 입력 표시가 떨어져 있어 관계가 모호함.
- 시도 2: 아래 편집 프롬프트로 해당 부분만 보정함. 기존 라벨과 4:3 구성 유지 요청.

<!-- image-prompt:ball-overview-02 -->
```text
Edit this image with one targeted correction to the main room illustration only. The luminous red ball's curved motion trail currently meets the floor at a pink glowing point near the middle of the room, separated from the right participant's shoe contact marker. Move the floor endpoint of that same curved trail to the center of the luminous contact marker directly beneath the right participant's forward shoe, so floor contact and ball reflection have one shared visible origin. Remove the old central pink contact point and reconstruct that small floor area naturally. Keep the single red ball and brick impact in the same place, and keep the same two people, poses, three walls, floor, colors, room framing, every bottom icon, every Korean heading and caption exactly unchanged. Do not add any other text, objects or effects. Preserve the exact 4:3 landscape aspect ratio and existing full composition.
```

# 5 실제 프롬프트

<!-- image-prompt:ball-overview-01 -->
```text
Create a landscape image with an exact width-to-height aspect ratio of 4:3. This is a Korean concept-document overview infographic for an immersive projection game. Use a white open canvas, a large realistic exhibition-room visualization occupying the upper 72%, and three small open editorial annotation clusters along the bottom. No boxed cards, no enclosing infographic border, no overall headline. Photorealistic adult participants, believable room perspective, full-color projected game graphics, subtle soft shadows, and restrained navy Korean sans-serif typography. Keep substantial white margins and make every caption easily readable at 800 pixels display width.

Render only the following six Korean strings, each exactly once, with the exact spelling and punctuation. In the bottom-left cluster, place the bold heading "손 색 변경" directly above the smaller caption "왼손 빨강, 오른손 파랑". In the bottom-center cluster, place "바닥 반사" directly above "접촉 위치에 따른 공 반사". In the bottom-right cluster, place "벽돌 파괴" directly above "같은 색 벽돌 파괴와 득점". Do not render any other text, letters, numbers, branding, logo, watermark or title. The room screens and clothing contain no text. Captions must be separate from the hero scene and never obscured.

Show a single immersive projection room from an elevated viewpoint through its open entrance, with the left wall, front wall, right wall and floor all visible as four continuous display surfaces. Keep both side walls sufficiently broad to show their content. The left wall displays red brick blocks; the right wall displays blue brick blocks. The far front wall displays subtle motion-tracked human silhouettes. Two photorealistic adults in neutral unbranded casual sportswear share the same playing space, without colored team uniforms, handheld controllers, headsets or physical balls. One person raises an empty hand toward the projected scene; another steps onto a luminous floor contact marker while watching the same virtual ball. Show exactly one luminous red virtual ball near the left red-brick wall, with a modest red-brick break effect. A single restrained motion trail and a floor contact glow suggest the ball's movement and floor reflection. Do not draw multiple balls or a physical soccer kick. The installation is a plausible visualization, not a photograph of a finished venue. Keep people full-body, natural anatomy and enough room for movement.

In the bottom-left annotation, add a compact full-color illustration of a red left-hand glow and a blue right-hand glow; these represent the two hands of one participant, not different teams. In the center annotation add a shoe contact with a glowing floor point and a short upward reflection arc. In the right annotation add a red virtual ball contacting a red brick with a few fragments. These small explanatory motifs accompany their respective headings but do not contain any text. Use delicate separators between the clusters and generous spacing. Preserve the exact 4:3 landscape canvas; all image content and captions must be inside the margins.
```


# 6 현재 파일과 검수 결과

- 현재 사용본: [Cave Super Ball 개요.png](<Cave Super Ball 개요.png>). 기획서 개요에 HTML img로 삽입함.
- 파일 규격: 1448 × 1086 px, 가로 세로 4:3, 1762277 bytes.
- 직접 검수: 공의 궤적이 신발 아래 접촉 표시 내부의 발광점으로 연결됨. 본문의 곡선은 이동 이력의 표현이며 하단 반사 모티프는 오른쪽 위 방향을 표시함. 라벨의 가독성과 위치, 사람 수, 실존 브랜드와 로고 및 워터마크 부재 확인.
- 블라인드 전사: 별도 컨텍스트의 ball_image_blind_review 에이전트가 시도별 이미지 파일을 직접 확인함. 정답 목록은 제공하지 않음. 최종 전사는 아래 데이터에 보존함.
- 기계 대조: 최종 한글 6개 문자열이 각각 1회이며 전사와 일치함. 불확실한 문자열, 지정 외 글자와 수치 없음.

## 6.1 관리 범위와 보관

- 기존 전체 플로우 이미지는 변경하지 않음. 별도 관리 파일로 other_article_images에 경로를 명시하여 개요 이미지와 함께 문서 연결 대조함.
- 검수는 그림의 표현과 문자열 및 파일에 한정함. 실제 설치 장비 수, 화면 색상, 공간 치수와 UI 디자인의 확정 또는 Unity 실행 검증을 의미하지 않음.
- 최초 시도는 보관 작업 ID `2026-11-05 Cave Super Ball 개요 이미지 생성`으로 보존함. 보관 위치: `99_보관소/종료 작업/2026-11-05 Cave Super Ball 개요 이미지 생성`.
- 생성 도구 기본 저장 위치의 원본은 유지함. 작업 공간의 채택 이미지는 자산 정본으로 이동하고 이동 전후 해시 일치 확인.
- 최초 시도 전사: 지정 6개 문구와 일치, 추가 문자 없음. 바닥 접점 관계를 보정함.

# 7 재검증 데이터

<!-- image-work-record:start -->
```json
{
  "schema": "image-work-record-v1",
  "article_path": "03_기반 기획/콘셉트/Cave Super Ball 콘셉트 기획서.md",
  "article_sha256": "8FD827316CA3108E49EAE99C9B6FA785555BA3A3F4624A404B5F144A2A2714B2",
  "source_article_sha256_before_insertion": "203FC67F7834D0950CF79FCD7E3968EC54D688D697B4AC6A22CDB216A5A9DC96",
  "other_article_images": [
    "06_자산/도표/CaveBall 전체 플로우/Cave Super Ball 전체 플로우.png"
  ],
  "images": [
    {
      "path": "06_자산/이미지/Cave Super Ball/Cave Super Ball 개요.png",
      "spec": {
        "width": 1448,
        "height": 1086,
        "bytes": 1762277,
        "sha256": "AE37517CE13CEF9F88276DE9E8B47433960DEF91D99021397491387ADD527BED"
      },
      "expected_labels": [
        {
          "text": "손 색 변경",
          "count": 1
        },
        {
          "text": "왼손 빨강, 오른손 파랑",
          "count": 1
        },
        {
          "text": "바닥 반사",
          "count": 1
        },
        {
          "text": "접촉 위치에 따른 공 반사",
          "count": 1
        },
        {
          "text": "벽돌 파괴",
          "count": 1
        },
        {
          "text": "같은 색 벽돌 파괴와 득점",
          "count": 1
        }
      ],
      "transcription": [
        {
          "text": "손 색 변경",
          "location": "하단 왼쪽 큰 제목",
          "uncertain": false
        },
        {
          "text": "왼손 빨강, 오른손 파랑",
          "location": "하단 왼쪽 제목 아래",
          "uncertain": false
        },
        {
          "text": "바닥 반사",
          "location": "하단 가운데 큰 제목",
          "uncertain": false
        },
        {
          "text": "접촉 위치에 따른 공 반사",
          "location": "하단 가운데 제목 아래",
          "uncertain": false
        },
        {
          "text": "벽돌 파괴",
          "location": "하단 오른쪽 큰 제목",
          "uncertain": false
        },
        {
          "text": "같은 색 벽돌 파괴와 득점",
          "location": "하단 오른쪽 제목 아래",
          "uncertain": false
        }
      ],
      "review_status": "pass",
      "direct_visual_review": true,
      "prompt_ids": [
        "ball-overview-01",
        "ball-overview-02"
      ],
      "generation_tool": "image_gen",
      "model": "unconfirmed",
      "requested_aspect_ratio": "4:3",
      "transparent_background": false,
      "blind_review_agent": "/root/ball_image_blind_review"
    }
  ],
  "archive_inventory": [
    {
      "archive_path": "99_보관소/종료 작업/2026-11-05 Cave Super Ball 개요 이미지 생성/시도 01.png",
      "bytes": 1778494,
      "sha256": "8FB015BA85A66AA34F74D9A69EFA3EDA58661F3D95530BFDF592F3B38D19B5BE"
    }
  ]
}
```
<!-- image-work-record:end -->
