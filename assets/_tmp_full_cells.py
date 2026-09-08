"""dump full cell content (no truncation) for 3.hwpx tables 2, 3, 4."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
HWPX = ROOT / "assets" / "3.hwpx"

NS_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"


def cell_lines(tc):
    sub = tc.find(f"{{{NS_HP}}}subList")
    if sub is None:
        return []
    out = []
    for p in sub.findall(f"{{{NS_HP}}}p"):
        # collect inline pic / nested table markers
        markers = []
        text_parts = []
        for run in p.findall(f"{{{NS_HP}}}run"):
            for child in run.iter():
                tag = child.tag.split("}",1)[-1]
                if tag == "pic":
                    markers.append("[PIC]")
                elif tag == "tbl":
                    markers.append("[NESTED_TBL]")
                elif tag == "t":
                    text_parts.append(child.text or "")
                elif tag == "lineBreak":
                    text_parts.append("\\n")
        prefix = (" ".join(markers) + " ") if markers else ""
        line = (prefix + "".join(text_parts)).strip()
        if line:
            out.append(line)
    return out


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
                if tbl_idx not in (2, 3, 4):
                    continue
                print(f"\n=== TBL {tbl_idx} ===")
                for ri, tr in enumerate(child.findall(f"{{{NS_HP}}}tr")):
                    for ci, tc in enumerate(tr.findall(f"{{{NS_HP}}}tc")):
                        span = tc.find(f"{{{NS_HP}}}cellSpan")
                        cs = int(span.attrib.get("colSpan", "1")) if span is not None else 1
                        rs = int(span.attrib.get("rowSpan", "1")) if span is not None else 1
                        lines = cell_lines(tc)
                        print(f"--- R{ri}C{ci} cs={cs} rs={rs} ---")
                        for L in lines:
                            print(f"    | {L}")


if __name__ == "__main__":
    main()
