#!/usr/bin/env node
// wiki_lint.mjs - LLM Wiki 정합성 자동 검증
// 사용법: node scripts/wiki_lint.mjs [--json]
//
// 검증 항목 (v2):
//   1. 깨진 wikilink: [[파일명]]의 대상 파일이 실재하는지
//      severity: warning (CONVENTIONS 3.5 Wikilink 규칙 "링크 대상 문서가 아직 없어도 괜찮음(나중에 생성)" 허용)
//   2. wikilink anchor 정합: [[파일#anchor]]의 anchor가 헤딩 텍스트와 일치하는지
//      severity: error (대상 파일 존재인데 anchor 매칭 안 됨: 명백한 stale)
//   3. 가운뎃점(·) 위배: 일반 위키 영역에 가운뎃점 사용 (CONVENTIONS 3.4 문체 위배)
//      severity: error
//   4. § 절 참조 사용: 2026-07-14에 폐기된 표기 (CONVENTIONS 3.5 Wikilink 규칙)
//      severity: error. 절 참조는 wikilink anchor로만 씀
//      예외: 당시 문서 상태를 인용한 이력 (log.md, _archive/, 반복 결함 카탈로그,
//            검수 기록 3종)과 폐지 정책 자체를 설명하는 CONVENTIONS 본문
//   5. MOC 미등록: 문서가 00_Index/MOC.md에 [[ ]]로 등록되지 않음 (CONVENTIONS 5.1 6단계)
//      severity: error
//   6. (2026-08-21 삭제) 링크 하한 미달: 나가는 링크 개수로는 고립을 판정할 수 없고 도달 보장은
//      MOC 등록 검사(5번)가 하므로 제거함. 상호 연결은 CONVENTIONS 3.5의 작성 규칙으로만 유지함
//   7. em dash 위배: CONVENTIONS 3.4.1이 금지하나 검사가 없어 사각지대였음 (2026-08-20 추가)
//      severity: error. 예외는 규칙을 설명하는 CONVENTIONS 본문뿐
//   8. 이미지 경로: ![](경로)와 <img src>의 파일이 실재하는지 (2026-08-20 추가)
//      severity: error. 코드블록, 인라인 백틱, <name> 자리표시자는 제외
//   9. 폐기 어휘: scripts/deprecated_terms.txt에 등록된 옛 용어가 활성 문서에 남았는지 (2026-08-21 추가)
//      severity: error. 백틱 안 언급(폐기 설명 자리)과 이력 보존 영역(log.md, _archive/)은 면제
//  10. 참조 순서 위반: 번호 N 폴더의 문서가 뒷 번호 폴더의 문서를 wikilink로 가리킴 (2026-08-21 추가)
//      severity: warning (CONVENTIONS 2 "폴더 번호는 참조 순서임". 해당 문서를 고칠 때 함께 정리함)
//      순서 밖: 00_Index(색인은 전체를 가리킴), 무번호 폴더, 루트 규칙 문서. 링크의 출발이나
//      도착이 순서 밖이면 검사하지 않음. log.md는 이력이라 제외
//
// exit code:
//   - 0: error 0건 (warning은 표시만 하고 통과)
//   - 1: error 1건 이상
//
// 별도 스크립트:
//   - 헤딩 넘버링 정합 (H1 `1.` / H2 `1.1` / H3 `1.1.1` / H4 `1)` / H5 `(1)`) → scripts/wiki_number.mjs
//     점검은 `node scripts/wiki_number.mjs --check`, 정정은 `--write` (anchor 연쇄 갱신 포함)
//
// 예외 영역:
//   - 02_References/_locked/, _sources/, _figures/, _reviews/, converted/ (read-only)
//   - 99_Logs/log.md (이력 보존: 가운뎃점/문체 검사 제외)
//   - .claude/, node_modules/, .git/, .obsidian/, assets/, scripts/
//
// 가운뎃점 의도 예외:
//   - CONVENTIONS.md (가운뎃점 규칙 정의)
//   - 01_HowTo/반복 결함 카탈로그.md (정규식 예시)
//   - 01_HowTo/codex 검수 포커스.md (정책 언급)

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, '..');

// 이미지 등 바이너리 자산이 실제로 사는 곳. 보통 REPO_ROOT와 같음.
// pre-commit 훅은 인덱스에서 .md와 스크립트만 임시 폴더로 꺼내 검사하므로
// 그 폴더에는 assets/가 없음. 훅이 이 변수로 진짜 저장소 루트를 알려 줌
const ASSET_ROOT = process.env.WIKI_ASSET_ROOT
  ? resolve(process.env.WIKI_ASSET_ROOT)
  : REPO_ROOT;

const EXCLUDED_PATHS = new Set([
  '02_References/_locked',
  '02_References/_sources',
  '02_References/_figures',
  '02_References/_reviews',
  '02_References/converted',
  '.claude',
  'node_modules',
  '.git',
  '.obsidian',
  'assets',
  'scripts',
  // 90_Temp(임시 대기소)는 lint 대상임. 외부 원자료가 들어오면 그 파일만 여기 개별 제외함
]);

const SKIP_CONTENT_CHECKS = new Set([
  '99_Logs/log.md',
]);

// MOC 등록을 면제하는 곳.
// 루트 규칙 문서, 색인, 로그, 작업 노트, 그리고 위키 밖에서 읽히는 자족 폴더임
const GRAPH_EXEMPT_FILES = new Set([
  'README.md', 'AGENTS.md', 'CONVENTIONS.md', 'CLAUDE.md', '00_Index/MOC.md',
]);
const GRAPH_EXEMPT_PREFIX = ['prototype/', '06_클라이언트 데이터/', '90_Temp/']; // 90_Temp: 임시 노트라 MOC 등록만 면제 (2026-08-20)
const GRAPH_EXEMPT_TYPES = new Set(['index', 'log', 'agentnote']);

// em dash 금지 규칙 자체를 설명하는 문서. 규칙을 적으려면 그 문자를 써야 함
const ALLOW_EM_DASH = new Set([
  'CONVENTIONS.md',
]);

const ALLOW_GAWUNDEOTJEOM = new Set([
  'CONVENTIONS.md',
  '01_HowTo/반복 결함 카탈로그.md',
  '01_HowTo/codex 검수 포커스.md',
  '02_References/converted_모순점.md', // 변환본 인용 컨텍스트
]);

// § 표기가 허용되는 곳. 모두 "당시 문서 상태"를 인용한 기록이라 고치면 기록이 왜곡됨
const ALLOW_SECTION_MARK = new Set([
  'CONVENTIONS.md',                                          // § 폐지 정책을 설명하는 본문
  '01_HowTo/반복 결함 카탈로그.md',                            // 과거 결함 사례 인용
]);
const ALLOW_SECTION_MARK_PREFIX = ['04_Projects/_archive/']; // 폐기 문서, 이력 보존

// fileIndex 빌드 시 read-only 영역도 포함 (link target 매칭용)
// 다만 검사 대상은 EXCLUDED_PATHS 제외한 일반 위키만
const INDEX_INCLUDED_DIRS = [
  '02_References/_locked',
  '02_References/converted',
];

// 이미지 등 첨부 파일이 사는 디렉토리 (임베드 ![[경로/파일.png]] 대상 검증용)
const ATTACHMENT_DIRS = [
  'assets',
  '02_References/_figures',
];

const args = process.argv.slice(2);
const JSON_OUT = args.includes('--json');

function normRel(p) {
  return p.split('\\').join('/');
}

function collectMd(root, rel = '') {
  const out = [];
  const dirPath = rel ? join(root, rel) : root;
  let entries;
  try {
    entries = readdirSync(dirPath);
  } catch {
    return out;
  }
  for (const entry of entries) {
    const relPath = rel ? `${rel}/${entry}` : entry;
    if (EXCLUDED_PATHS.has(relPath)) continue;
    const full = join(root, relPath);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) {
      out.push(...collectMd(root, relPath));
    } else if (extname(entry) === '.md') {
      out.push(normRel(relPath));
    }
  }
  return out;
}

function extractHeadings(content) {
  const headings = [];
  const lines = content.split('\n');
  let inCodeBlock = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;
    const m = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
    if (m) {
      headings.push({ level: m[1].length, text: m[2].trim(), line: i + 1 });
    }
  }
  return headings;
}

function extractWikilinks(content) {
  const links = [];
  // [[파일명#anchor|별칭]]: | escape도 처리 (\|)
  // 파일명이 비면([[#anchor]]) 자기 문서 참조 (CONVENTIONS 3.5 Wikilink 규칙이 정한 형식)
  const regex = /\[\[([^\[\]\|#]*)(?:#([^\[\]\|]+?))?(?:\\?\|([^\[\]]+?))?\]\]/g;
  const lines = content.split('\n');
  let inCodeBlock = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;
    // 인라인 백틱 안 wikilink 무시
    const lineNoCode = line.replace(/`[^`]*`/g, '');
    let m;
    regex.lastIndex = 0;
    while ((m = regex.exec(lineNoCode)) !== null) {
      links.push({
        target: m[1].trim(),
        anchor: m[2] ? m[2].trim() : null,
        alias: m[3] ? m[3].trim() : null,
        line: i + 1,
      });
    }
  }
  return links;
}

function buildFileIndex(allMdFiles) {
  const index = new Map();
  for (const relPath of allMdFiles) {
    const name = basename(relPath, '.md');
    if (!index.has(name)) {
      index.set(name, relPath);
    }
  }
  // EXCLUDED 영역의 .md도 link target 매칭용으로 인덱스에 포함
  for (const inclDir of INDEX_INCLUDED_DIRS) {
    const dirPath = join(REPO_ROOT, inclDir);
    let entries;
    try {
      entries = readdirSync(dirPath, { recursive: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const e = typeof entry === 'string' ? entry : entry.name;
      if (extname(e) === '.md') {
        const name = basename(e, '.md');
        if (!index.has(name)) {
          index.set(name, `${inclDir}/${e}`);
        }
      }
    }
  }
  // 첨부(이미지 등) 인덱싱: assets/, _figures/ 하위 비-.md 파일을 경로 접미사 형태로 등록
  // Obsidian은 ![[유람기/1_1.png]]를 경로 접미사로 해석하므로 모든 접미사 키를 등록함
  for (const attachDir of ATTACHMENT_DIRS) {
    let entries;
    try {
      entries = readdirSync(join(REPO_ROOT, attachDir), { recursive: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const e = (typeof entry === 'string' ? entry : entry.name).replace(/\\/g, '/');
      if (extname(e) === '' || extname(e) === '.md') continue; // 디렉토리/확장자 없음/.md 제외
      const rel = `${attachDir}/${e}`;
      const segs = rel.split('/');
      for (let i = segs.length - 1; i >= 0; i--) {
        const suffix = segs.slice(i).join('/');
        if (!index.has(suffix)) index.set(suffix, rel);
      }
    }
  }
  return index;
}

function checkBrokenWikilinks(allMdFiles, fileIndex) {
  const findings = [];
  for (const relPath of allMdFiles) {
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    const links = extractWikilinks(content);
    for (const link of links) {
      // log.md는 이력: wikilink 검사 제외 (과거 참조 보존)
      if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
      if (link.target === '') continue; // [[#anchor]] 자기 문서 참조: 대상 파일이 자기 자신
      if (!fileIndex.has(link.target)) {
        findings.push({
          type: 'broken_wikilink',
          severity: 'warning',
          file: relPath,
          line: link.line,
          message: `[[${link.target}]]: 대상 파일 없음 (미작성 stub link로 간주)`,
        });
      }
    }
  }
  return findings;
}

// anchor가 헤딩과 맞는지 봄. 중첩 경로(`#부모#자식`)도 지원함
//   Obsidian은 `[[파일#부모#자식]]`으로 부모 아래의 자식 헤딩을 콕 집을 수 있음. 시스템마다
//   반복되는 명세 항목 헤더(동작과 규칙 등)를 가리킬 때 씀. 통짜 텍스트로 비교하면 broken으로
//   오판정하므로, `#`로 나눠 부모에서 자식으로 내려가는 헤딩 경로가 실재하는지 순서대로 확인함
function matchHeadingPath(headings, anchor) {
  const segs = anchor.split('#').map(s => s.trim()).filter(Boolean);
  if (segs.length === 0) return false;
  if (segs.length === 1) return headings.some(h => h.text === segs[0]);

  // 부모 후보마다, 그 부모의 하위 구간(더 깊은 레벨이 이어지는 동안) 안에서 다음 조각을 찾음
  const search = (from, to, depth, si) => {
    for (let i = from; i < to; i++) {
      const h = headings[i];
      if (h.level <= depth) continue;          // 형제나 상위는 하위 구간이 아님
      if (h.text !== segs[si]) continue;
      if (si === segs.length - 1) return true;
      // 이 헤딩의 하위 구간 끝을 찾음
      let end = i + 1;
      while (end < to && headings[end].level > h.level) end++;
      if (search(i + 1, end, h.level, si + 1)) return true;
    }
    return false;
  };

  for (let i = 0; i < headings.length; i++) {
    if (headings[i].text !== segs[0]) continue;
    let end = i + 1;
    while (end < headings.length && headings[end].level > headings[i].level) end++;
    if (search(i + 1, end, headings[i].level, 1)) return true;
  }
  return false;
}

function checkWikilinkAnchors(allMdFiles, fileIndex) {
  const findings = [];
  const headingsCache = new Map();
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    const links = extractWikilinks(content);
    for (const link of links) {
      if (!link.anchor) continue;
      // [[#anchor]]는 자기 문서 헤딩 참조
      const targetPath = link.target === '' ? relPath : fileIndex.get(link.target);
      if (!targetPath) continue;
      // 블록 ID anchor (#^id): 헤딩이 아니라 블록 참조(Obsidian transclusion): 헤딩이 아니라 블록 ID 존재로 검증
      if (link.anchor.startsWith('^')) {
        const blockContent = readFileSync(join(REPO_ROOT, targetPath), 'utf8');
        const blockId = link.anchor.slice(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const blockRe = new RegExp('\\^' + blockId + '\\s*$', 'm');
        if (!blockRe.test(blockContent)) {
          findings.push({
            type: 'broken_anchor',
            severity: 'error',
            file: relPath,
            line: link.line,
            message: `[[${link.target}#${link.anchor}]]: 블록 ID가 ${link.target}에 없음`,
          });
        }
        continue;
      }
      let targetHeadings;
      if (headingsCache.has(targetPath)) {
        targetHeadings = headingsCache.get(targetPath);
      } else {
        const targetContent = readFileSync(join(REPO_ROOT, targetPath), 'utf8');
        targetHeadings = extractHeadings(targetContent);
        headingsCache.set(targetPath, targetHeadings);
      }
      if (!matchHeadingPath(targetHeadings, link.anchor)) {
        findings.push({
          type: 'broken_anchor',
          severity: 'error',
          file: relPath,
          line: link.line,
          message: `[[${link.target}#${link.anchor}]]: anchor가 ${link.target} 헤딩 텍스트와 매칭 안 됨`,
        });
      }
    }
  }
  return findings;
}

function checkGawundeotjeom(allMdFiles) {
  const findings = [];
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    if (ALLOW_GAWUNDEOTJEOM.has(relPath)) continue;
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    const lines = content.split('\n');
    let inCodeBlock = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^```/.test(line)) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;
      // 인라인 백틱 안 가운뎃점은 무시
      const lineNoCode = line.replace(/`[^`]*`/g, '');
      if (lineNoCode.includes('·')) {
        findings.push({
          type: 'gawundeotjeom',
          severity: 'error',
          file: relPath,
          line: i + 1,
          message: `가운뎃점 \`·\` 사용: CONVENTIONS 3.4 문체 위배 (쉼표 또는 슬래시로 대체)`,
        });
      }
    }
  }
  return findings;
}

// 7. em dash 위배. CONVENTIONS 3.4.1이 금지하나 어떤 검사도 없어 사각지대였음 (2026-08-20 추가)
function checkEmDash(allMdFiles) {
  const findings = [];
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    if (ALLOW_EM_DASH.has(relPath)) continue;
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    const lines = content.split('\n');
    let inCodeBlock = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^```/.test(line)) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;
      // 인라인 백틱 안 em dash는 무시 (규칙을 설명하는 자리)
      const lineNoCode = line.replace(/`[^`]*`/g, '');
      if (lineNoCode.includes('—')) {
        findings.push({
          type: 'em_dash',
          severity: 'error',
          file: relPath,
          line: i + 1,
          message: 'em dash 사용: CONVENTIONS 3.4.1 문체 위배 (쉼표, 콜론, 괄호로 대체하거나 문장을 나눔)',
        });
      }
    }
  }
  return findings;
}

// 8. 이미지 경로. CONVENTIONS 3.5가 "작성자가 직접 확인"으로 두었으나 한 번도
// 확인되지 않아 폴더 이동으로 깨진 32건이 방치됐음 (2026-08-20 기계로 옮김)
function checkImagePaths(allMdFiles) {
  const findings = [];
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    // 자산은 워킹트리 사실이라 ASSET_ROOT 기준으로 봄 (위 상수 설명 참조)
    const absDir = dirname(join(ASSET_ROOT, relPath));
    const lines = readFileSync(join(REPO_ROOT, relPath), 'utf8').split('\n');
    let inCodeBlock = false;
    for (let i = 0; i < lines.length; i++) {
      if (/^\s*```/.test(lines[i])) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;
      // 인라인 백틱 안은 문법 설명이라 제외
      const line = lines[i].replace(/`[^`]*`/g, '');
      const srcs = [];
      for (const m of line.matchAll(/!\[[^\]]*\]\(([^)\s]+)/g)) srcs.push(m[1].trim());
      for (const m of line.matchAll(/<img[^>]+src="([^"]+)"/g)) srcs.push(m[1].trim());
      for (const src of srcs) {
        if (/^https?:|^data:/.test(src)) continue;
        if (src.includes('<') || src.includes('>')) continue; // <name> 같은 자리표시자
        let target;
        try {
          target = resolve(absDir, decodeURIComponent(src));
        } catch {
          continue;
        }
        let exists = true;
        try {
          statSync(target);
        } catch {
          exists = false;
        }
        if (!exists) {
          findings.push({
            type: '이미지 경로',
            severity: 'error',
            file: relPath,
            line: i + 1,
            message: `이미지 파일 없음: ${src} (CONVENTIONS 3.5 이미지 삽입, 그 .md 기준 상대경로여야 함)`,
          });
        }
      }
    }
  }
  return findings;
}

// § 절 참조는 2026-07-14에 폐기됨. 절 참조는 wikilink anchor로만 씀
function checkSectionMark(allMdFiles) {
  const findings = [];
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    if (ALLOW_SECTION_MARK.has(relPath)) continue;
    if (ALLOW_SECTION_MARK_PREFIX.some(p => relPath.startsWith(p))) continue;
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    const lines = content.split('\n');
    let inCodeBlock = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^```/.test(line)) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;
      // 인라인 백틱 안 § 는 무시 (표기 자체를 예시로 드는 경우)
      const lineNoCode = line.replace(/`[^`]*`/g, '');
      if (lineNoCode.includes('§')) {
        findings.push({
          type: 'section_mark',
          severity: 'error',
          file: relPath,
          line: i + 1,
          message: `§ 절 참조 사용: 폐기된 표기임 (CONVENTIONS 3.5 Wikilink 규칙). wikilink anchor로 씀`,
        });
      }
    }
  }
  return findings;
}

// 9. 폐기 어휘. 폐기 선언 뒤에도 옛 용어가 활성 문서에 남는 것을 잡음 (2026-08-21 추가).
//    검증 불가능한 선언("옛 용어를 참조하지 않겠음")을 검증 가능한 검사로 옮긴 자리임
function loadDeprecatedTerms() {
  let raw;
  try {
    raw = readFileSync(join(SCRIPT_DIR, 'deprecated_terms.txt'), 'utf8');
  } catch {
    return [];
  }
  const terms = [];
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const [term, hint] = t.split('\t');
    if (term && term.trim()) terms.push({ term: term.trim(), hint: (hint || '').trim() });
  }
  return terms;
}

function checkDeprecatedTerms(allMdFiles) {
  const findings = [];
  const terms = loadDeprecatedTerms();
  if (!terms.length) return findings;
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue;
    if (relPath.startsWith('04_Projects/_archive/')) continue;
    const lines = readFileSync(join(REPO_ROOT, relPath), 'utf8').split('\n');
    let inCodeBlock = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^```/.test(line)) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;
      // 인라인 백틱 안은 폐기를 설명하는 메타 언급이라 면제
      const lineNoCode = line.replace(/`[^`]*`/g, '');
      for (const { term, hint } of terms) {
        if (lineNoCode.includes(term)) {
          findings.push({
            type: '폐기 어휘',
            severity: 'error',
            file: relPath,
            line: i + 1,
            message: `폐기 어휘 "${term}" 사용${hint ? ` (${hint})` : ''}. 용어 자체를 언급하는 자리면 백틱으로 감쌈`,
          });
        }
      }
    }
  }
  return findings;
}

function graphExempt(relPath, content) {
  if (GRAPH_EXEMPT_FILES.has(relPath)) return true;
  if (GRAPH_EXEMPT_PREFIX.some(pre => relPath.startsWith(pre))) return true;
  const fm = content.match(/^---\n([\s\S]*?)\n---/);
  if (!fm) return false;
  const t = fm[1].match(/^type:\s*(\S+)/m);
  return t ? GRAPH_EXEMPT_TYPES.has(t[1]) : false;
}

// 5. MOC 미등록. 셀프체크 "MOC에 등록했는가"를 기계로 옮긴 것 (2026-08-20)
function checkMocRegistration(allMdFiles) {
  const findings = [];
  const mocRel = '00_Index/MOC.md';
  if (!allMdFiles.includes(mocRel)) return findings;
  const moc = readFileSync(join(REPO_ROOT, mocRel), 'utf8');
  for (const relPath of allMdFiles) {
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    if (graphExempt(relPath, content)) continue;
    const name = basename(relPath, '.md');
    const hit = moc.includes('[[' + name + ']]')
      || moc.includes('[[' + name + '|')
      || moc.includes('[[' + name + '#');
    if (!hit) {
      findings.push({
        type: 'MOC 미등록',
        severity: 'error',
        file: relPath,
        line: 1,
        message: `00_Index/MOC.md에 [[${name}]]이 없음 (CONVENTIONS 5.1 문서 생성 6단계)`,
      });
    }
  }
  return findings;
}


// 폴더의 참조 순서 번호. 순서 밖(루트 문서, 무번호 폴더, 00_Index)은 null
function folderOrder(relPath) {
  const m = normRel(relPath).match(/^(\d{2})_[^/]+\//);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  if (n === 0) return null; // 00_Index: 색인은 전체를 가리키는 면제 폴더
  return n;
}

function checkReferenceOrder(allMdFiles, fileIndex) {
  const findings = [];
  for (const relPath of allMdFiles) {
    if (SKIP_CONTENT_CHECKS.has(relPath)) continue; // log.md: 이력
    const srcOrder = folderOrder(relPath);
    if (srcOrder === null) continue;
    const content = readFileSync(join(REPO_ROOT, relPath), 'utf8');
    for (const link of extractWikilinks(content)) {
      if (!link.target) continue; // [[#anchor]] 자기 문서 참조
      const targetPath = fileIndex.get(link.target);
      if (!targetPath) continue; // 대상 없음은 1번(깨진 wikilink) 검사 몫
      const tgtOrder = folderOrder(targetPath);
      if (tgtOrder === null || tgtOrder <= srcOrder) continue;
      const srcTop = normRel(relPath).split('/')[0];
      const tgtTop = normRel(targetPath).split('/')[0];
      findings.push({
        type: '참조 순서 위반',
        severity: 'warning',
        file: relPath,
        line: link.line,
        message: `[[${link.target}]]: ${srcTop} 문서가 뒷 폴더(${tgtTop}) 문서를 가리킴 (CONVENTIONS 2 참조 순서: 앞 폴더만 참고)`,
      });
    }
  }
  return findings;
}

function main() {
  const allMdFiles = collectMd(REPO_ROOT);
  const fileIndex = buildFileIndex(allMdFiles);
  const findings = [
    ...checkBrokenWikilinks(allMdFiles, fileIndex),
    ...checkWikilinkAnchors(allMdFiles, fileIndex),
    ...checkGawundeotjeom(allMdFiles),
    ...checkEmDash(allMdFiles),
    ...checkImagePaths(allMdFiles),
    ...checkSectionMark(allMdFiles),
    ...checkDeprecatedTerms(allMdFiles),
    ...checkMocRegistration(allMdFiles),
    ...checkReferenceOrder(allMdFiles, fileIndex),
  ];
  const errors = findings.filter(f => f.severity === 'error');
  const warnings = findings.filter(f => f.severity === 'warning');
  if (JSON_OUT) {
    console.log(JSON.stringify({
      ok: errors.length === 0,
      errorCount: errors.length,
      warningCount: warnings.length,
      scanned: allMdFiles.length,
      findings,
    }, null, 2));
  } else {
    console.log(`Wiki lint v2: ${allMdFiles.length}개 .md 스캔`);
    if (findings.length === 0) {
      console.log('✓ 발견 0건');
    } else {
      console.log(`✗ error ${errors.length}건 / warning ${warnings.length}건\n`);
      const byType = {};
      for (const f of findings) {
        byType[f.type] = byType[f.type] || [];
        byType[f.type].push(f);
      }
      for (const type of Object.keys(byType)) {
        const sev = byType[type][0].severity;
        console.log(`[${type}] (${sev}) ${byType[type].length}건`);
        for (const f of byType[type]) {
          console.log(`  ${f.file}:${f.line}: ${f.message}`);
        }
        console.log('');
      }
    }
  }
  process.exit(errors.length === 0 ? 0 : 1);
}

main();
