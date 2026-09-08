"""dig into header.xml borderFill structures + sample cell IDRefs."""
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


def main():
    with zipfile.ZipFile(HWPX) as zf:
        header_raw = zf.read("Contents/header.xml")
        section_raw = zf.read("Contents/section0.xml")

    header = ET.fromstring(header_raw)
    # collect all borderFills
    bf_elems = list(header.iter(f"{{{NS_HH}}}borderFill"))
    print(f"borderFill count: {len(bf_elems)}")
    for bf in bf_elems[:5]:
        bf_id = bf.attrib.get("id", "")
        print(f"\n--- bf id={bf_id} ---")
        print(f"  tag attrs: {bf.attrib}")
        for child in bf:
            print(f"  <{child.tag.split('}',1)[-1]}> {child.attrib}")
            for sub in child:
                print(f"    <{sub.tag.split('}',1)[-1]}> {sub.attrib}")
                for ssub in sub:
                    print(f"      <{ssub.tag.split('}',1)[-1]}> {ssub.attrib}")

    # now find the schedule tables and dump distinct borderFillIDRef values
    section = ET.fromstring(section_raw)
    tbl_idx = 0
    for p in section.findall(f"{{{NS_HP}}}p"):
        for run in p.findall(f"{{{NS_HP}}}run"):
            for child in run.iter():
                if child.tag.split("}",1)[-1] == "tbl":
                    tbl_idx += 1
                    if tbl_idx not in (5, 6, 7):
                        continue
                    bf_seen = {}
                    for tr in child.findall(f"{{{NS_HP}}}tr"):
                        for tc in tr.findall(f"{{{NS_HP}}}tc"):
                            bid = tc.attrib.get("borderFillIDRef", "")
                            bf_seen[bid] = bf_seen.get(bid, 0) + 1
                    print(f"\nTBL {tbl_idx} cell borderFillIDRef distribution: {sorted(bf_seen.items(), key=lambda x: -x[1])}")

    # dump full borderFill list with key attrs
    print("\n# All borderFills:")
    for bf in bf_elems:
        bf_id = bf.attrib.get("id", "")
        # find slash/backSlash
        slash = bf.find(f"{{{NS_HH}}}slash")
        bs = bf.find(f"{{{NS_HH}}}backSlash")
        slash_t = slash.attrib.get("Type", slash.attrib.get("type", "NONE")) if slash is not None else "-"
        bs_t = bs.attrib.get("Type", bs.attrib.get("type", "NONE")) if bs is not None else "-"
        # find any winBrush face color
        wb = bf.find(f".//{{{NS_HH}}}winBrush")
        face = wb.attrib.get("faceColor", "") if wb is not None else ""
        # find fillBrush type
        fb = bf.find(f"{{{NS_HH}}}fillBrush")
        fb_type = fb.attrib.get("type", "-") if fb is not None else "-"
        print(f"  id={bf_id:>3} slash={slash_t} backSlash={bs_t} fillBrush.type={fb_type} winBrush.faceColor={face}")


if __name__ == "__main__":
    main()
