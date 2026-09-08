"""inspect 3.hwpx full content (paragraphs + tables with rowSpan/colSpan)."""
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


def text_of(p_elem):
    parts = []
    for run in p_elem.findall(f"{{{NS['hp']}}}run"):
        for child in run.iter():
            tag = child.tag.split("}", 1)[-1]
            if tag == "t":
                parts.append(child.text or "")
            elif tag == "lineBreak":
                parts.append("\\n")
    return "".join(parts).strip()


def cell_text(tc):
    sub = tc.find(f"{{{NS['hp']}}}subList")
    if sub is None:
        return ""
    out = []
    for p in sub.findall(f"{{{NS['hp']}}}p"):
        # collect text and any nested tbl/pic markers
        markers = []
        for run in p.findall(f"{{{NS['hp']}}}run"):
            for child in run.iter():
                tag = child.tag.split("}", 1)[-1]
                if tag == "pic":
                    markers.append("[PIC]")
                elif tag == "tbl":
                    markers.append("[NESTED_TBL]")
        t = text_of(p)
        line = (" ".join(markers) + " " if markers else "") + t
        line = line.strip()
        if line:
            out.append(line)
    return " // ".join(out)


def main():
    with zipfile.ZipFile(HWPX) as zf:
        styles_xml = zf.read("Contents/header.xml")
        section_xml = zf.read("Contents/section0.xml")
    style_root = ET.fromstring(styles_xml)
    styles = {}
    for s in style_root.iter(f"{{{NS['hh']}}}style"):
        styles[s.attrib["id"]] = s.attrib.get("name", "")

    root = ET.fromstring(section_xml)

    tbl_idx = 0
    para_idx = 0
    for p in root.findall(f"{{{NS['hp']}}}p"):
        para_idx += 1
        sid = p.attrib.get("styleIDRef", "0")
        sname = styles.get(sid, "")
        text = text_of(p)
        # detect inline pics and tables
        has_pic = False
        tables = []
        for run in p.findall(f"{{{NS['hp']}}}run"):
            for child in run.iter():
                tag = child.tag.split("}", 1)[-1]
                if tag == "pic":
                    has_pic = True
                elif tag == "tbl":
                    tables.append(child)
        marker = "[PIC]" if has_pic else ""
        if text or marker or tables:
            head = f"P{para_idx} [{sname}]"
            print(f"{head}: {marker}{text[:200]}")
        for tbl in tables:
            tbl_idx += 1
            rows = []
            for tr in tbl.findall(f"{{{NS['hp']}}}tr"):
                cells = []
                for tc in tr.findall(f"{{{NS['hp']}}}tc"):
                    span = tc.find(f"{{{NS['hp']}}}cellSpan")
                    cs = int(span.attrib.get("colSpan", "1")) if span is not None else 1
                    rs = int(span.attrib.get("rowSpan", "1")) if span is not None else 1
                    cells.append({"text": cell_text(tc), "cs": cs, "rs": rs})
                rows.append(cells)
            print(f"\n=== TBL {tbl_idx} (P{para_idx}, {len(rows)} rows) ===")
            for ri, row in enumerate(rows):
                cell_repr = " | ".join(f"[cs={c['cs']} rs={c['rs']}] {c['text'][:80]}" for c in row)
                print(f"  R{ri}: {cell_repr}")
            print()


if __name__ == "__main__":
    main()
