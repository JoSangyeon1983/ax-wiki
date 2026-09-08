"""build clean markdown for ref 4 from 4.hwpx with rowSpan expansion."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
HWPX = ROOT / "assets" / "4.hwpx"
OUT = ROOT / "03_References" / "_locked" / "ref 4. 마일스톤 체계 및 수행계획.md"

NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}


def text_of(p_elem):
    parts = []
    for run in p_elem.findall(f"{{{NS['hp']}}}run"):
        for child in run.iter():
            tag = child.tag.split("}", 1)[-1]
            if tag == "t":
                parts.append(child.text or "")
            elif tag == "lineBreak":
                parts.append("\n")
    return "".join(parts).strip()


def cell_lines(tc):
    sub = tc.find(f"{{{NS['hp']}}}subList")
    if sub is None:
        return []
    out = []
    for p in sub.findall(f"{{{NS['hp']}}}p"):
        t = text_of(p)
        if t:
            out.append(t)
    return out


def extract_table(tbl):
    """Return raw rows: list of list of dicts {text, cs, rs}."""
    rows = []
    for tr in tbl.findall(f"{{{NS['hp']}}}tr"):
        cells = []
        for tc in tr.findall(f"{{{NS['hp']}}}tc"):
            span = tc.find(f"{{{NS['hp']}}}cellSpan")
            cs = int(span.attrib.get("colSpan", "1")) if span is not None else 1
            rs = int(span.attrib.get("rowSpan", "1")) if span is not None else 1
            lines = cell_lines(tc)
            cells.append({"lines": lines, "cs": cs, "rs": rs})
        rows.append(cells)
    return rows


def expand_grid(raw_rows):
    """Expand rowSpan/colSpan into a 2D grid with each cell repeated.

    Returns: list of list of {lines, is_continuation}.
    """
    n_rows = len(raw_rows)
    if n_rows == 0:
        return []
    n_cols = sum(c["cs"] for c in raw_rows[0])
    grid = [[None] * n_cols for _ in range(n_rows)]
    for ri, row in enumerate(raw_rows):
        ci = 0
        for cell in row:
            while ci < n_cols and grid[ri][ci] is not None:
                ci += 1
            for dr in range(cell["rs"]):
                for dc in range(cell["cs"]):
                    if ri + dr < n_rows and ci + dc < n_cols:
                        grid[ri + dr][ci + dc] = {
                            "lines": cell["lines"],
                            "is_origin": (dr == 0 and dc == 0),
                        }
            ci += cell["cs"]
    return grid


def render_table(raw_rows, repeat_groups=True):
    """Render a milestone-style table to markdown.

    repeat_groups: if True, repeat 개발 목표 (col 0) on every row for readability.
    """
    grid = expand_grid(raw_rows)
    if not grid:
        return ""
    n_cols = len(grid[0])
    headers = [" / ".join(g["lines"]) if g else "" for g in grid[0]]
    out = []
    out.append("| " + " | ".join(h.replace("|", "\\|") or " " for h in headers) + " |")
    out.append("| " + " | ".join(["---"] * n_cols) + " |")
    for ri in range(1, len(grid)):
        cells = []
        for ci in range(n_cols):
            cell = grid[ri][ci]
            if cell is None:
                cells.append(" ")
                continue
            text = "<br>".join(cell["lines"])
            if not repeat_groups and not cell["is_origin"]:
                text = ""
            cells.append(text.replace("|", "\\|") or " ")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    with zipfile.ZipFile(HWPX) as zf:
        section_xml = zf.read("Contents/section0.xml")
    root = ET.fromstring(section_xml)

    tables = []
    for p in root.findall(f"{{{NS['hp']}}}p"):
        for run in p.findall(f"{{{NS['hp']}}}run"):
            for child in run.iter():
                tag = child.tag.split("}", 1)[-1]
                if tag == "tbl":
                    tables.append(extract_table(child))

    # Expected: T1 title, T2 stage1, T3 "1단계" label, T4 "2단계" label,
    # T5 stage2, T6 "3단계" label, T7 stage3
    assert len(tables) == 7, f"unexpected table count: {len(tables)}"
    stage1 = render_table(tables[1])
    stage2 = render_table(tables[4])
    stage3 = render_table(tables[6])

    body = []
    body.append("---")
    body.append("title: 마일스톤 체계 및 수행계획")
    body.append("tags: [reference, RFP, 연구개발계획서, KOCCA, 실감AX, 마일스톤]")
    body.append("created: 2026-05-08")
    body.append("updated: 2026-05-08")
    body.append("source: assets/4.hwpx")
    body.append("---")
    body.append("")
    body.append("# 4. 마일스톤 체계 및 수행계획")
    body.append("")
    body.append("> 본 문서는 `assets/4.hwpx`의 마일스톤 표를 마크다운으로 옮긴 원문 사본임. "
                "원본의 표는 단계(1/2/3차년도)별로 구분되며, 각 단계마다 동일한 8열 구조"
                "(개발 목표 / 번호 / 마일스톤 명 / 목표일정 / 핵심수행기관 / 주요 가시적 결과물 / 점검기준 / 점검방법)를 따름. "
                "원문에서 병합되어 있던 셀(`rowSpan`)은 가독성을 위해 각 행에 값을 반복하여 펼침.")
    body.append("")
    body.append("> 표기 주의 — 원문에 보이는 일정 표기 오류(예: 3단계 일부 일정이 `28.xx ~ 27.xx` 또는 `28.xx~26.xx`로 적힌 부분, 4.2의 `26.09 ~ 26.12`, 11.2의 `ㅍ미디어월–AR` 오타 등)는 **원문 그대로 옮김**. 임의 수정하지 않음.")
    body.append("")
    body.append("## 4-1. 1단계 (1차년도, 2026.04~2026.12)")
    body.append("")
    body.append(stage1)
    body.append("")
    body.append("## 4-2. 2단계 (2차년도, 2027.01~2027.12)")
    body.append("")
    body.append(stage2)
    body.append("")
    body.append("## 4-3. 3단계 (3차년도, 2028.01~2028.12)")
    body.append("")
    body.append(stage3)
    body.append("")

    OUT.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote: {OUT}")
    print(f"size: {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
