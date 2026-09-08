#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MD 기획서 -> 지정 양식 docx 변환기.

동작:
  1) MD 전처리: frontmatter 제거, 첫 H1 앞 내용 절단, 헤딩 한국 공문서 번호 제거
     (Word 자동 번호에 위임), 임베드 ![[파일#^블록]] 실제 내용 평탄화, 위키링크 [[ ]]
     표시 텍스트만 남김.
  2) pandoc: 전처리 MD -> 본문 content.docx (--reference-doc 로 양식 스타일 승계).
  3) 조립: 양식 docx 패키지를 베이스로, word/document.xml 을
     [양식 앞부분(표지/버전/목차) + 섹션 나누기] + [pandoc 본문] + [양식 최종 sectPr]
     로 교체. styles.xml 은 pandoc 상위집합으로, numbering.xml 은 양식+pandoc 병합으로 교체.
     푸터(페이지 -1- 부터), 페이지 설정, 표지 서식은 양식 그대로 보존.

사용법:
  python scripts/md_to_docx.py <입력.md> [출력.docx]

의존성: pandoc (PATH 또는 winget 경로), Python 표준 라이브러리만 사용.
"""

import sys
import os
import re
import glob
import shutil
import zipfile
import tempfile
import subprocess
import urllib.parse

# ---------------------------------------------------------------------------
# 경로
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.dirname(SCRIPT_DIR)  # scripts/ 의 상위 = vault root
TEMPLATE = os.path.join(
    VAULT, "assets", "무형문화유산 전승_기획서 양식_ver.0.0.2_20260721.docx"
)


def fail(msg):
    print("[오류] " + msg, file=sys.stderr)
    sys.exit(1)


def find_pandoc():
    """PATH 우선, 없으면 winget 설치 경로 탐색."""
    if shutil.which("pandoc"):
        return "pandoc"
    winget = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "WinGet", "Packages",
    )
    if os.path.isdir(winget):
        for d in os.listdir(winget):
            if d.startswith("JohnMacFarlane.Pandoc"):
                hits = glob.glob(os.path.join(winget, d, "pandoc-*", "pandoc.exe"))
                if hits:
                    return hits[0]
    for c in [
        os.path.join(os.environ.get("ProgramFiles", ""), "Pandoc", "pandoc.exe"),
        "/usr/bin/pandoc", "/usr/local/bin/pandoc",
    ]:
        if c and os.path.isfile(c):
            return c
    fail("pandoc 을 찾을 수 없음. winget install --id JohnMacFarlane.Pandoc 후 재시도.")


# ---------------------------------------------------------------------------
# MD 전처리
# ---------------------------------------------------------------------------

def strip_frontmatter(text):
    """맨 앞 YAML frontmatter(--- ... ---) 제거."""
    if text.startswith("---"):
        m = re.match(r"^---\r?\n.*?\r?\n---\r?\n", text, re.S)
        if m:
            return text[m.end():]
    return text


# 양식 표지의 부제 자리표시(변환 시 문서 title 로 치환). 문서 전체에 1회만 등장.
COVER_SUBTITLE_PLACEHOLDER = "덜미 전자책 변환"


def extract_frontmatter_title(md_path):
    """md frontmatter 의 title 값을 반환(없으면 None). 표지 부제 치환용."""
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    for line in m.group(1).split("\n"):
        tm = re.match(r"\s*title\s*:\s*(.+?)\s*$", line)
        if tm:
            t = tm.group(1).strip()
            if len(t) >= 2 and t[0] in "\"'" and t[-1] == t[0]:
                t = t[1:-1]  # 따옴표 제거
            return t
    return None


def strip_comments(text):
    """Obsidian 주석 %%...%% 구간 제거(인라인/블록 모두). 비탐욕 매칭이라
    가장 가까운 %% 쌍끼리 묶음. 짝이 안 맞는 홀수 %% 는 건드리지 않음."""
    return re.sub(r"%%.*?%%", "", text, flags=re.S)


def cut_before_first_h1(text):
    """첫 번째 H1(# ) 앞 내용(TL;DR 등) 절단. 첫 H1부터 옮김."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r"^#\s+\S", ln):
            return "\n".join(lines[i:])
    return text  # H1 없으면 원문 유지


def drop_h1_sections(text, numbers):
    """지정한 번호의 H1 절(# N. …)을 통째로 제거. numbers 예: {'11','12','13'}."""
    if not numbers:
        return text
    out = []
    skip = False
    for ln in text.split("\n"):
        if re.match(r"^#\s+\S", ln):  # H1 경계마다 skip 재판정
            m = re.match(r"^#\s+(\d+)\.\s", ln)
            skip = bool(m and m.group(1) in numbers)
        if not skip:
            out.append(ln)
    return "\n".join(out)


def drop_excluded_refs(text, numbers):
    """제외 절을 가리키는 댕글링 참조 정리(변환 시에만, 소스 MD 불변).

    (1) 문서맵 표에서 첫 셀이 제외 절인 행(`| §N …`) 삭제.
    (2) 줄 끝 괄호절에 제외 절 §참조가 들어 있으면 그 괄호절 삭제.
        예: `…정함(예시는 §13.다 8) 실패 안내)` -> `…정함`.
        괄호절 안 한글 서수의 `8)` 닫는 괄호와 충돌하지 않게 줄 끝(`$`)에만 적용.
    """
    if not numbers:
        return text
    alt = "|".join(sorted(numbers, key=len, reverse=True))
    row_re = re.compile(r"^\s*\|\s*§(?:" + alt + r")(?![0-9])\b")
    paren_re = re.compile(r"\s*\([^(]*§(?:" + alt + r")(?![0-9])[^(]*\)\s*$")
    out = []
    for ln in text.split("\n"):
        if row_re.match(ln):
            continue
        ln = paren_re.sub("", ln)
        out.append(ln)
    return "\n".join(out)


# 레벨별 헤딩 번호 접두 패턴 (선행 토큰만). 정본은 CONVENTIONS 4.2 헤딩 넘버링
# H1~H4는 리터럴 번호를 떼어 Word 멀티레벨 헤딩 자동번호(제목 1~4)에 위임함.
# H5(제목 5)는 양식에서 무번호 레벨(ilvl 4)이라, 접두를 떼면 번호 없이 제목만 렌더됨.
# H1은 `1.`이고 H2는 `1.1`이라, H1 패턴이 "1.1 핵심"을 먹지 않도록 마침표 뒤 공백을 요구함
_HEAD_NUM = {
    1: re.compile(r"^\d+\.\s+"),           # 1. 개요
    2: re.compile(r"^\d+\.\d+\s+"),        # 1.1 핵심 내용
    3: re.compile(r"^\d+\.\d+\.\d+\s+"),   # 1.1.1 세부 항목
    4: re.compile(r"^\d+\)\s+"),           # 1) 보충 설명  (번호 떼고 Word 자동번호에 위임)
    5: re.compile(r"^\(\d+\)\s+"),         # (1) 역할과 목적  (양식이 무번호라 번호 없이 렌더)
}


def strip_heading_numbers(text):
    """헤딩의 한국 공문서 번호 접두만 제거. 본문 속 숫자는 건드리지 않음."""
    out = []
    for ln in text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            level = len(m.group(1))
            title = m.group(2)
            pat = _HEAD_NUM.get(level)
            if pat:
                title = pat.sub("", title, count=1)
            out.append(m.group(1) + " " + title)
        else:
            out.append(ln)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 임베드 평탄화 (블록 ID)
# ---------------------------------------------------------------------------

_MD_INDEX = None


def _build_md_index():
    global _MD_INDEX
    if _MD_INDEX is not None:
        return
    _MD_INDEX = {}
    for p in glob.glob(os.path.join(VAULT, "**", "*.md"), recursive=True):
        name = os.path.splitext(os.path.basename(p))[0]
        _MD_INDEX.setdefault(name, p)  # 첫 매치 우선


def _find_md(name):
    _build_md_index()
    return _MD_INDEX.get(name)


# ---------------------------------------------------------------------------
# 이미지 임베드 -> 실제 이미지 경로
# ---------------------------------------------------------------------------

_IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
_IMG_INDEX = None


def _build_img_index():
    global _IMG_INDEX
    if _IMG_INDEX is not None:
        return
    _IMG_INDEX = {}
    for p in glob.glob(os.path.join(VAULT, "assets", "**", "*"), recursive=True):
        if os.path.isfile(p) and p.lower().endswith(_IMG_EXTS):
            parts = p.replace("\\", "/").split("/")
            _IMG_INDEX.setdefault("/".join(parts[-2:]), p)  # 폴더/파일
            _IMG_INDEX.setdefault(parts[-1], p)             # 파일명 폴백


def _find_img(partial):
    _build_img_index()
    partial = partial.replace("\\", "/").strip()
    return _IMG_INDEX.get(partial) or _IMG_INDEX.get(partial.split("/")[-1])


_IMG_EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")

# Obsidian 이미지 폭(px)을 Word 지면 물리 크기(cm)로 환산하는 배율.
# 사용자 기준: Obsidian 500px = Word 8cm (px->cm, 약 158.75 DPI 상당).
# px 를 96 DPI 로 그대로 쓰면(500px=13.2cm) Obsidian 화면 대비 지면에서 과대해짐.
PX_TO_CM = 8.0 / 500  # = 0.016 cm/px


def _img_embed_md(inner):
    """![[폴더/파일.png|너비]] 내부 텍스트 -> ![](절대경로){width=너비cm}.
    폭(px)은 PX_TO_CM 배율로 cm 환산(500px=8cm). 이미지가 아니면 None(잔류),
    경로 못 찾으면 ''(제거)."""
    inner = inner.strip()
    if "|" in inner:
        path_part, width = inner.rsplit("|", 1)
    else:
        path_part, width = inner, None
    path_part = path_part.strip()
    if not path_part.lower().endswith(_IMG_EXTS):
        return None  # 블록ID 등 비이미지 임베드는 resolve_embeds 로 넘김
    abspath = _find_img(path_part)
    if not abspath:
        print("[경고] 이미지 없음: " + path_part, file=sys.stderr)
        return ""
    attr = ""
    if width and width.strip().isdigit():
        attr = "{width=%.2fcm}" % (int(width.strip()) * PX_TO_CM)
    return "![](%s)%s" % (abspath.replace("\\", "/"), attr)


def resolve_image_embeds(text):
    """![[폴더/파일.png|너비]] -> ![](절대경로){width=너비px}. 비이미지 임베드는 잔류.

    리스트 항목의 들여쓰기된 줄(블릿 연속 줄)에 있는 이미지는 들여쓰기를
    보존하고 앞뒤 빈 줄을 넣지 않음. 빈 줄로 감싸고 열 0으로 내보내면 리스트가
    끊겨 블릿이 깨지기 때문. 최상위(들여쓰기 0) 단독 이미지만 앞뒤 빈 줄로 둘러
    pandoc 이 독립 그림 문단으로 렌더하게 함.
    """
    def repl(m):
        r = _img_embed_md(m.group(1))
        return m.group(0) if r is None else r

    out = []
    for ln in text.split("\n"):
        if not _IMG_EMBED_RE.search(ln):
            out.append(ln)
            continue
        replaced = _IMG_EMBED_RE.sub(repl, ln)
        if replaced == ln:  # 비이미지 임베드만 있어 치환 없음
            out.append(ln)
            continue
        lead = ln[: len(ln) - len(ln.lstrip())]
        standalone = _IMG_EMBED_RE.sub("", ln).strip() == ""  # 그 줄이 이미지뿐
        if standalone:
            # 단독 이미지는 앞뒤 빈 줄로 독립 문단화해 자기 줄에 옴.
            # 리스트 안(들여쓰기)이면 들여쓰기를 유지해 리스트 항목 내부 문단이
            # 되어 리스트를 안 깨고 새 줄에 옴(들여쓰기 없이 열 0으로 내보내면
            # 리스트가 끊김). 최상위면 그림 문단이 됨.
            out.extend(["", replaced if lead else replaced.strip(), ""])
        else:
            # 텍스트와 한 줄에 섞여 있으면 인라인 유지(들여쓰기 보존)
            out.append(replaced)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML <img>  및  표준 마크다운 ![]() 이미지 처리 (GitHub 표준 문법)
# ---------------------------------------------------------------------------
# CONVENTIONS 는 이미지 삽입에 옵시디언 임베드(![[ ]]) 대신 GitHub 표준
# (![]() 와 <img>)을 강제함. pandoc 은 <img> raw HTML 을 docx 에서 버리고,
# 표준 ![]() 도 상대경로가 임시 폴더의 clean.md 기준이라 안 풀림. 그래서
# 변환 전에 둘 다 절대경로 pandoc 이미지(![](abs){width=cm})로 바꿔 둠.

_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
# 표준 마크다운 이미지. src 캡처는 공백/닫는 괄호 전까지(제목 인자 " ... " 제외).
_MD_IMG_RE = re.compile(r"(!\[[^\]]*\])\(\s*([^)\s]+)")


def _resolve_img_path(src, md_dir):
    """상대경로/부분경로 -> 실제 절대경로. %20 등 URL 인코딩은 디코드.
    md 기준 상대경로를 먼저 풀고, 실패하면 assets 인덱스(_find_img)로 폴백."""
    src = urllib.parse.unquote(src.strip())
    cand = os.path.normpath(os.path.join(md_dir, src))
    if os.path.isfile(cand):
        return cand
    return _find_img(src)


def _html_img_md(tag, md_dir):
    """<img src=".." width="N"> -> ![](절대경로){width=cm}. 경로 없으면 '' (제거)."""
    sm = re.search(r"""src\s*=\s*["']([^"']+)["']""", tag)
    if not sm:
        return ""
    abspath = _resolve_img_path(sm.group(1), md_dir)
    if not abspath:
        print("[경고] 이미지 없음: " + sm.group(1), file=sys.stderr)
        return ""
    attr = ""
    wm = re.search(r"""width\s*=\s*["']?(\d+)""", tag)
    if wm:
        attr = "{width=%.2fcm}" % (int(wm.group(1)) * PX_TO_CM)
    return "![](%s)%s" % (abspath.replace("\\", "/"), attr)


def resolve_html_images(text, md_dir):
    """<img ...> -> pandoc 이미지 마크다운. 배치 규칙은 resolve_image_embeds 와 동일:
    단독 이미지는 앞뒤 빈 줄로 독립 문단화(리스트 안이면 들여쓰기 유지), 텍스트와
    한 줄에 섞였으면 인라인 유지."""
    out = []
    for ln in text.split("\n"):
        if not _HTML_IMG_RE.search(ln):
            out.append(ln)
            continue
        replaced = _HTML_IMG_RE.sub(lambda m: _html_img_md(m.group(0), md_dir), ln)
        lead = ln[: len(ln) - len(ln.lstrip())]
        standalone = _HTML_IMG_RE.sub("", ln).strip() == ""
        if standalone:
            out.extend(["", replaced if lead else replaced.strip(), ""])
        else:
            out.append(replaced)
    return "\n".join(out)


def absolutize_md_images(text, md_dir):
    """표준 ![alt](상대경로) 의 경로를 절대경로로 치환(임시폴더 pandoc 이 찾도록).
    이미 절대경로거나 URL(http 등)이면 그대로 둠. <img>에서 만든 절대경로 이미지도
    절대경로라 건드리지 않음."""
    def repl(m):
        alt, path = m.group(1), m.group(2)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", path) or os.path.isabs(path):
            return m.group(0)
        abspath = _resolve_img_path(path, md_dir)
        if not abspath:
            print("[경고] 이미지 없음: " + path, file=sys.stderr)
            return m.group(0)
        return "%s(%s" % (alt, abspath.replace("\\", "/"))
    return _MD_IMG_RE.sub(repl, text)


def _extract_block(lines, marker_idx):
    """marker_idx 는 '^id' 를 담은 줄. 그 위 블록(콜아웃/표/문단)을 추출."""
    # 마커가 줄 끝에 붙은 문단형(... ^id)인지, 독립 줄인지 판별
    marker_line = lines[marker_idx]
    if marker_line.strip().startswith("^"):
        i = marker_idx - 1
        while i >= 0 and lines[i].strip() == "":
            i -= 1
        end = i  # 블록 마지막 줄
    else:
        end = marker_idx  # 문단 끝에 붙음
    if end < 0:
        return ""
    probe = lines[end].lstrip()
    if probe.startswith(">"):
        kind = "quote"
    elif "|" in lines[end]:
        kind = "table"
    else:
        kind = "para"
    start = end
    while start - 1 >= 0:
        prev = lines[start - 1]
        if kind == "quote" and prev.lstrip().startswith(">"):
            start -= 1
        elif kind == "table" and "|" in prev:
            start -= 1
        elif kind == "para" and prev.strip() != "" and not prev.lstrip().startswith(">") and "|" not in prev:
            start -= 1
        else:
            break
    block = lines[start:end + 1]
    # 문단 끝에 붙은 ^id 제거
    block = [re.sub(r"\s*\^[A-Za-z0-9-]+\s*$", "", b) for b in block]
    return "\n".join(block)


def _flatten_callout(block):
    """콜아웃(> [!note] ...)을 일반 본문(진짜 불릿 리스트)으로 평탄화.

    인용블록(>)으로 두면 제목/문단/리스트 사이 빈 줄이 없어 pandoc이 한 문단으로
    뭉쳐 불릿이 풀림. 그래서 > 접두를 벗기고, 블록 종류(문단/불릿)가 바뀌는 경계에
    빈 줄을 넣어 리스트가 리스트로 렌더되게 함. 콜아웃이 아니면(표/문단) 원본 반환.
    """
    lines = block.split("\n")
    if not lines or not lines[0].lstrip().startswith(">"):
        return block  # 콜아웃 아님(표/문단 등)은 그대로

    # 1) 인용 접두(> ) 한 겹 제거 + 선행 탭을 4칸 공백으로(하위 불릿 들여쓰기 보존)
    stripped = []
    for ln in lines:
        m = re.match(r"^\s*>\s?(.*)$", ln)
        c = m.group(1) if m else ln
        c = re.sub(r"^\t+", lambda mm: "    " * len(mm.group(0)), c)
        stripped.append(c)

    # 2) 첫 줄 [!note] 제목 -> H3 헤딩(### ). 워드 제목 3 스타일로 매핑됨.
    m = re.match(r"^\[!\w+\]\s*(.*)$", stripped[0])
    title_present = bool(m)
    if m:
        t = m.group(1).strip()
        stripped[0] = ("### " + t) if t else ""

    # 3) 블록 경계에 빈 줄 삽입 (문단<->불릿 전환, 제목 뒤)
    def is_bullet(s):
        return bool(re.match(r"^\s*[-*+]\s", s))

    out = []
    for i, ln in enumerate(stripped):
        prev = out[-1] if out else ""
        if ln.strip() and prev.strip():
            change = is_bullet(ln) != is_bullet(prev)  # 문단<->불릿 전환
            after_title = (i == 1 and title_present)    # 제목 바로 뒤
            if (change or after_title) and prev.strip() != "":
                out.append("")
        out.append(ln)
    return "\n".join(out)


def resolve_embeds(text):
    """![[파일#^블록]] -> 대상 블록 실제 내용. (블록 ID 형만 처리, 그 외는 경고 후 잔류)"""
    warned = []

    def repl(m):
        target, block_id = m.group(1).strip(), m.group(2).strip()
        path = _find_md(target)
        if not path:
            warned.append("파일 없음: " + target)
            return m.group(0)
        with open(path, encoding="utf-8") as f:
            tlines = f.read().split("\n")
        idx = None
        for i, ln in enumerate(tlines):
            if re.search(r"\^" + re.escape(block_id) + r"\s*$", ln):
                idx = i
                break
        if idx is None:
            warned.append("블록 없음: " + target + "#^" + block_id)
            return m.group(0)
        blk = _extract_block(tlines, idx)
        blk = _flatten_callout(blk)
        return "\n\n" + blk + "\n\n"

    # 블록 ID 임베드
    text = re.sub(r"!\[\[([^\]#|]+)#\^([A-Za-z0-9-]+)\]\]", repl, text)
    # 남은 임베드(헤딩/전체 파일형) 경고
    for m in re.finditer(r"!\[\[([^\]]+)\]\]", text):
        warned.append("미평탄화 임베드(블록ID 아님): " + m.group(1))
    for w in warned:
        print("[경고] " + w, file=sys.stderr)
    return text


# ---------------------------------------------------------------------------
# 위키링크 -> 표시 텍스트
# ---------------------------------------------------------------------------

def strip_wikilinks(text):
    def repl(m):
        target, anchor, alias = m.group(1), m.group(2), m.group(3)
        if alias:
            return alias.strip()
        if target and target.strip():
            return target.strip()
        return (anchor or "").strip()  # [[#anchor]] 자기참조
    return re.sub(
        r"\[\[([^\]\|#]*)(?:#([^\]\|]+))?(?:\|([^\]]+))?\]\]", repl, text
    )


# ---------------------------------------------------------------------------
# § 상호참조 번호 변환 (한글 공문서 -> Word 십진 다단계)
# ---------------------------------------------------------------------------

# H2 서수 글자 -> 십진. [가-하] 범위는 수천 음절을 포함하므로 14자만 명시.
_SEC_H2 = {c: str(i + 1) for i, c in enumerate("가나다라마바사아자차카타파하")}
# §N.<서수>  또는  §N.<서수> <한자리>)  형태 (H3 색인은 한 자리로 제한해 오탐 축소)
_SEC_RE = re.compile(
    r"§(\d+)\.([가나다라마바사아자차카타파하])(?:\s+(\d)\)?)?"
)


def convert_section_refs(text):
    """§4.가 -> §4.1, §3.다 4) -> §3.3.4 (Word 십진 다단계에 맞춤).

    Word 제목 번호는 H1=4, H2=4.1, H3=4.1.3 형식(템플릿 numbering 확인).
    범위 표기(~라)나 두 자리 이상 색인은 건드리지 않음(엣지, 스킵).
    """
    def repl(m):
        s = "§" + m.group(1) + "." + _SEC_H2[m.group(2)]
        if m.group(3):
            s += "." + m.group(3)
        return s
    return _SEC_RE.sub(repl, text)


def flatten_native_callouts(text):
    """문서 자체 본문의 > [!note] 콜아웃을 평탄화(임베드 아닌 원본 콜아웃 대상).

    임베드된 콜아웃은 resolve_embeds 에서 이미 평탄화됨. 소스 문서(공통 사양 등)를
    직접 변환할 때는 자체 콜아웃도 같은 방식(제목 H3 + 불릿)으로 풀어야 함.
    """
    lines = text.split("\n")
    out = []
    i, n = 0, len(lines)
    while i < n:
        if re.match(r"^\s*>\s*\[!\w+\]", lines[i]):
            j = i
            block = []
            while j < n and lines[j].lstrip().startswith(">"):
                block.append(lines[j])
                j += 1
            out.append("")
            out.append(_flatten_callout("\n".join(block)))
            out.append("")
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def strip_block_ids(text):
    """Obsidian 블록 ID 마커 제거: 독립 줄 `^id` 와 문단 끝 ` ^id`."""
    out = []
    for ln in text.split("\n"):
        if re.match(r"^\s*\^[A-Za-z0-9_-]+\s*$", ln):
            continue  # 독립 블록 ID 줄
        ln = re.sub(r"\s+\^[A-Za-z0-9_-]+\s*$", "", ln)  # 문단 끝 블록 ID
        out.append(ln)
    return "\n".join(out)


def preprocess(md_path, exclude=None):
    md_dir = os.path.dirname(md_path)
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    text = strip_frontmatter(text)
    text = strip_comments(text)              # Obsidian 주석 %%...%% 제거
    text = cut_before_first_h1(text)
    text = drop_h1_sections(text, exclude)   # 제외 절 제거(임베드 처리 전)
    text = drop_excluded_refs(text, exclude)  # 제외 절 댕글링 참조 정리
    text = resolve_html_images(text, md_dir)  # <img src width> -> ![](절대){width=cm}
    text = resolve_image_embeds(text)        # 레거시 이미지 임베드 (![[x.png|W]])
    text = resolve_embeds(text)              # 임베드 평탄화 (![[ ]])
    text = absolutize_md_images(text, md_dir)  # 표준 ![](상대경로) -> 절대경로
    text = flatten_native_callouts(text)     # 자체 콜아웃 평탄화 (> [!note])
    text = strip_block_ids(text)             # 블록 ID 마커 제거 (^id)
    text = strip_wikilinks(text)             # 위키링크 표시텍스트화 ([[ ]])
    text = convert_section_refs(text)        # § 참조 번호 십진화
    text = strip_heading_numbers(text)
    return text


# ---------------------------------------------------------------------------
# docx 조립
# ---------------------------------------------------------------------------

# 목록 들여쓰기: 양식이 글자 수 기준(leftChars)이라 pandoc의 인치 기준(720/360 twips)을
# 글자 수 기준으로 바꿈. 한 단계당 2글자씩 들여쓰고, 글머리표는 2글자 내어쓰기로 매닮.
LIST_STEP_CHARS = 200   # 1/100 글자 단위 = 2글자
LIST_STEP_TWIPS = 440   # 11pt 기준 2글자 근사치 (leftChars 미지원 뷰어용 폴백)


def normalize_list_indent(pan_num):
    """pandoc 리스트 numbering 의 들여쓰기를 양식의 글자 수 기준으로 교체.

    글머리표 문자와 폰트(Symbol •, Courier New o, Wingdings ▪)는 그대로 둠.
    """
    def fix_lvl(m):
        lvl = m.group(0)
        ilvl = int(re.search(r'w:ilvl="(\d+)"', lvl).group(1))
        left_chars = LIST_STEP_CHARS * (ilvl + 1)
        left = LIST_STEP_TWIPS * (ilvl + 1)
        ind = (
            '<w:ind w:leftChars="%d" w:left="%d" '
            'w:hangingChars="%d" w:hanging="%d"/>'
            % (left_chars, left, LIST_STEP_CHARS, LIST_STEP_TWIPS)
        )
        return re.sub(r"<w:ind\b[^/>]*/>", ind, lvl)

    return re.sub(r"<w:lvl\b.*?</w:lvl>", fix_lvl, pan_num, flags=re.S)


# pandoc 이 본문에서 참조하지만 양식 styles.xml 에는 없는 스타일. 정의가 없으면 워드가
# 기본 단락으로 떨어뜨려 불릿마다 문단 간격(8pt)이 붙음. 양식 Normal(a) 기반으로 채움.
PANDOC_STYLES = """\
<w:style w:type="paragraph" w:styleId="Compact">
<w:name w:val="Compact"/><w:basedOn w:val="a"/><w:qFormat/>
<w:pPr><w:spacing w:after="0" w:line="259" w:lineRule="auto"/><w:contextualSpacing/></w:pPr>
</w:style>
<w:style w:type="paragraph" w:styleId="FirstParagraph">
<w:name w:val="First Paragraph"/><w:basedOn w:val="a"/><w:qFormat/>
</w:style>
<w:style w:type="paragraph" w:styleId="BodyText">
<w:name w:val="Body Text"/><w:basedOn w:val="a"/><w:qFormat/>
</w:style>
"""


def inject_pandoc_styles(styles_xml):
    """pandoc 이 쓰는 단락 스타일 중 정의가 빠진 것을 양식 스타일 기반으로 추가."""
    add = "".join(
        blk for blk in re.findall(r"<w:style\b.*?</w:style>", PANDOC_STYLES, re.S)
        if 'w:styleId="%s"' % re.search(r'w:styleId="([^"]+)"', blk).group(1)
        not in styles_xml
    )
    if not add:
        return styles_xml
    close = styles_xml.rfind("</w:styles>")
    return styles_xml[:close] + add + styles_xml[close:]


def merge_numbering(tpl_num, pan_num):
    """양식 numbering + pandoc 리스트 numbering 병합 (ID 충돌 없음 전제)."""
    pan_num = normalize_list_indent(pan_num)
    pan_abs = re.findall(r"<w:abstractNum\b.*?</w:abstractNum>", pan_num, re.S)
    pan_nums = re.findall(r"<w:num\s.*?</w:num>", pan_num, re.S)
    merged = tpl_num
    # abstractNum 은 첫 <w:num 앞에 삽입
    first_num = re.search(r"<w:num\s", merged)
    ins = first_num.start() if first_num else merged.find("</w:numbering>")
    merged = merged[:ins] + "".join(pan_abs) + merged[ins:]
    # num 은 </w:numbering> 앞에 삽입
    close = merged.rfind("</w:numbering>")
    merged = merged[:close] + "".join(pan_nums) + merged[close:]
    return merged


# ---------------------------------------------------------------------------
# 표 서식 (양식 스타일 + 헤더 색 + 중앙 정렬)
# ---------------------------------------------------------------------------

# 표에 적용할 양식 내장 표 스타일과 헤더(첫 행) 배경색.
# 10 = "Grid Table 1 Light"(눈금 표 1 밝게). firstRow 조건서식이 헤더를 굵게 함.
TABLE_STYLE_ID = "10"
TABLE_HEADER_FILL = "BDD6EE"

_NEW_TBLPR = (
    '<w:tblPr><w:tblStyle w:val="%s"/>'
    '<w:tblW w:w="5000" w:type="pct"/>'
    '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
    'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
) % TABLE_STYLE_ID


def _grab(inner, tag):
    m = re.search(
        r"<w:%s\b[^>]*/>|<w:%s\b[^>]*>.*?</w:%s>" % (tag, tag, tag), inner, re.S
    )
    return m.group(0) if m else ""


def _rebuild_tcpr(tc, header):
    """셀 tcPr 를 CT_TcPr 스키마 순서로 재구성. 헤더면 배경색(shd), 전 셀 vAlign 중앙.

    OOXML 은 자식 순서가 엄격함: tcW, gridSpan, vMerge, tcBorders, shd, tcMar, vAlign.
    순서가 어긋나면 Word 가 "일부 콘텐츠 읽을 수 없음"을 냄. 그래서 기존 조각을
    빼내 정해진 순서로 다시 씀."""
    # 자기닫힘 <w:tcPr/> 와 일반 <w:tcPr>...</w:tcPr> 를 모두 잡음.
    # 자기닫힘을 못 잡으면 원본이 남아 tcPr 가 둘이 되어 스키마 위반이 됨.
    m = re.search(r"<w:tcPr\b[^>]*/>|<w:tcPr>(.*?)</w:tcPr>", tc, re.S)
    inner = m.group(1) if (m and m.group(1) is not None) else ""
    shd = (
        '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % TABLE_HEADER_FILL
    ) if header else ""
    new = (
        "<w:tcPr>"
        + _grab(inner, "tcW") + _grab(inner, "gridSpan") + _grab(inner, "vMerge")
        + _grab(inner, "tcBorders") + shd + _grab(inner, "tcMar")
        + '<w:vAlign w:val="center"/></w:tcPr>'
    )
    if m:
        return tc[:m.start()] + new + tc[m.end():]
    return tc.replace("<w:tc>", "<w:tc>" + new, 1)


def _center_paras(tc, header):
    """셀 안 문단을 가로 중앙(jc). 헤더면 흰 글씨(color) 제거해 검정 상속.

    jc 는 CT_PPr 에서 문단부호 rPr 앞에 와야 함: rPr 있으면 그 앞, 없으면 pPr 끝.
    볼드는 style 10 firstRow 조건서식이 부여하므로 여기서 넣지 않음."""
    jc = '<w:jc w:val="center"/>'

    def fix_p(pm):
        p = pm.group(0)
        # 자기닫힘 <w:pPr/> 는 통째로 교체(안 그러면 pPr 가 둘이 됨).
        selfc = re.search(r"<w:pPr\b[^>]*/>", p)
        prm = None if selfc else re.search(r"<w:pPr>(.*?)</w:pPr>", p, re.S)
        if selfc:
            p = p[:selfc.start()] + "<w:pPr>" + jc + "</w:pPr>" + p[selfc.end():]
        elif prm:
            pin = re.sub(r"<w:jc\b[^>]*/>", "", prm.group(1))  # 기존 jc 제거
            idx = pin.rfind("<w:rPr>")
            if idx != -1 and pin.rstrip().endswith("</w:rPr>"):
                pin = pin[:idx] + jc + pin[idx:]
            else:
                pin = pin + jc
            p = p[:prm.start()] + "<w:pPr>" + pin + "</w:pPr>" + p[prm.end():]
        else:
            p = re.sub(r"(<w:p\b[^>]*>)", r"\1<w:pPr>" + jc + "</w:pPr>", p, count=1)
        if header:
            p = re.sub(r"<w:color\b[^>]*/>", "", p)  # 흰 글씨 제거 -> 검정
        return p

    return re.sub(r"<w:p\b[^>]*>.*?</w:p>", fix_p, tc, flags=re.S)


def style_tables(body):
    """pandoc 본문의 표에 양식 표 스타일(10), 헤더 배경색, 전 셀 중앙 정렬 적용.

    head/tail(양식 표지·목차)의 표는 건드리지 않음(body 만 대상)."""
    def do_tbl(tm):
        tbl = re.sub(r"<w:tblPr>.*?</w:tblPr>", _NEW_TBLPR, tm.group(0),
                     count=1, flags=re.S)
        hdr_end = tbl.find("</w:tr>")  # 첫 행 끝 = 헤더 경계

        def do_tc(cm):
            header = cm.start() < hdr_end
            return _center_paras(_rebuild_tcpr(cm.group(0), header), header)

        return re.sub(r"<w:tc>.*?</w:tc>", do_tc, tbl, flags=re.S)

    return re.sub(r"<w:tbl>.*?</w:tbl>", do_tbl, body, flags=re.S)


def assemble(content_docx, out_docx, title=None):
    with zipfile.ZipFile(TEMPLATE) as z:
        names = list(z.namelist())
        datas = {n: z.read(n) for n in names}
    tpl_doc = datas["word/document.xml"].decode("utf-8")
    tpl_num = datas["word/numbering.xml"].decode("utf-8")
    rels_name = "word/_rels/document.xml.rels"
    tpl_rels = datas.get(rels_name, b"").decode("utf-8")
    ct_name = "[Content_Types].xml"
    ct = datas.get(ct_name, b"").decode("utf-8")

    with zipfile.ZipFile(content_docx) as z:
        cnames = z.namelist()
        pan_doc = z.read("word/document.xml").decode("utf-8")
        pan_styles = z.read("word/styles.xml").decode("utf-8")
        pan_num = z.read("word/numbering.xml").decode("utf-8")
        pan_rels = (z.read(rels_name).decode("utf-8")
                    if rels_name in cnames else "")
        pan_media = {n: z.read(n) for n in cnames if n.startswith("word/media/")}

    pan_styles = inject_pandoc_styles(pan_styles)

    # 양식 앞부분: 첫 <w:sectPr(섹션 나누기)를 담은 문단 끝까지.
    # 단, 그 문단이 목차 <w:sdt> 안 마지막 문단이면 sdt 닫는 태그까지 포함해야
    # 함(안 그러면 sdt 미닫힘으로 XML 깨짐).
    first_sect = tpl_doc.find("<w:sectPr")
    if first_sect < 0:
        fail("양식에서 섹션 나누기(sectPr)를 찾지 못함")
    head_end = tpl_doc.find("</w:p>", first_sect) + len("</w:p>")
    closer = re.match(r"\s*(?:</w:sdtContent>\s*</w:sdt>\s*)*", tpl_doc[head_end:])
    head_end += closer.end()
    head = tpl_doc[:head_end]
    # 표지 부제를 변환 문서 title 로 치환. 부제는 dc:subject 에 바인딩된 콘텐츠
    # 컨트롤이라, 정본은 docProps/core.xml 의 <dc:subject>. Word 가 열 때 여기서
    # 다시 읽어 표시하므로 core.xml 을 바꿔야 함(document.xml 캐시 텍스트만 바꾸면
    # 열 때 되돌아감). 캐시 표시 텍스트도 함께 갱신함.
    if title:
        esc = (title.replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;"))
        core_name = "docProps/core.xml"
        if core_name in datas:
            core = datas[core_name].decode("utf-8")
            new_core = re.sub(
                r"<dc:subject>.*?</dc:subject>",
                lambda _m: "<dc:subject>" + esc + "</dc:subject>",
                core, count=1, flags=re.S)
            if new_core != core:
                datas[core_name] = new_core.encode("utf-8")
            else:
                print("[경고] core.xml 의 dc:subject 를 못 바꿈", file=sys.stderr)
        if COVER_SUBTITLE_PLACEHOLDER in head:
            head = head.replace(COVER_SUBTITLE_PLACEHOLDER, esc, 1)
        else:
            print("[경고] 표지 부제 캐시 텍스트를 못 찾음: "
                  + COVER_SUBTITLE_PLACEHOLDER, file=sys.stderr)
    # 양식 최종 sectPr(본문 섹션 = 페이지 -1- 설정)
    last_sect = tpl_doc.rfind("<w:sectPr")
    tail = tpl_doc[last_sect:]

    # pandoc 본문: <w:body> 다음 ~ pandoc 자체 최종 sectPr 앞
    pb = pan_doc.find("<w:body>") + len("<w:body>")
    pan_last_sect = pan_doc.rfind("<w:sectPr")
    body = pan_doc[pb:pan_last_sect]

    # pandoc 이미지/하이퍼링크 관계와 미디어를 양식 패키지로 병합.
    # rId 충돌을 피하려 양식 최대 rId 다음부터 재번호하고, 본문 참조도 함께 고침.
    # 본문이 실제 참조하는 관계(이미지 r:embed, 하이퍼링크 r:id)만 병합함:
    # numbering/styles/settings/comments 등 파트 관계는 양식이 이미 제공하므로
    # 병합하면 중복·댕글링(comments.xml 미포함)이 생겨 Word가 "일부 콘텐츠를
    # 읽을 수 없음"을 띄움.
    body_refs = set(re.findall(r'r:(?:embed|id)="(rId\d+)"', body))
    # 새 rId 는 양식 것뿐 아니라 pandoc 것까지 포함한 전체 최대+1 부터 매김.
    # 양식 것만 기준(예: 13부터)으로 하면, 아직 재매핑 전인 pandoc old id(예: rId19)와
    # 겹쳐 전역 문자열 치환이 서로를 덮어씀(이미지 뒤바뀜). old id 는 모두 이 값 미만이라
    # 위에서 시작하면 충돌이 없음.
    existing = [int(x) for x in re.findall(r'Id="rId(\d+)"', tpl_rels)]
    existing += [int(x) for x in re.findall(r'Id="rId(\d+)"', pan_rels)]
    next_id = (max(existing) + 1) if existing else 1
    new_rel, img_added = [], False
    for rel in re.findall(r"<Relationship\b[^>]*?/>", pan_rels):
        old_id = re.search(r'Id="(rId\d+)"', rel).group(1)
        if old_id not in body_refs:
            continue  # 본문이 참조 안 하는 파트 관계는 양식 것을 그대로 씀
        new_id = "rId%d" % next_id
        next_id += 1
        body = body.replace('r:embed="%s"' % old_id, 'r:embed="%s"' % new_id)
        body = body.replace('r:id="%s"' % old_id, 'r:id="%s"' % new_id)
        if "/image" in rel:
            target = re.search(r'Target="([^"]+)"', rel).group(1)
            old_media = "word/" + target.lstrip("./")
            new_base = "pan_" + os.path.basename(target)
            if old_media in pan_media:
                dest = "word/media/" + new_base
                datas[dest] = pan_media[old_media]
                if dest not in names:
                    names.append(dest)
                img_added = True
            rel = rel.replace('Target="%s"' % target, 'Target="media/%s"' % new_base)
        rel = rel.replace('Id="%s"' % old_id, 'Id="%s"' % new_id)
        new_rel.append(rel)
    if new_rel:
        cl = tpl_rels.rfind("</Relationships>")
        tpl_rels = tpl_rels[:cl] + "".join(new_rel) + tpl_rels[cl:]
        datas[rels_name] = tpl_rels.encode("utf-8")
    if img_added:
        for ext, ctype in (("png", "image/png"), ("jpeg", "image/jpeg"),
                           ("jpg", "image/jpeg"), ("gif", "image/gif"),
                           ("bmp", "image/bmp")):
            if ('Extension="%s"' % ext) not in ct:
                cl = ct.rfind("</Types>")
                ct = ct[:cl] + ('<Default Extension="%s" ContentType="%s"/>' % (ext, ctype)) + ct[cl:]
        datas[ct_name] = ct.encode("utf-8")

    body = style_tables(body)  # 표에 양식 스타일·헤더 색·중앙 정렬 적용

    new_doc = head + body + tail

    # pandoc 이미지 XML이 쓰는 네임스페이스(wp/a/pic 등)를 양식 루트 <w:document>에
    # 보강. 없으면 그 접두를 못 풀어 Word 가 "unbound prefix"로 문서를 못 읽음.
    pan_root = re.search(r"<w:document\b([^>]*)>", pan_doc).group(1)
    tpl_root = re.search(r"<w:document\b([^>]*)>", new_doc).group(1)
    pan_ns = re.findall(r'(xmlns:\w+)="([^"]+)"', pan_root)
    have = set(re.findall(r"xmlns:\w+", tpl_root))
    add_ns = "".join(' %s="%s"' % (k, v) for k, v in pan_ns if k not in have)
    if add_ns:
        new_doc = new_doc.replace(
            "<w:document" + tpl_root + ">",
            "<w:document" + tpl_root + add_ns + ">", 1)

    datas["word/document.xml"] = new_doc.encode("utf-8")
    datas["word/styles.xml"] = pan_styles.encode("utf-8")
    datas["word/numbering.xml"] = merge_numbering(tpl_num, pan_num).encode("utf-8")

    with zipfile.ZipFile(out_docx, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, datas[n])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    # --exclude "11,12,13" : 해당 번호의 H1 절 제외
    argv = sys.argv[1:]
    exclude = set()
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--exclude" and i + 1 < len(argv):
            exclude = {t.strip() for t in argv[i + 1].split(",") if t.strip()}
            i += 2
        elif a.startswith("--exclude="):
            exclude = {t.strip() for t in a.split("=", 1)[1].split(",") if t.strip()}
            i += 1
        else:
            rest.append(a)
            i += 1

    if not rest:
        fail("사용법: python scripts/md_to_docx.py <입력.md> [출력.docx] [--exclude 11,12,13]")
    md_path = os.path.abspath(rest[0])
    if not os.path.isfile(md_path):
        fail("입력 파일 없음: " + md_path)
    if not os.path.isfile(TEMPLATE):
        fail("양식 파일 없음: " + TEMPLATE)

    base = os.path.splitext(os.path.basename(md_path))[0]
    if len(rest) >= 2:
        out_docx = os.path.abspath(rest[1])
    else:
        export_dir = os.path.join(VAULT, "export")
        os.makedirs(export_dir, exist_ok=True)
        out_docx = os.path.join(export_dir, base + ".docx")
    os.makedirs(os.path.dirname(out_docx), exist_ok=True)

    pandoc = find_pandoc()
    cleaned = preprocess(md_path, exclude=exclude)

    with tempfile.TemporaryDirectory() as td:
        clean_md = os.path.join(td, "clean.md")
        content_docx = os.path.join(td, "content.docx")
        with open(clean_md, "w", encoding="utf-8") as f:
            f.write(cleaned)
        r = subprocess.run(
            [pandoc, clean_md, "--reference-doc", TEMPLATE, "-o", content_docx],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            fail("pandoc 실패:\n" + r.stderr)
        assemble(content_docx, out_docx, title=extract_frontmatter_title(md_path))

    print("[완료] " + out_docx)


if __name__ == "__main__":
    main()
