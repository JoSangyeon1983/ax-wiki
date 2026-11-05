---
title: "CaveBall과 Cave Action 콘셉트 작성 기준"
type: synthesis
created: "2026-11-05"
updated: "2026-11-05"
status: confirmed
sources:
  - "[[01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/2026-11-05 CaveBall 프로젝트 구현 원자료]]"
---

# 1 채택 내용과 적용 범위

- 2026-11-05 사용자 요청인 코드 분석 기반 콘셉트 작성과 두 콘텐츠의 개별 문서 작성을 채택 근거로 삼음.
- 채택 범위는 현재 구현에서 확인한 플레이 개념, 상태 전환, 입력과 피드백을 두 콘셉트 초안의 출발점으로 사용하는 것임.
- `confirmed`는 이 작성용 채택 범위에만 적용함. 콘셉트 승인, 운영 수치 확정 및 실제 동작 검증은 포함하지 않음.
- 적용 대상은 Cave Super Ball 콘셉트 초안과 Cave Action 콘셉트 초안임. 상세 기획과 기존 과제 해석의 자동 변경은 포함하지 않음.

# 2 CaveBall 작성 기준

## 2.1 공간과 참여

- 정면, 좌측 벽, 우측 벽과 바닥 화면에 공과 상호작용을 표시함. 바닥에는 블렌딩 출력 설정이 있음.
- 인식된 여러 참여자의 손목을 입력으로 처리함. 현재 설정의 4명은 손 효과 처리 슬롯 수이며 현장 권장 인원 확정값이 아님.
- 왼손은 빨강, 오른손은 파랑 요청으로 처리함. 사람별 진영 배정은 채택하지 않음.
- 적용 위치: 콘셉트의 개요, 주요 시스템 중 공간과 화면 및 참여자 인식.

근거: [화면 배치](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallDisplayRig.cs>)의 `Configure`, `ApplyFloorBlendDisplays`; [손 입력](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallMLInteraction.cs>)의 `OnPoseOutput`, `UpdateHand`; [설정](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/StreamingAssets/Setting/CaveballSetting.json>)의 `MaxTrackedPeople`.

## 2.2 플레이와 반복

- 콘텐츠 진입 후 공, 벽돌과 점수를 초기화하고 플레이를 시작함.
- 손과 바닥 입력은 공 이동 중 각각 처리하는 입력이며 반드시 차례대로 수행하는 절차가 아님.
- 같은 색 공으로 벽돌을 파괴함. 좌측 빨강 벽돌 파괴 시 파랑 득점, 우측 파랑 벽돌 파괴 시 빨강 득점.
- 모든 벽돌 파괴 후 공을 멈추고 대기한 다음 공, 벽돌과 두 색 점수를 초기화함.
- 적용 위치: 콘셉트의 전체 플로우, 주요 시스템 중 공과 벽돌 및 진행.

근거: [콘텐츠 진입](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallContent.cs>)의 `_OnEnter`; [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallGameManager.cs>)의 `ResetRound`, `ConfigureBricks`, `NotifyBrickDestroyed`, `ResetRoundAfterDelay`; [색과 벽돌 규칙](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/Core/CaveBallRules.cs>)의 `CanBreakBrick`.

## 2.3 색상과 바닥 반사

- 흰색 공에만 손 색을 부여하며, 지속 시간이 끝나면 흰색으로 복귀함.
- 바닥 접촉 영역과 공의 바닥 투영 영역이 겹치고 높이와 반사 간격 조건을 통과하면 반사함.
- 겹치는 접촉점 중 가장 가까운 점에서 공 중심으로 향하는 수평 방향과 위쪽 속도를 부여함.
- 적용 위치: 콘셉트의 주요 시스템 중 입력, 공의 색과 반사.

근거: [공](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBall.cs>)의 `TryApplyHandColor`, `Update`, `BounceFromFloorContact`; [바닥 입력](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallFloorInteraction.cs>)의 `TryBounceFromActiveTouches`, `IsBallNearFloor`.

## 2.4 표시와 기준값

- 정면 실루엣과 손 효과, 색별 점수, 벽돌 파괴 효과와 소리 및 측면 카메라 흔들림을 표시함.
- 현재 설정은 손 색 유지 5초, 라운드 재시작 대기 3초임. 콘셉트 초안의 검토 기준값으로만 사용함.
- 바닥 허용 높이 10은 경기장 높이 10과 같으므로 현장 판정 범위 확인 대상으로 둠.
- 적용 위치: 콘셉트의 주요 시스템 중 표시, 진행 및 미정 사항.

근거: [실루엣](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallSilhouetteView.cs>)의 `Initialize`, `SetMask`; [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/CaveBallGameManager.cs>)의 `NotifyBrickDestroyed`; [설정](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/StreamingAssets/Setting/CaveballSetting.json>).

# 3 Cave Action 작성 기준

## 3.1 공간과 입력

- 두 플레이어를 바닥의 좌측과 우측 영역으로 구분하고 각 영역에 하나의 발판을 표시함.
- 센서 점의 좌표 중앙값을 발판 중심으로 사용하며, 고정 크기와 이동 평활화 및 담당 영역 제한을 적용함.
- 정면의 실루엣은 분할 마스크를 화면 절반으로 나누어 표시함. 신원에 따른 사람 구분으로 해석하지 않음.
- 적용 위치: 콘셉트의 개요, 주요 시스템 중 공간과 입력.

근거: [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionGameManager.cs>)의 `ProcessFloorInput`, `UpdatePlayerPlatform`, `UpdatePlatformVisual`; [발판 규칙](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveBall/Core/CaveActionRules.cs>)의 `CalculateFixedPlatformRect`; [실루엣](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionSilhouetteController.cs>).

## 3.2 공수와 공격

- 게임 시작 시 첫 공격자를 무작위로 정하고, 턴 시간이 끝나면 공수를 교대함.
- 점프, 벽면 레이저, 위험 구역을 섞어 사용하고 연속 중복을 방지함. 플레이어의 공격 방식 선택 기능은 채택하지 않음.
- 점프 공격은 공격자 바닥 입력 소실에 따라 상대 영역 스캔라인을 생성함. 벽면 레이저는 벽 터치 시 상대의 당시 위치를 목표로 삼아 예고 후 공격함.
- 위험 구역은 공격자 위치를 좌우 반전하여 상대 영역에 표시하고 이동을 따라가며 발판 겹침을 판정함. 현재 폭과 높이 배율은 각각 발판의 0.5임.
- 적용 위치: 콘셉트의 전체 플로우, 주요 시스템 중 공수와 공격.

근거: [게임 진행과 공격](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionGameManager.cs>)의 `ResetGame`, `RefillAttackModeBag`, `SwitchRoles`, `UpdatePlatformLoss`, `UpdateScanLines`, `ProcessWallInput`, `StartLaserAttack`, `RunLaserAttack`, `SpawnHazard`, `UpdateHazards`.

## 3.3 소행성

- 소행성은 바닥 공간에 진입해 이동하고, 플레이어 발판과 위험 구역 또는 레이저 접촉 시 분할됨.
- 큰 소행성은 중간 크기, 중간 소행성은 작은 크기로 나뉘며 작은 소행성은 제거됨. 현재 분할 수는 2~3개이며 전체 개수 상한을 적용함.
- 추가 생성은 현재 3.5초 간격으로 확인하며 큰 소행성과 전체 소행성 상한 이내에서 수행함.
- 소행성 접촉에 따른 플레이어 체력 감소, 소행성 점수와 자원 획득은 채택 범위에 없음.
- 적용 위치: 콘셉트의 주요 시스템 중 소행성.

근거: [소행성](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionAsteroidController.cs>)의 `ResetSession`, `CheckContacts`, `HitByLaser`, `SplitAsteroid`; [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionGameManager.cs>)의 `UpdateAsteroidContacts`.

## 3.4 피해와 종료

- 유효 공격에 맞으면 체력 1 감소와 피격 무적을 적용함. 체력 0인 쪽이 발생하면 게임을 종료함.
- 피격 시 소리, 발판 점멸과 화면 흔들림으로 결과를 표시함.
- 종료 시 공격을 정리하고 소행성 이동을 멈추며 패배 측 화면 절반의 실루엣 조각 연출과 GAME OVER를 표시함.
- 대기 후 체력, 공격 상태와 소행성을 초기화하여 새 게임을 시작함.
- 적용 위치: 콘셉트의 전체 플로우, 주요 시스템 중 체력과 종료.

근거: [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionGameManager.cs>)의 `ApplyDamage`, `BeginGameOver`, `RestartAfterDelay`; [패배 연출](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionSilhouetteController.cs>)의 `PlayGameOver`, `CreateShatterPieces`, `ShowGameOverAfterShatter`.

## 3.5 표시와 기준값

- 역할, 공격 방식, 남은 시간과 체력을 안내하고 교대 전 3초를 표시함.
- 현재 설정의 턴 15초, 체력 3, 피격 무적 2초, 재시작 대기 20초를 검토 기준값으로 사용함.
- 소행성은 초기 4개, 전체 최대 24개이며 큰 소행성의 동시 상한은 코드에서 4개임.
- 현재 `UseOSC: false`이므로 실제 센서 입력은 현장 설정과 검증이 필요함. 점프 판정은 0.12초 입력 소실 기준임.
- 적용 위치: 콘셉트의 주요 시스템 중 진행, 소행성 및 미정 사항.

근거: [게임 진행](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionGameManager.cs>)의 `UpdateRoleGuide`; [소행성](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/Scripts/CaveAction/CaveActionAsteroidController.cs>)의 `MaximumBigAsteroids`; [설정](<../../01_프로젝트/개발 자료/CaveBall/2026-11-05 구현 자료/원문/Assets/StreamingAssets/Setting/CaveActionSettings.json>).

# 4 제외 사항과 한계

## 4.1 기획으로 확정하지 않는 내용

- 실제 공간 크기, 프로젝터와 센서 대수, 권장 연령 및 현장 수용 인원은 원문 코드만으로 확정하지 않음.
- 참가자 등록, 인원 충족 대기, 이용 시간 제한, 콘텐츠 선택 화면과 운영자 종료 화면은 새 기능으로 추가하지 않음.
- CaveBall의 사람별 진영, 최종 승자 판정과 누적 랭킹, 노란 공 및 8방향 반사를 현재 플레이 규칙으로 채택하지 않음. 노란 상태와 방향 함수는 정의만으로 실제 호출을 입증하지 않음.
- CaveAction의 안내 문구 RED와 BLUE는 현재 녹색 및 흰색 설정과 일치하지 않음. 콘셉트는 좌측과 우측 명칭을 사용하고 색상 통일은 미정으로 둠.
- 과거 콘셉트의 연구개발계획, 교육과 후속 사업 연계 해석은 이번 코드 기반 작성 범위에 포함하지 않음.

## 4.2 검증과 승인 경계

- 소스의 구현 사실을 콘셉트 초안 작성에 사용하며, 실제 체험 품질과 균형은 미검증임.
- 서브모듈 6개가 비어 있어 장치 연동과 실행을 확인하지 않음. 복원 후 실행 검증이 필요함.
- 두 콘셉트의 개발 목적과 핵심 경험은 채택한 규칙을 목적 언어로 정리한 기획상 해석임.
