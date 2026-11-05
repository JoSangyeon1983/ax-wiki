from pathlib import Path
import re
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
TARGET = ROOT / '03_Articles/발표/피드백.md'
ORIGINAL = WORK / '피드백 원문.txt'
DRAFT = WORK / '피드백.md'

EDITS = [
    (
        '해당 연구를 손가락 재활 훈련에서도 사용할 수 있을지 문의하였고 고려하고 있는데 아직 섬세한 구현이 안되어서 해당 부분은 조금 더 발전시켜야 한다는 답변을 받았습니다.',
        '해당 연구를 손가락 재활 훈련에도 활용할 수 있을지 문의했습니다. 이에 대해, 활용을 고려하고 있으나 아직 세밀한 구현이 이루어지지 않아 해당 부분을 더 발전시킬 필요가 있다는 답변을 받았습니다.',
    ),
    (
        '기술이 발전하더라도 도구만으로 몰입감이 증가하는 것이 아니며 발표대로 몰입감은 사용자가 가상 객체와의 상호작용으로 형성되므로 향후 가상현실 기반 실감 콘텐츠 개발에 유용한 연구라고 생각합니다.',
        '기술이 발전하더라도 도구만으로 몰입감이 높아지는 것은 아닙니다. 발표에서 설명한 바와 같이 몰입감은 사용자가 가상 객체와 상호작용하는 과정에서 형성되므로, 향후 가상현실 기반 실감 콘텐츠 개발에 유용한 연구라고 생각합니다.',
    ),
    (
        '개인적으로 월드 오브 워크래프트 게임의 수중 지역인 바쉬르에서 플레이할 때 심해공포증을 겪은 적이 있어서 이러한 감정을 극복할 수 있는 방안이 있는지 질문하였습니다. 이에 대해 연구 과정에서 동일한 반응이 있었고 이를 해결하기 위해 최대한 밝은 생명체와 밝은 환경들로 감정이 이완되도록 설계했다는 답변을 들었습니다.',
        '개인적으로 월드 오브 워크래프트의 수중 지역인 바쉬르에서 플레이할 때 심해공포증을 경험한 적이 있어, 이러한 감정을 극복할 방안이 있는지 질문했습니다. 이에 대해 연구 과정에서도 같은 반응이 나타났으며, 이를 해결하기 위해 최대한 밝은 생명체와 환경을 활용해 정서적 이완을 유도하도록 설계했다는 답변을 받았습니다.',
    ),
    (
        'XR 방탈출의 경우 구성을 잘 짠다면 영화 큐브처럼 공간적 제약을 극복할 수 있을 것이라고 생각합니다.',
        'XR 방탈출은 구성을 정교하게 설계한다면 영화 큐브처럼 공간적 제약을 극복할 수 있을 것으로 생각합니다.',
    ),
    (
        'XR 방탈출의 소재로 사도세자 관련 이야기가 진행되는 것으로 보이는데 장소로는 폴아웃의 볼트같은 지하대피소나 우주정거장 같은 폐쇄된 공간을, 소재로는 ‘장미의 이름’의 살인사건이나 ‘건축무한육면각체의 비밀’의 이상의 시도 소재로 괜찮을 것 같습니다.',
        'XR 방탈출은 사도세자와 관련된 이야기를 소재로 진행되는 것으로 보입니다. 공간적 배경으로는 폴아웃의 볼트 같은 지하 대피소나 우주정거장처럼 폐쇄된 공간을, 이야기 소재로는 ‘장미의 이름’의 살인사건이나 ‘건축무한육면각체의 비밀’에서 다룬 이상의 시를 고려해봐도 좋을 것 같습니다.',
    ),
    (
        'CAVE 미술의 경우 사용자들이 부적절한 그림을 그렸을 경우 대처를 질문하였고 이에 대해 관리 기능 추가가 필요하다고 우탁 교수님께서 답변해주셨습니다. 이외에 주기적으로 초기화되는 콘텐츠도 예시로 제시되었습니다.',
        'CAVE 미술에서는 사용자가 부적절한 그림을 그렸을 때의 대처 방안을 질문했습니다. 이에 대해 우탁 교수님께서 관리 기능을 추가할 필요가 있다고 답변해 주셨습니다. 이 밖에 주기적으로 초기화되는 콘텐츠도 예시로 제시되었습니다.',
    ),
    (
        '창의성 실험에서 자유 주제로 진행할 경우 주제에 따라 인공지능의 결과물이 달라질 수 있으므로 주제를 좁히거나 유형을 나누어서 진행하는 것이 좋을 것 같습니다.',
        '창의성 실험을 자유 주제로 진행할 경우, 주제에 따라 인공지능의 결과물이 달라질 수 있으므로 주제의 범위를 좁히거나 유형별로 나누어 진행하면 좋을 것 같습니다.',
    ),
    (
        '학습에서 파트너 유형의 구분만 있는데 학습은 양방향 정보소통이기 때문에 사용자 유형도 구분하는 것이 좋을 것이라 생각합니다.',
        '학습에서는 파트너 유형만 구분하고 있으나, 양방향 정보 소통이라는 학습의 특성을 고려해 사용자 유형도 함께 구분하면 좋을 것으로 생각합니다.',
    ),
    (
        '파트너 유형이 어투의 차이만 있는데 동일한 어투더라도 교수법에 따라 차이가 발생할 수 있으므로 이러한 내용도 고려되면 좋겠습니다. 개인적으로 운동을 배울 때 같은 엄격한 말투로 지도받더라도 중간마다 적절한 휴식, 피드백을 받을 때 더 큰 효과를 본 적이 있었습니다. 대학교 수업 때도 전문 지식을 주욱 늘어놓으시는 교수님도 계셨고 토론을 통해 사고를 유도하시는 교수님도 계셨는데 모두 내용이 머릿속에 잘 들어왔던 경험도 있었습니다.',
        '파트너 유형이 어투의 차이로만 구분되어 있으나, 같은 어투라도 교수법에 따라 차이가 나타날 수 있으므로 이 점도 고려하면 좋겠습니다. 개인적으로 운동을 배울 때 같은 엄격한 말투로 지도를 받더라도, 중간중간 적절한 휴식과 피드백이 제공되었을 때 더 큰 효과를 경험한 적이 있습니다. 대학교 수업에서도 전문 지식을 중심으로 설명하시는 교수님과 토론을 통해 사고를 유도하시는 교수님이 계셨으며, 두 방식 모두 내용을 이해하는 데 도움이 되었습니다.',
    ),
]

if not ORIGINAL.exists():
    ORIGINAL.write_bytes(TARGET.read_bytes())
before = ORIGINAL.read_text(encoding='utf-8-sig')
after = before
for old, new in EDITS:
    assert after.count(old) == 1, old
    after = after.replace(old, new, 1)

for pattern in [r'^\[발표자:.*$', r'^\|.*$', r'발표 내용\n\n([^\n]+)', r'\]\(([^)]+)\)']:
    assert re.findall(pattern, before, re.M) == re.findall(pattern, after, re.M), pattern
assert before.split('---', 2)[1] == after.split('---', 2)[1]
assert len(re.findall(r'^\[발표자:', after, re.M)) == 5
assert len(re.findall(r'발표 내용\n\n([^\n]+)', after)) == 5

stage = after.replace('sources: []\n', 'sources: []\ntarget_folder: 03_Articles\n', 1)
if '--publish' in sys.argv:
    assert TARGET.read_bytes() == ORIGINAL.read_bytes(), 'Original changed; publication stopped.'
    assert DRAFT.read_text(encoding='utf-8') == stage, 'Draft differs from reviewed text.'
    TARGET.write_bytes(after.encode('utf-8'))
    print('Published tone edits. Existing frontmatter preserved.')
elif '--verify' in sys.argv:
    assert TARGET.read_text(encoding='utf-8') == after
    assert DRAFT.read_text(encoding='utf-8') == stage
    print('Published text matches reviewed draft.')
else:
    DRAFT.write_bytes(stage.encode('utf-8'))
    print('Draft created from the current replacement document.')
print('Checked: 9 feedback paragraphs edited; 5 presenter entries, 5 presentation summaries, image tables, links and existing frontmatter preserved.')
