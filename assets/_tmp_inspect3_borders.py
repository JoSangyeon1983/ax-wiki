"""inspect 3.hwpx schedule tables (TBL 5/6/7) cell borderFillIDRef classification."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
HWPX = ROOT / "assets" / "3.hwpx"

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}


def text_of_cell(tc):
    sub = tc.find(f"{{{NS['hp']}}}subList")
    if sub is None:
        return ""
    out = []
    for p in sub.findall(f"{{{NS['hp']}}}p"):
        for run in p.findall(f"{{{NS['hp']}}}run"):
            for child in run.iter():
                tag = child.tag.split("}", 1)[-1]
                if tag == "t":
                    out.append(child.text or "")
    return "".join(out).strip()


def parse_borderfills(zf):
    """Return {id -> classification}: 'X' (slash+backSlash), 'WHITE' (winBrush white), 'FILL' (other).
    """
    raw = zf.read("Contents/header.xml")
    root = ET.fromstring(raw)
    out = {}
    for bf in root.iter(f"{{{NS['hh']}}}borderFill"):
        bf_id = bf.attrib.get("id", "")
        # check diagonals
        slash = bf.find(f"{{{NS['hh']}}}slash")
        backslash = bf.find(f"{{{NS['hh']}}}backSlash")
        slash_type = slash.attrib.get("type", "NONE") if slash is not None else "NONE"
        bs_type = backslash.attrib.get("type", "NONE") if backslash is not None else "NONE"
        # check fill
        fill = bf.find(f"{{{NS['hh']}}}fillBrush")
        win_brush = bf.find(f"{{{NS['hh']}}}winBrush") if fill is None else fill.find(f"{{{NS['hh']}}}winBrush")
        # try also direct winBrush
        if win_brush is None:
            win_brush = bf.find(f".//{{{NS['hh']}}}winBrush")
        face_color = win_brush.attrib.get("faceColor", "") if win_brush is not None else ""

        if slash_type != "NONE" and bs_type != "NONE":
            cls = "X"
        elif win_brush is not None and face_color.upper() == "#FFFFFF":
            cls = "WHITE"
        elif win_brush is not None:
            cls = f"FILL({face_color})"
        else:
            cls = "DEFAULT"
        out[bf_id] = cls
    return out


def render_table(tbl, bf_map, n_cols=13):
    rows = []
    for tr in tbl.findall(f"{{{NS['hp']}}}tr"):
        cells = []
        for tc in tr.findall(f"{{{NS['hp']}}}tc"):
            span = tc.find(f"{{{NS['hp']}}}cellSpan")
            cs = int(span.attrib.get("colSpan", "1")) if span is not None else 1
            rs = int(span.attrib.get("rowSpan", "1")) if span is not None else 1
            bf_id = tc.attrib.get("borderFillIDRef", "")
            cls = bf_map.get(bf_id, "?")
            cells.append({
                "text": text_of_cell(tc),
                "cs": cs, "rs": rs,
                "bf_id": bf_id, "bf_cls": cls,
            })
        rows.append(cells)
    return rows


def main():
    with zipfile.ZipFile(HWPX) as zf:
        bf_map = parse_borderfills(zf)
        section_xml = zf.read("Contents/section0.xml")
    print(f"# borderFill classifications:")
    seen = sorted(set(bf_map.values()))
    for s in seen:
        ids = [k for k, v in bf_map.items() if v == s]
        print(f"  {s}: ids={ids[:30]}{'...' if len(ids)>30 else ''} (count={len(ids)})")
    print()

    root = ET.fromstring(section_xml)
    tbl_idx = 0
    for p in root.findall(f"{{{NS['hp']}}}p"):
        for run in p.findall(f"{{{NS['hp']}}}run"):
            for child in run.iter():
                if child.tag.split("}",1)[-1] == "tbl":
                    tbl_idx += 1
                    if tbl_idx not in (5, 6, 7):
                        continue
                    rows = render_table(child, bf_map)
                    print(f"=== TBL {tbl_idx} ({len(rows)} rows) ===")
                    for ri, row in enumerate(rows):
                        if ri < 2:
                            # header rows
                            cell_repr = " | ".join(f"{c['text'][:30]}" for c in row)
                            print(f"  R{ri}: {cell_repr}")
                            continue
                        # name col + 12 month cells
                        name = row[0]["text"]
                        marks = []
                        for c in row[1:]:
                            cls = c["bf_cls"]
                            if cls == "X":
                                marks.append("X")
                            elif cls == "WHITE":
                                marks.append("·")
                            elif cls.startswith("FILL"):
                                marks.append("■")
                            else:
                                marks.append("?")
                        print(f"  R{ri}: name='{name[:50]}' | marks={' '.join(marks)} (■={marks.count('■')}, ·={marks.count('·')})")
                    n_fill = sum(1 for r in rows[2:] for c in r[1:] if c['bf_cls'].startswith('FILL'))
                    n_white = sum(1 for r in rows[2:] for c in r[1:] if c['bf_cls'] == 'WHITE')
                    n_x = sum(1 for r in rows[2:] for c in r[1:] if c['bf_cls'] == 'X')
                    print(f"  TOTALS: ■={n_fill}, ·={n_white}, X={n_x}")
                    print()


if __name__ == "__main__":
    main()
