#!/usr/bin/env node
// migrate_secref.mjs - 일회성 마이그레이션: 본문 § 참조를 wikilink anchor로 변환
// 사용법:
//   node scripts/migrate_secref.mjs            # dry-run (기본): 변환안과 미해결 목록 출력
//   node scripts/migrate_secref.mjs --write    # 반영
//   node scripts/migrate_secref.mjs --list     # 미해결 건만 출력 (수동 처리용)
//
// 왜 지금 넘버링으로 변환하나:
//   현행 헤딩 텍스트("다. 공통 화면") 그대로 anchor를 만들면, 변환 결과가 wiki_lint의
//   anchor 정합 검사로 전수 검증됨. 잘못 짚은 참조는 즉시 error로 드러남.
//   그 뒤 wiki_number가 새 넘버링으로 재번호하면서 anchor를 자동 연쇄 갱신함.
//   (재번호를 먼저 하면 776건이 한꺼번에 stale이 되어 손으로 매핑을 다시 짜야 함)
//
// 변환 규칙:
//   §5.다 생성과 변환 대기  →  [[#다. 생성과 변환 대기]]        (자기 문서)
//   공통 사양 §5.다 ...     →  [[시범콘텐츠 공통 사양#다. ...]]  (별칭 표로 대상 해석)
//   [[문서]] §5.다 ...      →  [[문서#다. ...]]                 (바로 앞 wikilink가 대상)
//   § 뒤 이름은 대상 헤딩 텍스트와 겹치는 만큼만 먹어치움 (조사와 문장은 남김)
//
// 변환 안 함 (수동 처리 대상으로 목록 출력):
//   - 대상 문서나 헤딩을 확정 못 하는 것
//   - 범위 참조 (§1-4): 헤딩 하나를 가리키지 않아 anchor로 표현 불가
//   - 인라인 코드(`...`)와 코드펜스 안
//
// 제외 파일/영역:
//   - 01_HowTo/반복 결함 카탈로그.md: § 용례가 과거 결함 사례 인용이라 당시 상태를 가리킴
//   - 02_References/(read-only), 99_Logs/log.md(이력), 04_Projects/_archive/(폐기 문서)

import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join, resolve, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, '..');

const EXCLUDED_PATHS = new Set([
  '02_References', '99_Logs', '04_Projects/_archive',
  '.claude', '.git', '.obsidian', 'node_modules', 'assets', 'export', 'scripts',
]);

// § 표기가 참조가 아니라 인용/예시인 파일
const SKIP_FILES = new Set([
  '01_HowTo/반복 결함 카탈로그.md',
]);

// § 앞 맨텍스트 → 대상 문서. 긴 것부터 매칭함
const ALIAS = [
  ['시범콘텐츠 공통 사양', '시범콘텐츠 공통 사양'],
  ['공통 사양', '시범콘텐츠 공통 사양'],
  ['플랫폼 사양', '플랫폼 사양'],
  ['CONVENTIONS.md', 'CONVENTIONS'],
  ['CONVENTIONS', 'CONVENTIONS'],
  ['AGENTS.md', 'AGENTS'],
  ['AGENTS', 'AGENTS'],
];

// 대상 후보가 동점일 때 고르는 순서 (자기 문서가 언제나 1순위, 그다음 이 표의 차례)
const PREFER = ['시범콘텐츠 공통 사양', '플랫폼 사양', 'CONVENTIONS', 'AGENTS'];

const KO = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하'];

const args = process.argv.slice(2);
const WRITE = args.includes('--write');
const LIST = args.includes('--list');

function normRel(p) { return p.split('\\').join('/'); }

function collectMd(rel = '') {
  const out = [];
  const dirPath = rel ? join(REPO_ROOT, rel) : REPO_ROOT;
  let entries;
  try { entries = readdirSync(dirPath); } catch { return out; }
  for (const entry of entries) {
    const relPath = rel ? `${rel}/${entry}` : entry;
    if (EXCLUDED_PATHS.has(relPath)) continue;
    const full = join(REPO_ROOT, relPath);
    let st;
    try { st = statSync(full); } catch { continue; }
    if (st.isDirectory()) out.push(...collectMd(relPath));
    else if (extname(entry) === '.md') out.push(normRel(relPath));
  }
  return out;
}

// 헤딩마다 레벨별 카운터를 붙여 둠. § 경로(예: 5.다 2))를 이 카운터로 찾음
function headingTree(content) {
  const heads = [];
  const lines = content.split('\n');
  const counters = [0, 0, 0, 0, 0];
  let inCode = false;
  let i = 0;
  if (lines[0] !== undefined && lines[0].trim() === '---') {
    for (i = 1; i < lines.length; i++) if (lines[i].trim() === '---') { i++; break; }
  }
  for (; i < lines.length; i++) {
    if (/^\s*```/.test(lines[i])) { inCode = !inCode; continue; }
    if (inCode) continue;
    const m = /^(#{1,6})\s+(.+?)\s*$/.exec(lines[i]);
    if (!m) continue;
    const level = m[1].length;
    if (level > 5) continue;
    counters[level - 1] += 1;
    for (let d = level; d < 5; d++) counters[d] = 0;
    heads.push({ level, text: m[2].trim(), path: counters.slice(0, level) });
  }
  return heads;
}

// 헤딩 텍스트에서 번호 접두사를 뗀 알맹이 (이름 대조용)
const BARE_RE = new RegExp(`^(?:\\(\\d+\\)|\\d+\\.|\\d+\\)|[${KO.join('')}]\\.|[${KO.join('')}]\\))\\s+`);
function bare(text) { return text.replace(BARE_RE, ''); }

// § 뒤 경로 토큰을 읽음. 반환: { toks:[{lvl,n},...], len:소비한 문자수 } 또는 null
// H1을 생략하고 H2부터 적는 형태(§다. 덧뵈기)도 받음: 그때는 lvl 2 토큰만 나옴
function parsePath(s) {
  if (/^\d+\s*[-~]\s*\d+/.test(s)) return null; // 범위 참조는 헤딩 하나를 가리키지 않음
  const toks = [];
  let p = 0;
  let m;
  if ((m = /^(\d+)/.exec(s.slice(p)))) {
    toks.push({ lvl: 1, n: +m[1] }); p += m[1].length;
    if ((m = /^\.([가-힣])(?![가-힣])/.exec(s.slice(p)))) {
      const idx = KO.indexOf(m[1]);
      if (idx < 0) return null;
      toks.push({ lvl: 2, n: idx + 1 }); p += 2;
    }
  } else if ((m = /^([가-힣])\./.exec(s.slice(p)))) {
    const idx = KO.indexOf(m[1]);
    if (idx < 0) return null;
    toks.push({ lvl: 2, n: idx + 1 }); p += 1;
  } else return null;

  if (toks.length >= 2 || toks[0].lvl === 2) {
    if ((m = /^\.(\d+)/.exec(s.slice(p)))) { toks.push({ lvl: 3, n: +m[1] }); p += 1 + m[1].length; }
    else if ((m = /^\s(\d+)\)/.exec(s.slice(p)))) { toks.push({ lvl: 3, n: +m[1] }); p += 2 + m[1].length; }
  }
  if (toks.some(t => t.lvl === 3)) {
    if ((m = /^\s([가-힣])\)/.exec(s.slice(p)))) {
      const idx = KO.indexOf(m[1]);
      if (idx >= 0) { toks.push({ lvl: 4, n: idx + 1 }); p += 3; }
    }
  }
  if (toks.some(t => t.lvl === 4)) {
    if ((m = /^\s\((\d+)\)/.exec(s.slice(p)))) { toks.push({ lvl: 5, n: +m[1] }); p += 3 + m[1].length; }
  }
  if (s[p] === '.') p += 1; // "§9." 처럼 끝에 붙은 마침표
  return { toks, len: p };
}

function pathLabel(toks) {
  return toks.map(t => `L${t.lvl}:${t.n}`).join('.');
}

// 경로에 맞는 헤딩 후보들. 여럿이면 이름 대조로 좁힘
function findHeadings(heads, toks) {
  const deepest = Math.max(...toks.map(t => t.lvl));
  return heads.filter(h => h.level === deepest && toks.every(t => h.path[t.lvl - 1] === t.n));
}

// § 뒤에 이어지는 텍스트에서 헤딩 이름과 겹치는 앞부분을 먹어치울 길이
function nameEatLen(after, headBare) {
  const t = after.replace(/^\s+/, '');
  const lead = after.length - t.length;
  let best = 0;
  const max = Math.min(t.length, headBare.length);
  for (let L = max; L >= 2; L--) {
    const cand = t.slice(0, L);
    if (!headBare.includes(cand)) continue;
    const next = t[L] ?? '';
    // 낱말 경계에서 끊겨야 함 (조사, 문장부호, 공백, 줄끝)
    if (next === '' || /[\s.,)\]:;'"」』]/.test(next) || /[은는이가을를의에로와과도만]/.test(next)) {
      best = L;
      break;
    }
  }
  return best === 0 ? 0 : lead + best;
}

function main() {
  const files = collectMd();
  const index = new Map();
  for (const f of files) index.set(basename(f, '.md'), f);
  const contents = new Map();
  for (const f of files) contents.set(f, readFileSync(join(REPO_ROOT, f), 'utf8'));
  const trees = new Map();
  for (const f of files) trees.set(f, headingTree(contents.get(f)));

  // 파일마다 그 안에서 wikilink로 부르는 문서들. 맨텍스트 § 의 대상 후보로 씀
  const docLinks = new Map();
  for (const f of files) {
    const names = new Set();
    for (const m of contents.get(f).matchAll(/\[\[([^\[\]|#]+?)(?:[#|][^\[\]]*?)?\]\]/g)) {
      const n = m[1].trim();
      if (n && index.has(n)) names.add(n);
    }
    docLinks.set(f, [...names]);
  }

  const converted = [];
  const skipped = [];
  const touched = new Set();

  for (const file of files) {
    if (SKIP_FILES.has(file)) continue;
    const lines = contents.get(file).split('\n');
    let inCode = false;
    let changed = false;

    for (let i = 0; i < lines.length; i++) {
      if (/^\s*```/.test(lines[i])) { inCode = !inCode; continue; }
      if (inCode) continue;
      if (!lines[i].includes('§')) continue;

      // 헤딩 줄은 건드리지 않음: 헤딩 텍스트가 바뀌면 그걸 가리키던 anchor가 전부 깨짐.
      // 헤딩 안 § 참조는 헤딩에서 걷어내는 편집이 필요하므로 수동 처리로 넘김
      if (/^#{1,6}\s/.test(lines[i])) {
        skipped.push({ file, line: i + 1, reason: '헤딩 줄 안의 § (헤딩에서 참조를 걷어내야 함)', text: lines[i].slice(0, 40) });
        continue;
      }

      // 인라인 코드와 기존 wikilink 안은 건드리지 않음 (위치만 표시)
      const codeMask = new Array(lines[i].length).fill(false);
      for (const cm of lines[i].matchAll(/`[^`]*`/g)) {
        for (let k = cm.index; k < cm.index + cm[0].length; k++) codeMask[k] = true;
      }
      for (const wm of lines[i].matchAll(/!?\[\[[^\[\]]*\]\]/g)) {
        for (let k = wm.index; k < wm.index + wm[0].length; k++) codeMask[k] = true;
      }

      let line = lines[i];
      let out = '';
      let pos = 0;
      while (true) {
        const at = line.indexOf('§', pos);
        if (at < 0) { out += line.slice(pos); break; }
        if (codeMask[at]) { out += line.slice(pos, at + 1); pos = at + 1; continue; }
        out += line.slice(pos, at);

        const rest = line.slice(at + 1);
        const parsed = parsePath(rest);
        if (!parsed) {
          const asWord = /^\s/.test(rest) || rest === '';
          skipped.push({
            file, line: i + 1,
            reason: asWord ? '§ 를 낱말로 씀 (참조 아님)' : '범위 참조 등 경로 해석 불가',
            text: line.slice(at, at + 34),
          });
          out += '§'; pos = at + 1; continue;
        }

        // 대상 문서 후보: 명시 힌트가 있으면 그것만, 없으면 자기 문서 + 이 파일이 링크하는 문서들
        const pre = out;
        let aliasEat = 0;
        let hinted = null;
        for (const [alias, doc] of ALIAS) {
          if (pre.endsWith(alias + ' ')) { hinted = doc; aliasEat = alias.length + 1; break; }
          if (pre.endsWith(alias)) { hinted = doc; aliasEat = alias.length; break; }
        }
        let linkAdjacent = false;
        if (!hinted && /\]\]\s*$/.test(pre)) {
          const lm = /\[\[([^\[\]|#]+?)(?:\\?\|[^\[\]]*?)?\]\]\s*$/.exec(pre);
          if (lm && index.has(lm[1].trim())) { hinted = lm[1].trim(); linkAdjacent = true; }
        }

        const candidates = hinted
          ? [index.get(hinted)].filter(Boolean)
          : [file, ...docLinks.get(file).map(n => index.get(n)).filter(Boolean)];

        const after = line.slice(at + 1 + parsed.len);

        // "§5 나~마" 처럼 하위 절 범위를 잇는 표기: 재번호하면 "나~마"가 뜻을 잃음. 손으로 고침
        if (/^\s*[가-하]\s*[~-]\s*[가-하]/.test(after)) {
          skipped.push({ file, line: i + 1, reason: '하위 절 범위 표기 (나~마 등)', text: line.slice(at, at + 34) });
          out += '§'; pos = at + 1; continue;
        }

        const hits = [];
        for (const cand of candidates) {
          if (!cand) continue;
          for (const h of findHeadings(trees.get(cand), parsed.toks)) {
            hits.push({ cand, head: h, eat: nameEatLen(after, bare(h.text)) });
          }
        }

        // 동점이면 자기 문서 우선, 그다음 정본 문서 순
        const rank = (c) => (c === file ? 0 : PREFER.indexOf(basename(c, '.md')) >= 0 ? 1 + PREFER.indexOf(basename(c, '.md')) : 99);
        const bestOf = (list) => {
          const r = Math.min(...list.map(h => rank(h.cand)));
          const top = list.filter(h => rank(h.cand) === r);
          if (top.length === 1) return top[0];
          if (top.every(h => h.cand === top[0].cand && h.head.text === top[0].head.text)) return top[0];
          return null;
        };

        let pick = null;
        const named = hits.filter(h => h.eat > 0);
        if (named.length > 0) {
          const best = Math.max(...named.map(h => h.eat));
          pick = bestOf(named.filter(h => h.eat === best));
        } else if (hits.length > 0) {
          pick = bestOf(hits);
        }

        if (!pick) {
          const where = hinted ?? '자기 문서 또는 이 파일이 링크하는 문서';
          skipped.push({
            file, line: i + 1,
            reason: hits.length === 0 ? `${where}에 해당 헤딩 없음 (stale 의심)` : '대상 헤딩이 여럿이라 확정 불가',
            text: line.slice(at, at + 34),
          });
          out += '§'; pos = at + 1; continue;
        }

        let cursor = at + 1 + parsed.len + pick.eat;

        // 별칭 맨텍스트("공통 사양 ")는 wikilink가 문서명을 품으므로 지움
        if (aliasEat > 0 && pick.cand !== file) out = out.slice(0, out.length - aliasEat);
        // "[[문서]] §5.다" 형태면 앞 wikilink를 anchor 붙은 것으로 흡수
        if (linkAdjacent && pick.cand !== file) {
          const lm = /\[\[([^\[\]|#]+?)(?:\\?\|[^\[\]]*?)?\]\]\s*$/.exec(out);
          if (lm && index.get(lm[1].trim()) === pick.cand) out = out.slice(0, out.length - lm[0].length);
        }

        const linkText = pick.cand === file
          ? `[[#${pick.head.text}]]`
          : `[[${basename(pick.cand, '.md')}#${pick.head.text}]]`;

        converted.push({ file, line: i + 1, from: line.slice(at, cursor), to: linkText });
        out += linkText;
        pos = cursor;
        changed = true;
      }
      if (changed) lines[i] = out;
    }
    if (changed) { contents.set(file, lines.join('\n')); touched.add(file); }
  }

  if (WRITE) for (const f of touched) writeFileSync(join(REPO_ROOT, f), contents.get(f), 'utf8');

  if (LIST) {
    console.log(`미해결 ${skipped.length}건 (수동 처리 대상)\n`);
    for (const s of skipped) console.log(`  ${s.file}:${s.line}  [${s.reason}]  ${s.text.replace(/\s+/g, ' ')}`);
    return;
  }

  console.log(`§ → wikilink anchor 변환 (${WRITE ? '반영' : 'dry-run'})`);
  console.log(`  변환 ${converted.length}건 / 미해결 ${skipped.length}건 / 대상 파일 ${touched.size}개\n`);
  console.log('=== 변환 샘플 (앞 20건) ===');
  for (const c of converted.slice(0, 20)) {
    console.log(`  ${c.file}:${c.line}`);
    console.log(`    ${c.from.replace(/\s+/g, ' ')}`);
    console.log(`    → ${c.to}`);
  }
  if (skipped.length > 0) {
    console.log(`\n=== 미해결 사유별 ===`);
    const by = {};
    for (const s of skipped) by[s.reason] = (by[s.reason] || 0) + 1;
    for (const [r, n] of Object.entries(by).sort((a, b) => b[1] - a[1])) console.log(`  ${String(n).padStart(3)}  ${r}`);
    console.log(`\n  전체 목록: node scripts/migrate_secref.mjs --list`);
  }
  if (!WRITE) console.log(`\n반영하려면: node scripts/migrate_secref.mjs --write`);
}

main();
