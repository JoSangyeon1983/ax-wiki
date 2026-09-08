---
title: CaveBall 계층형 플로우
type: overview
status: draft
tags: [CaveBall, Mermaid, 플로우, 인터랙션]
sources: [CaveBall 클라이언트 코드 구조 분석]
created: 2026-09-08
updated: 2026-09-08
---

> CaveBall의 실행 구조를 핵심 게임 플로우와 세 개의 사전 프로세스로 분리한 문서임. 핵심 플로우는 사용자 경험과 게임 규칙만 보여 주고, 콘텐츠 준비, 손 입력 처리와 바닥 입력 처리는 같은 계약 ID를 가진 별도 Mermaid 흐름도로 연결함. 코드 근거와 정적 분석의 한계는 [[CaveBall 클라이언트 코드 구조 분석]]을 따름.

# 1. 핵심 게임 플로우

핵심 플로우는 게임이 실행된 뒤 반복되는 사건과 결과만 표시함. 이 흐름에 입력을 공급하는 준비 과정은 호출형 노드로 접어 둠.

```mermaid
flowchart TD
    contentEnter([콘텐츠 진입]) --> pInit[["P-INIT: 콘텐츠 준비"]]
    pInit --> initReady{"게임 실행 중?"}
    initReady -->|"아니요"| prepareStop([준비 중단])
    initReady -->|"예"| gameStart[게임 시작]
    gameStart --> runtimeWait[공 이동과 입력 대기]
    runtimeWait --> eventType{"런타임 사건?"}

    eventType -->|"손 입력"| pHand[["P-HAND: 손 입력 처리"]]
    pHand --> handApplied{"색 적용됨?"}
    handApplied -->|"예"| applyColor[공 색 부여]
    handApplied -->|"아니요"| handResume[게임 계속]
    applyColor --> handResume
    handResume --> eventType

    eventType -->|"바닥 입력"| pFloor[["P-FLOOR: 바닥 입력 처리"]]
    pFloor --> floorApplied{"반사 적용됨?"}
    floorApplied -->|"예"| redirectBall[반사 방향 변경]
    floorApplied -->|"아니요"| floorResume[게임 계속]
    redirectBall --> floorResume
    floorResume --> eventType

    eventType -->|"벽돌 충돌"| colorMatch{"같은 색 벽돌?"}
    colorMatch -->|"아니요"| hitResume[벽돌 유지]
    colorMatch -->|"예"| breakBrick[벽돌 파괴]
    breakBrick --> scoreTeam[반대 진영 득점]
    scoreTeam --> bricksRemain{"남은 벽돌 있음?"}
    bricksRemain -->|"예"| hitResume
    bricksRemain -->|"아니요"| resetRound[지연 후 라운드 재설정]
    resetRound --> hitResume
    hitResume --> eventType

    eventType -->|"콘텐츠 이탈"| gameStop([게임 정지])

    classDef prep fill:#DCCCFF,stroke:#874FFF
    classDef action fill:#C2E5FF,stroke:#3DADFF
    classDef outcome fill:#CDF4D3,stroke:#66D575
    class pInit,pHand,pFloor prep
    class applyColor,redirectBall,breakBrick action
    class scoreTeam,resetRound outcome
```

## 1.1 사전 프로세스 연결 계약

핵심 플로우의 보라색 호출형 노드는 아래 상세 절과 연결됨. Mermaid 렌더러마다 클릭 링크 지원이 달라 문서 anchor를 정본 연결로 사용함.

| 계약 ID | 상세 플로우 | 입력 | 핵심 플로우로 돌려주는 결과 |
|---|---|---|---|
| `P-INIT` | [[#2. 사전 프로세스 A 콘텐츠 준비]] | 콘텐츠 로드와 진입 호출 | 게임 실행 중 또는 준비 중단 |
| `P-HAND` | [[#3. 사전 프로세스 B 손 입력 처리]] | 자세 추정 또는 인물 분할 메시지 | 공 색 적용 또는 변경 없음 |
| `P-FLOOR` | [[#4. 사전 프로세스 C 바닥 입력 처리]] | OSC 바닥 접촉점 | 공 반사 적용 또는 변경 없음 |

근거 범위는 [[CaveBall 클라이언트 코드 구조 분석#4. 실행 흐름]]임.

# 2. 사전 프로세스 A 콘텐츠 준비

`P-INIT`은 프리팹 로드부터 게임 시작 호출까지를 묶음. 준비가 끝나야 핵심 플로우의 게임 시작 이후로 들어갈 수 있음.

```mermaid
flowchart TD
    pInitIn(["P-INIT 입력: 콘텐츠 로드"]) --> createBg[CaveballBG 생성]
    createBg --> bgCreated{"배경 생성됨?"}
    bgCreated -->|"예"| hideBg[배경 비활성화]
    bgCreated -->|"아니요"| bgError[오류 기록]
    hideBg --> markLoaded[로드 완료 통지]
    bgError --> markLoaded

    markLoaded --> loadSettings[설정 JSON 로드]
    loadSettings --> bgAvailable{"배경 인스턴스 있음?"}
    bgAvailable -->|"아니요"| pInitStop(["P-INIT 출력: 준비 중단"])
    bgAvailable -->|"예"| configureDisplay[다면 출력 구성]
    configureDisplay --> initializeGame[게임 구성 요소 초기화]
    initializeGame --> ballFound{"공 발견됨?"}
    ballFound -->|"아니요"| ballError[오류 기록]
    ballError --> pInitStop
    ballFound -->|"예"| loadDialog[대화상자 연결]
    loadDialog --> contentEnter[콘텐츠 진입]
    contentEnter --> activateBg[배경 활성화]
    activateBg --> activateDisplay[UI 출력 적용]
    activateDisplay --> startGame[게임 시작 호출]
    startGame --> pInitOut(["P-INIT 출력: 게임 실행 중"])

    classDef input fill:#DCCCFF,stroke:#874FFF
    classDef success fill:#CDF4D3,stroke:#66D575
    classDef failure fill:#FFCDC2,stroke:#FF7556
    class pInitIn input
    class pInitOut success
    class pInitStop,bgError,ballError failure
```

## 2.1 콘텐츠 준비의 경계

- **포함**:
	- Addressable 배경 생성과 설정 로드
	- 다면 디스플레이, 점수판, 공, 벽돌, 효과와 입력 구성 요소 초기화
	- 콘텐츠 진입에 따른 배경 활성화, UI 출력 적용과 게임 시작
- **제외**:
	- 실제 프리팹과 JSON의 배포 상태
	- 외부 패키지의 초기화 내부 동작
- **실패 경계**:
	- 배경이 없으면 로드 완료 단계에서 준비를 멈춤
	- 공을 찾지 못하면 게임 관리자가 초기화를 실패 처리하지만 상위 콘텐츠는 반환값을 사용하지 않음

근거 범위는 [[CaveBall 클라이언트 코드 구조 분석#4.1 로드와 진입]]과 [[CaveBall 클라이언트 코드 구조 분석#6.1 우선 확인]]임.

# 3. 사전 프로세스 B 손 입력 처리

`P-HAND`는 자세 추정 세션 준비와 한 프레임의 손목 접촉 판정을 함께 표시함. 인물 분할 결과는 전면 실루엣으로 전달되고, 자세 결과만 공 색 판정으로 들어감.

```mermaid
flowchart TD
    pHandIn(["P-HAND 입력: 세션 시작"]) --> subscribePose[자세와 분할 구독]
    subscribePose --> moduleReady{"모듈 준비됨?"}
    moduleReady -->|"다음 프레임"| moduleReady
    moduleReady -->|"예"| startModule[자세와 분할 시작]
    startModule --> messageType{"수신 메시지?"}

    messageType -->|"인물 분할"| updateMask[실루엣 마스크 갱신]
    updateMask --> waitInput[다음 입력 대기]

    messageType -->|"자세"| postprocessPose[자세 후처리]
    postprocessPose --> peopleFound{"사람 있음?"}
    peopleFound -->|"아니요"| hideEffects[손 효과 숨김]
    hideEffects --> waitInput
    peopleFound -->|"예"| mapWrists[설정 인원과 손목 매핑]
    mapWrists --> wristValid{"손목 유효함?"}
    wristValid -->|"아니요"| waitInput
    wristValid -->|"예"| transformPoint[화면 좌표 보정]
    transformPoint --> overlapBall{"공 영역과 겹침?"}
    overlapBall -->|"아니요"| waitInput
    overlapBall -->|"예"| ballWhite{"공이 흰색?"}
    ballWhite -->|"아니요"| waitInput
    ballWhite -->|"예"| applyHandColor[손 색 적용]
    applyHandColor --> pHandOut(["P-HAND 출력: 공 색 적용"])
    pHandOut --> waitInput
    waitInput --> messageType

    classDef input fill:#DCCCFF,stroke:#874FFF
    classDef success fill:#CDF4D3,stroke:#66D575
    classDef inactive fill:#D9D9D9,stroke:#B3B3B3
    class pHandIn input
    class pHandOut success
    class hideEffects inactive
```

## 3.1 손 입력의 계약

- **입력**:
	- 자세 추정 결과의 사람 목록과 손목 좌표
	- 인물 분할 마스크
- **색 규칙**:
	- 왼손목은 빨간색 요청으로 바꿈
	- 오른손목은 파란색 요청으로 바꿈
	- 흰색 공만 손 색을 받을 수 있음
- **출력**:
	- 접촉 조건과 상태 규칙을 모두 통과하면 공 색을 바꿈
	- 통과하지 못하면 손 효과 표시만 갱신하거나 아무 변경 없이 다음 입력을 기다림

근거 범위는 [[CaveBall 클라이언트 코드 구조 분석#4.3 손 입력과 색 상태]]임.

# 4. 사전 프로세스 C 바닥 입력 처리

`P-FLOOR`는 OSC 점을 지속 가능한 접촉 목록으로 바꾼 뒤 공의 바닥 투영 영역과 비교함. 모든 조건을 통과한 가장 가까운 접촉점이 반사 방향의 기준이 됨.

```mermaid
flowchart TD
    pFloorIn(["P-FLOOR 입력: 수신 시작"]) --> subscribeOsc[OSC 점 구독]
    subscribeOsc --> receivePoint[접촉점 수신]
    receivePoint --> pointValid{"센서와 데이터 유효함?"}
    pointValid -->|"아니요"| floorWait[다음 입력 대기]
    pointValid -->|"예"| normalizePoint[접촉점 정규화]
    normalizePoint --> nearbyTouch{"가까운 접촉 있음?"}
    nearbyTouch -->|"예"| updateTouch[기존 접촉 갱신]
    nearbyTouch -->|"아니요"| addTouch[새 접촉 추가]
    updateTouch --> removeExpired[매 프레임 만료 제거]
    addTouch --> removeExpired

    removeExpired --> bounceGate{"반사 조건 통과?"}
    bounceGate -->|"아니요"| noBounce[변경 없음]
    noBounce --> floorWait
    bounceGate -->|"예"| projectBall[공 바닥 영역 계산]
    projectBall --> touchOverlap{"접촉 영역과 겹침?"}
    touchOverlap -->|"아니요"| noBounce
    touchOverlap -->|"예"| chooseNearest[가장 가까운 접촉 선택]
    chooseNearest --> calculateDirection[공 중심 방향 계산]
    calculateDirection --> applyBounce[공 반사 적용]
    applyBounce --> pFloorOut(["P-FLOOR 출력: 반사 적용"])
    pFloorOut --> floorWait
    floorWait --> receivePoint

    classDef input fill:#DCCCFF,stroke:#874FFF
    classDef success fill:#CDF4D3,stroke:#66D575
    classDef inactive fill:#D9D9D9,stroke:#B3B3B3
    class pFloorIn input
    class pFloorOut success
    class noBounce inactive
```

## 4.1 바닥 입력의 계약

- **입력 준비**:
	- 지정 센서의 OSC 점만 사용함
	- 보정 범위로 좌표를 정규화하고 설정에 따라 축을 뒤집음
	- 가까운 점은 합치고 유지 시간을 넘긴 점은 제거함
- **반사 조건**:
	- 활성 접촉점이 있어야 함
	- 공이 경기장 바닥 가까이에 있어야 함
	- 직전 반사 뒤 재입력 대기 시간이 지나야 함
	- 접촉 영역과 공의 바닥 투영 영역이 겹쳐야 함
- **출력**:
	- 접촉점에서 공 중심으로 향하는 수평 방향을 공에 전달함
	- 조건을 통과하지 못하면 이동을 바꾸지 않음

근거 범위는 [[CaveBall 클라이언트 코드 구조 분석#4.4 바닥 입력과 공 반사]]임.

# 5. 연결과 확장 규칙

이 문서의 연결 규칙은 새 세부 흐름이 생겨도 핵심 다이어그램이 비대해지지 않게 함.

- **계약 ID 유지**: 핵심 노드와 상세 절에서 같은 `P-...` ID를 사용함
- **입출력 명시**: 상세 플로우의 첫 노드와 마지막 노드에 계약 입력과 출력을 적음
- **정본 연결**: Mermaid 클릭 기능이 아니라 wikilink anchor로 핵심 노드와 상세 절을 연결함
- **상세 분리 기준**:
	- 독립 입력이나 준비 상태를 가짐
	- 세 단계 이상의 내부 처리 또는 분기를 가짐
	- 핵심 플로우에는 결과만 필요함
- **확장 방식**: 새 사전 프로세스는 핵심 플로우에 호출형 노드 하나를 추가하고, 별도 절과 계약표 행을 함께 추가함

# 6. 관련 자료

- [[CaveBall 클라이언트 코드 구조 분석]]: 코드 근거, 구성 요소 책임과 실행 확인 항목
- ![[CaveBall 코드 기반 인터랙션 구성도.png]]
