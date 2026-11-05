"""Create editable draw.io flowcharts and render their XML to PNG with Pillow.

The XML is the editing master. Rendering reads the saved XML, not a second
copy of the flow graph. This renderer supports the styles used here only.
"""
from pathlib import Path
from html import escape, unescape
import math
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "작업 중"
FONT = Path("C:/Windows/Fonts/malgun.ttf")
BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
BASE = "whiteSpace=wrap;html=1;fontFamily=Malgun Gothic;fontSize=20;align=center;verticalAlign=middle;spacing=7;strokeWidth=1.6;"
PALETTE = {
    "process": ("#FFFFFF", "#64748B", "#0F172A"),
    "start": ("#E2E8F0", "#334155", "#0F172A"),
    "play": ("#EFF6FF", "#2563EB", "#1E3A8A"),
    "decision": ("#FFFBEB", "#D97706", "#92400E"),
    "finish": ("#FEF2F2", "#DC2626", "#991B1B"),
}


class Chart:
    def __init__(self, title, width, height):
        self.title, self.width, self.height = title, width, height
        self.file = ET.Element("mxfile", host="app.diagrams.net")
        diagram = ET.SubElement(self.file, "diagram", id=title.split()[1].lower(), name=title)
        model = ET.SubElement(diagram, "mxGraphModel", dx=str(width), dy=str(height), grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(width), pageHeight=str(height), math="0", shadow="0", background="#FFFFFF")
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")
        self.boxes = {}
        self.cell("panel", "", "rounded=1;arcSize=3;fillColor=#F8FAFC;strokeColor=#CBD5E1;strokeWidth=1;", (32, 84, width - 64, height - 116))
        self.cell("title", title, BASE + "text;fillColor=none;strokeColor=none;fontSize=26;fontStyle=1;fontColor=#0F172A;", (40, 24, width - 80, 44))

    def cell(self, ident, value, style, box):
        c = ET.SubElement(self.root, "mxCell", id=ident, value=value, style=style, vertex="1", parent="1")
        x, y, w, h = box
        ET.SubElement(c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), attrib={"as": "geometry"})
        self.boxes[ident] = box

    def node(self, ident, title, subtitle, box, kind="process"):
        fill, stroke, text = PALETTE[kind]
        shape = "rhombus;spacing=2;" if kind == "decision" else "rounded=1;arcSize=12;"
        if kind == "start":
            shape = "rounded=1;arcSize=50;absoluteArcSize=1;"
        value = "<b>" + escape(title).replace("\n", "<br>") + "</b>"
        if subtitle:
            value += '<br><span style="font-size:16px">' + escape(subtitle).replace("\n", "<br>") + "</span>"
        self.cell(ident, value, BASE + shape + f"fillColor={fill};strokeColor={stroke};fontColor={text};", box)

    def edge(self, ident, source, target, exit_point=(.5, 1), entry_point=(.5, 0), bends=(), color="#64748B", label=None):
        style = ("edgeStyle=none;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=1.7;"
                 f"strokeColor={color};exitX={exit_point[0]};exitY={exit_point[1]};exitPerimeter=0;entryX={entry_point[0]};entryY={entry_point[1]};entryPerimeter=0;")
        c = ET.SubElement(self.root, "mxCell", id=ident, value="", style=style, edge="1", parent="1", source=source, target=target)
        g = ET.SubElement(c, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if bends:
            a = ET.SubElement(g, "Array", attrib={"as": "points"})
            for x, y in bends:
                ET.SubElement(a, "mxPoint", x=str(x), y=str(y))
        if label:
            value, x, y = label
            self.cell(ident + "-label", value, BASE + f"text;fillColor=none;strokeColor=none;fontSize=17;fontStyle=1;fontColor={color};spacing=0;", (x - 40, y - 15, 80, 30))

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / (self.title + ".drawio.xml")
        if path.exists():
            raise FileExistsError(f"Existing editing master will not be overwritten: {path}")
        ET.indent(self.file, space="  ")
        ET.ElementTree(self.file).write(path, encoding="UTF-8", xml_declaration=True)
        render(path)


def styles(cell):
    result = {}
    for item in cell.get("style", "").split(";"):
        key, _, value = item.partition("=")
        if key:
            result[key] = value or True
    return result


def render(path):
    tree = ET.parse(path)
    model = tree.find(".//mxGraphModel")
    cells = {c.get("id"): c for c in tree.findall(".//mxCell")}
    scale = 3
    size = (int(model.get("pageWidth")), int(model.get("pageHeight")))
    image = Image.new("RGB", (size[0] * scale, size[1] * scale), "white")
    draw = ImageDraw.Draw(image)

    def point(p):
        return tuple(round(v * scale) for v in p)

    def box(c):
        g = c.find("mxGeometry")
        return tuple(float(g.get(k, "0")) for k in ("x", "y", "width", "height"))

    def vertex(c):
        s = styles(c)
        x, y, w, h = box(c)
        fill = s.get("fillColor", "none")
        stroke = s.get("strokeColor", "none")
        fill = None if fill == "none" else fill
        stroke = None if stroke == "none" else stroke
        bounds = (point((x, y)), point((x + w, y + h)))
        line_width = max(1, round(float(s.get("strokeWidth", 1)) * scale))
        if "rhombus" in s:
            poly = [point((x + w / 2, y)), point((x + w, y + h / 2)), point((x + w / 2, y + h)), point((x, y + h / 2))]
            draw.polygon(poly, fill=fill)
            draw.line(poly + [poly[0]], fill=stroke, width=line_width, joint="curve")
        elif "rounded" in s:
            radius = 25 if s.get("absoluteArcSize") == "1" else min(w, h) * float(s.get("arcSize", 12)) / 100
            draw.rounded_rectangle(bounds, radius=radius * scale, fill=fill, outline=stroke, width=line_width)
        elif fill or stroke:
            draw.rectangle(bounds, fill=fill, outline=stroke, width=line_width)
        value = c.get("value", "")
        if not value:
            return
        parts = re.split(r"<br\s*/?>", value)
        lines = []
        caption = False
        for part in parts:
            if "<span" in part:
                caption = True
            plain = unescape(re.sub(r"<[^>]*>", "", part))
            bold = ("<b>" in value and not caption) or s.get("fontStyle") == "1"
            font_size = 16 if caption else int(s.get("fontSize", 20))
            font = ImageFont.truetype(str(BOLD if bold else FONT), font_size * scale)
            if draw.textlength(plain, font=font) > (w - 10) * scale:
                raise ValueError(f"Label overflow: {plain}")
            lines.append((plain, font, font_size + 10))
        total = sum(v[2] for v in lines)
        top = y + (h - total) / 2
        for plain, font, line_height in lines:
            draw.text(point((x + w / 2, top + line_height / 2)), plain, font=font, anchor="mm", fill=s.get("fontColor", "#0F172A"))
            top += line_height

    vertex(cells["panel"])
    for c in cells.values():
        if c.get("edge") != "1":
            continue
        s = styles(c)
        source, target = cells[c.get("source")], cells[c.get("target")]
        sx, sy, sw, sh = box(source)
        tx, ty, tw, th = box(target)
        points = [(sx + sw * float(s["exitX"]), sy + sh * float(s["exitY"]))]
        points += [(float(p.get("x")), float(p.get("y"))) for p in c.findall(".//Array/mxPoint")]
        points += [(tx + tw * float(s["entryX"]), ty + th * float(s["entryY"]))]
        for a, b in zip(points, points[1:]):
            assert abs(a[0] - b[0]) < .01 or abs(a[1] - b[1]) < .01, (c.get("id"), a, b)
        draw.line([point(p) for p in points], fill=s["strokeColor"], width=round(1.7 * scale), joint="curve")
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        length, half_width = 10, 4.5
        back = (b[0] - math.cos(angle) * length, b[1] - math.sin(angle) * length)
        arrow = [b, (back[0] - math.sin(angle) * half_width, back[1] + math.cos(angle) * half_width), (back[0] + math.sin(angle) * half_width, back[1] - math.cos(angle) * half_width)]
        draw.polygon([point(p) for p in arrow], fill=s["strokeColor"])
    for c in cells.values():
        if c.get("vertex") == "1" and c.get("id") != "panel":
            vertex(c)
    target = path.with_name(path.name.removesuffix(".drawio.xml") + ".png")
    image.resize((size[0] * 2, size[1] * 2), Image.Resampling.LANCZOS).save(target)
    print(f"Saved {path.name} and {target.name}: {size[0] * 2} x {size[1] * 2}")


def main():
    ball = Chart("Cave Super Ball 전체 플로우", 840, 800)
    ball.node("start", "콘텐츠 진입", "", (300, 100, 240, 52), "start")
    ball.node("prepare", "라운드 준비", "벽돌, 점수와 공 초기화", (270, 204, 300, 76))
    ball.node("play", "플레이", "손으로 색 변경, 바닥으로 반사\n벽돌 파괴와 점수 획득", (270, 332, 300, 100), "play")
    ball.node("clear", "모든 벽돌\n파괴?", "", (300, 482, 240, 116), "decision")
    ball.node("restart", "라운드 완료", "공 정지 후 재시작 대기", (270, 654, 300, 76))
    ball.edge("enter", "start", "prepare")
    ball.edge("ready", "prepare", "play")
    ball.edge("check", "play", "clear")
    ball.edge("continue", "clear", "play", (0, .5), (0, .5), [(150, 540), (150, 382)], label=("아니오", 224, 519))
    ball.edge("complete", "clear", "restart", color="#16A34A", label=("예", 445, 625))
    ball.edge("reset", "restart", "prepare", (1, .5), (1, .5), [(710, 692), (710, 242)], label=("재시작", 644, 220))
    ball.save()

    action = Chart("Cave Action 전체 플로우", 1120, 1100)
    action.node("start", "콘텐츠 진입", "", (350, 100, 240, 52), "start")
    action.node("prepare", "게임 준비", "체력, 공격과 소행성 초기화", (320, 200, 300, 76))
    action.node("assign", "첫 턴 배정", "첫 공격자와 공격 방식 결정", (320, 326, 300, 76))
    action.node("play", "공격과 방어 플레이", "배정된 방식으로 공격과 회피\n피격 시 체력 감소", (320, 452, 300, 100), "play")
    action.node("health", "한쪽 체력\n소진?", "", (350, 602, 240, 116), "decision")
    action.node("turn", "턴 시간\n종료?", "", (350, 776, 240, 116), "decision")
    action.node("swap", "공수 교대", "체력 유지, 다음 공격 방식 배정", (320, 946, 300, 76), "play")
    action.node("finish", "게임 종료", "패배 연출과 GAME OVER", (730, 618, 320, 84), "finish")
    action.node("restart", "재시작 대기", "", (730, 794, 320, 76))
    action.edge("enter", "start", "prepare")
    action.edge("ready", "prepare", "assign")
    action.edge("first", "assign", "play")
    action.edge("hit", "play", "health")
    action.edge("alive", "health", "turn", label=("아니오", 510, 745))
    action.edge("timeup", "turn", "swap", color="#16A34A", label=("예", 496, 919))
    action.edge("continue", "turn", "play", (0, .5), (0, .68), [(240, 834), (240, 520)], label=("아니오", 294, 812))
    action.edge("nextturn", "swap", "play", (0, .5), (0, .24), [(150, 984), (150, 476)], color="#2563EB")
    action.edge("gameover", "health", "finish", (1, .5), (0, .5), color="#DC2626", label=("예", 660, 637))
    action.edge("wait", "finish", "restart", color="#DC2626")
    action.edge("reset", "restart", "prepare", (1, .5), (1, .5), [(1080, 832), (1080, 238)], label=("새 게임", 860, 216))
    action.save()


if __name__ == "__main__":
    main()
