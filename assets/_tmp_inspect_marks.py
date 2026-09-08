"""extract per-cell borderFillIDRef for schedule tables 5/6/7 with full grid expansion."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
HWPX = ROOT / "assets" / "3.hwpx"

NS_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS_HH = "http://www.hancom.co.kr/hwpml/2011/head"


def cell_text(tc):
    sub = tc.find(f"{{{NS_HP}}}subList")
    if sub is None:
        return ""
    out = []
    for p in sub.findall(f"{{{NS_HP}}}p"):
        for run in p.findall(f"{{{NS_HP}}}run"):
            for child in run.iter():
                if child.tag.split("}",1)[-1] == "t":
                    out.append(child.text or "")
    return "".join(out).strip()


def main():
    with zipfile.ZipFile(HWPX) as zf:
        section = ET.fromstring(zf.read("Contents/section0.xml"))

    tbl_idx = 0
    for p in section.findall(f"{{{NS_HP}}}p"):
        for run in p.findall(f"{{{NS_HP}}}run"):
            for child in run.iter():
                if child.tag.split("}",1)[-1] != "tbl":
                    continue
                tbl_idx += 1
                if tbl_idx not in (5, 6, 7):
                    continue
                rows = []
                for tr in child.findall(f"{{{NS_HP}}}tr"):
                    cells = []
                    for tc in tr.findall(f"{{{NS_HP}}}tc"):
                        span = tc.find(f"{{{NS_HP}}}cellSpan")
                        cs = int(span.attrib.get("colSpan", "1")) if span is not None else 1
                        rs = int(span.attrib.get("rowSpan", "1")) if span is not None else 1
                        cells.append({
                            "text": cell_text(tc),
                            "cs": cs, "rs": rs,
                            "bf": tc.attrib.get("borderFillIDRef", ""),
                        })
                    rows.append(cells)

                # Build full grid
                n_rows = len(rows)
                n_cols = sum(c["cs"] for c in rows[0]) if rows else 0
                grid = [[None] * n_cols for _ in range(n_rows)]
                for ri, row in enumerate(rows):
                    ci = 0
                    for c in row:
                        while ci < n_cols and grid[ri][ci] is not None:
                            ci += 1
                        for dr in range(c["rs"]):
                            for dc in range(c["cs"]):
                                if ri+dr < n_rows and ci+dc < n_cols:
                                    grid[ri+dr][ci+dc] = c
                        ci += c["cs"]

                print(f"=== TBL {tbl_idx}: rows={n_rows}, cols={n_cols} ===")
                # Header rows: 0, 1
                # Body starts at row 2
                # Col 0 = name; cols 1..12 = month marks
                for ri in range(n_rows):
                    line = []
                    for ci in range(n_cols):
                        c = grid[ri][ci]
                        if c is None:
                            line.append("---")
                        else:
                            txt = c["text"] or ""
                            if ci == 0:
                                line.append(f"[{c['bf']}] {txt[:35]}")
                            else:
                                line.append(c["bf"])
                    print(f"  R{ri}: " + " | ".join(line))
                print()


if __name__ == "__main__":
    main()
