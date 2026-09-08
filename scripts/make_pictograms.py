# -*- coding: utf-8 -*-
"""덧뵈기 프로토타입 동작 픽토그램 9종을 그림 (prototype/덧뵈기-나만의탈춤-프로토타입.html이 씀).

실행: python scripts/make_pictograms.py
    prototype/assets/픽토_*.png 9개를 덮어씀.

그리는 기준
  - 동작 내용은 프로토타입 MOVES[].how(실기기에서 유저가 하는 몸짓)를 따름
  - 22px(동작 목록), 32px(가이드 레인), 52px(입력부 제시)로 줄어도 읽혀야 하므로
    선을 굵게 하고 실루엣을 단순하게 둠. 팔다리가 머리에 붙으면 작은 크기에서
    덩어리로 뭉쳐 안 읽히므로 반드시 띄움
  - 한 마당의 동작 3개는 실루엣이 서로 달라야 함 (같은 화면에서 골라야 하므로)
  - PIL은 도형을 부드럽게 그리지 않아 4배 크기로 그린 뒤 줄여 계단현상을 없앰
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "prototype", "assets")
SIZE, SS = 256, 4          # 최종 256px, 4배 supersampling
W = SIZE * SS
GOLD = (224, 192, 112, 255)
STROKE = 21                # 최종 기준 선 굵기
HEAD_R = 23

def S(v):        return int(round(v * SS))
def P(pts):      return [(S(x), S(y)) for x, y in pts]

class Pen:
    def __init__(self):
        self.img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
    def line(self, pts, w=STROKE, cap=True):
        p, sw = P(pts), S(w)
        self.d.line(p, fill=GOLD, width=sw, joint="curve")
        if cap:                                  # 둥근 끝 처리
            for x, y in p:
                r = sw // 2
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD)
    def dot(self, c, r):
        x, y = S(c[0]), S(c[1]); r = S(r)
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD)
    def ring(self, c, r, w=STROKE):
        x, y = S(c[0]), S(c[1]); r = S(r)
        self.d.ellipse([x - r, y - r, x + r, y + r], outline=GOLD, width=S(w))
    def poly(self, pts):
        self.d.polygon(P(pts), fill=GOLD)
    def arc(self, c, r, a0, a1, w=STROKE):
        x, y = S(c[0]), S(c[1]); r = S(r)
        self.d.arc([x - r, y - r, x + r, y + r], a0, a1, fill=GOLD, width=S(w))
    def curve(self, pts, w=STROKE, steps=48):
        """제어점 3개 이상을 지나는 부드러운 곡선 (Catmull-Rom)"""
        p = list(pts)
        p = [p[0]] + p + [p[-1]]
        out = []
        for i in range(len(p) - 3):
            p0, p1, p2, p3 = p[i], p[i+1], p[i+2], p[i+3]
            for s in range(steps + 1):
                t = s / steps; t2, t3 = t*t, t*t*t
                out.append((
                    .5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
                    .5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)))
        self.line(out, w, cap=False)
        self.dot(out[0], w/2); self.dot(out[-1], w/2)

def head(pen, c):
    pen.dot(c, HEAD_R)

# ── 동작 9종 ─────────────────────────────────────────
# 각 함수는 MOVES[].how(실기기 몸짓)를 그림으로 옮긴 것임

def chikyeo(pen):        # 기막히다는 듯 한 팔을 머리 위로 치켜들고 상체를 숙인 채 버팀
    # 치켜든 손은 머리보다 확실히 위에 둠. 그 높이 하나로 다른 동작과 갈림
    head(pen, (104, 108))
    pen.line([(110, 132), (134, 190)])                  # 앞으로 숙인 몸통
    pen.line([(134, 190), (108, 240)])                  # 다리
    pen.line([(134, 190), (166, 238)])
    pen.line([(122, 146), (176, 104), (186, 40)])       # 머리 위로 치켜든 팔
    pen.dot((186, 28), 15)                              # 펴 보인 손바닥
    pen.line([(118, 150), (66, 176)])                   # 다른 팔은 아래로

def jjilleo(pen):        # 팔을 앞으로 힘껏 뻗어 찌름
    head(pen, (86, 76))
    pen.line([(88, 100), (94, 172)])
    pen.line([(94, 172), (58, 232)])                    # 뒷다리
    pen.line([(94, 172), (152, 224)])                   # 내디딘 앞다리
    pen.line([(90, 116), (206, 116)])                   # 곧게 뻗은 팔
    pen.dot((214, 116), 15)                             # 내지른 주먹
    pen.line([(90, 118), (56, 156)])                    # 뒤로 당긴 팔

def hwidulleo(pen):      # 팔을 좌우로 크고 빠르게 휘둘러 쫓음
    head(pen, (128, 88))
    pen.line([(128, 114), (128, 180)])
    pen.line([(128, 180), (100, 234)])
    pen.line([(128, 180), (156, 234)])
    pen.line([(128, 128), (196, 96)])                   # 휘두르는 팔
    pen.line([(128, 128), (66, 116)])
    pen.arc((128, 108), 96, 200, 250, w=STROKE - 8)     # 좌우 휘두름 자취
    pen.arc((128, 108), 96, 290, 340, w=STROKE - 8)

def geodeureum(pen):     # 상체를 뒤로 젖혀 거드름 피우는 자세로 버팀
    # 팔꿈치를 양옆으로 크게 벌려 짚어 거들먹거리는 실루엣을 만듦
    head(pen, (146, 62))
    pen.curve([(142, 86), (162, 128), (140, 180)], w=STROKE)    # 배를 내민 상체
    pen.line([(140, 180), (110, 236)])
    pen.line([(140, 180), (172, 234)])
    pen.line([(150, 108), (208, 138), (156, 168)])      # 오른쪽 허리 짚음
    pen.line([(146, 110), (86, 140), (132, 172)])       # 왼쪽 허리 짚음

def satdae(pen):         # 팔을 뻗어 가리킨 채 버팀
    head(pen, (98, 92))
    pen.line([(98, 118), (100, 184)])
    pen.line([(100, 184), (74, 234)])
    pen.line([(100, 184), (130, 234)])
    pen.line([(100, 132), (168, 88), (216, 54)])        # 위로 뻗어 가리킴
    pen.dot((224, 46), 13)                              # 가리키는 끝
    pen.line([(100, 134), (66, 178)])

def chaejjik(pen):       # 말채찍 쥔 팔을 좌우로 크게 휘두름
    head(pen, (112, 116))
    pen.line([(112, 142), (114, 196)])
    pen.line([(114, 196), (88, 240)])
    pen.line([(114, 196), (142, 240)])
    pen.line([(112, 156), (152, 120)])                  # 채찍 쥔 팔
    pen.curve([(152, 120), (206, 74), (168, 34), (104, 44), (74, 78)], w=STROKE - 7)  # 채찍
    pen.line([(112, 158), (76, 190)])

def eokkae(pen):         # 팔을 어깨 위로 얹은 채 버팀
    # 팔꿈치를 옆으로 빼고 아래팔을 곧게 세워 머리와 안 겹치게 함
    head(pen, (150, 78))
    pen.line([(150, 104), (146, 178)])
    pen.line([(146, 178), (118, 234)])
    pen.line([(146, 178), (178, 234)])
    pen.line([(148, 122), (84, 126), (84, 62)])         # 어깨 위로 세워 얹은 팔
    pen.line([(150, 126), (192, 168)])                  # 다른 팔은 아래로

def balchago(pen):       # 한 발을 높이 차올림
    head(pen, (96, 78))
    pen.line([(98, 102), (104, 170)])
    pen.line([(104, 170), (92, 238)])                   # 딛고 선 다리
    pen.line([(104, 170), (168, 128), (214, 94)])       # 차올린 다리
    pen.line([(100, 120), (54, 100)])                   # 균형 잡는 팔
    pen.line([(100, 124), (140, 96)])

def somae(pen):          # 장삼 소매를 좌우로 크게 뿌림
    # 소매는 채워진 나팔 모양으로 그림. 가는 선 고리보다 작게 줄여도 잘 읽힘
    head(pen, (128, 72))
    pen.line([(128, 96), (128, 170)])
    pen.line([(128, 170), (98, 232)])
    pen.line([(128, 170), (158, 232)])
    pen.line([(128, 114), (66, 100)])                   # 양팔
    pen.line([(128, 114), (190, 100)])
    pen.poly([(70, 86), (24, 128), (44, 176), (78, 150), (86, 110)])       # 펄럭이는 소매
    pen.poly([(186, 86), (232, 128), (212, 176), (178, 150), (170, 110)])

MOVES = [("손치켜들기", chikyeo), ("찔러보기", jjilleo), ("휘둘러쫓기", hwidulleo),
         ("거드름흉내", geodeureum), ("삿대질", satdae), ("채찍휘두르기", chaejjik),
         ("어깨메기", eokkae), ("한발차올리기", balchago), ("소매뿌리기", somae)]

os.makedirs(OUT, exist_ok=True)
for name, fn in MOVES:
    pen = Pen(); fn(pen)
    img = pen.img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(os.path.join(OUT, "픽토_%s.png" % name))
    print("픽토_%s.png" % name)
print("완료:", OUT)
