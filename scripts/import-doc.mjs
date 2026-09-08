#!/usr/bin/env node
// HWPX/DOCX → MD 변환 파이프라인
// 사용법: node scripts/import-doc.mjs <path-to-hwpx-or-docx>
// 출력:
//   02_References/_sources/<name>.<ext>                       (원본 보존)
//   02_References/converted/<name>/<name>.md                  (변환 본문)
//   02_References/converted/<name>/figures/media/             (추출 이미지)
//   02_References/converted/<name>/<name>_review_pending.md   (검수 큐 사이드카)
//
// 분기:
//   .hwpx → Python(assets/extract_hwpx.py) 호출: 헤딩/표/이미지 직접 파싱 (권장)
//   .docx → Pandoc 호출: 한컴 export 한계로 헤딩 손실 가능
//
// JSON 결과를 stdout으로 출력. 호출자(슬래시 커맨드 등)가 파싱하여 사용자에게 안내.

import { spawnSync, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync,
  statSync, writeFileSync,
} from 'node:fs';
import { basename, dirname, extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, '..');

function fail(msg, extra = {}) {
  console.log(JSON.stringify({ ok: false, error: msg, ...extra }, null, 2));
  process.exit(1);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function countMatches(text, pattern) {
  const m = text.match(pattern);
  return m ? m.length : 0;
}

function listFigures(figuresDir) {
  if (!existsSync(figuresDir)) return [];
  const out = [];
  function walk(dir) {
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, ent.name);
      if (ent.isDirectory()) walk(full);
      else if (ent.isFile()) out.push(full);
    }
  }
  walk(figuresDir);
  return out;
}

function sha256(filePath) {
  const buf = readFileSync(filePath);
  return createHash('sha256').update(buf).digest('hex');
}

function findPandoc() {
  try {
    execFileSync('pandoc', ['--version'], { stdio: 'ignore' });
    return 'pandoc';
  } catch {}
  if (process.env.PANDOC_PATH && existsSync(process.env.PANDOC_PATH)) {
    return process.env.PANDOC_PATH;
  }
  if (process.platform === 'win32') {
    const wingetBase = join(process.env.LOCALAPPDATA || '', 'Microsoft', 'WinGet', 'Packages');
    if (existsSync(wingetBase)) {
      try {
        const dirs = readdirSync(wingetBase).filter(d => d.startsWith('JohnMacFarlane.Pandoc'));
        for (const dir of dirs) {
          const subdirs = readdirSync(join(wingetBase, dir)).filter(d => d.startsWith('pandoc-'));
          for (const subdir of subdirs) {
            const candidate = join(wingetBase, dir, subdir, 'pandoc.exe');
            if (existsSync(candidate)) return candidate;
          }
        }
      } catch {}
    }
  }
  const candidates = [
    join(process.env.ProgramFiles || '', 'Pandoc', 'pandoc.exe'),
    '/usr/bin/pandoc',
    '/usr/local/bin/pandoc',
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return null;
}

function findPython() {
  // 1) PATH
  for (const cmd of ['python', 'python3', 'py']) {
    try {
      execFileSync(cmd, ['--version'], { stdio: 'ignore' });
      return cmd;
    } catch {}
  }
  return null;
}

// ---- main ----
const inputArg = process.argv[2];
if (!inputArg) {
  fail('Usage: node scripts/import-doc.mjs <path-to-hwpx-or-docx>');
}

const inputAbs = resolve(inputArg);
if (!existsSync(inputAbs)) fail(`입력 파일이 없음: ${inputAbs}`);
if (!statSync(inputAbs).isFile()) fail(`파일이 아님: ${inputAbs}`);

const ext = extname(inputAbs).toLowerCase();
if (ext !== '.hwpx' && ext !== '.docx') {
  fail(`HWPX 또는 DOCX 파일이 아님: ${inputAbs}`);
}

const sourceName = basename(inputAbs, ext);
const refRoot = join(REPO_ROOT, '02_References');
const sourcesDir = join(refRoot, '_sources');
const sourcePath = join(sourcesDir, `${sourceName}${ext}`);
// 분리 구조:
//   converted/  : 본문 .md만 (1차 탐색 대상)
//   _figures/   : 이미지 (영구 자산, 문서별 서브폴더)
//   _reviews/   : 검수 큐 사이드카 (일시 자산)
const convertedRoot = join(refRoot, 'converted');
const figuresRoot = join(refRoot, '_figures');
const reviewsRoot = join(refRoot, '_reviews');
const mdPath = join(convertedRoot, `${sourceName}.md`);
const figuresDir = join(figuresRoot, sourceName);
const sidecarPath = join(reviewsRoot, `${sourceName}.review.md`);

mkdirSync(sourcesDir, { recursive: true });
mkdirSync(convertedRoot, { recursive: true });
mkdirSync(figuresDir, { recursive: true });
mkdirSync(reviewsRoot, { recursive: true });

// _sources/는 read-only 정책 (AGENTS.md). 변환 파이프라인의 "추가"는 허용하나
// 기존 원본을 덮어쓰지 않도록 동일성 체크. 같은 파일명으로 다른 내용이 들어오면 거부.
if (resolve(inputAbs) !== resolve(sourcePath)) {
  if (existsSync(sourcePath)) {
    const existingHash = sha256(sourcePath);
    const incomingHash = sha256(inputAbs);
    if (existingHash !== incomingHash) {
      fail(
        `_sources/${sourceName}${ext}가 이미 존재하지만 내용이 다름. ` +
        `덮어쓰기 거부 (AGENTS.md _xxx/ read-only 정책). ` +
        `다른 파일명으로 import하거나, 기존 원본 보존이 불필요하면 명시적으로 _sources/에서 먼저 제거할 것.`,
        {
          existingSha256: existingHash,
          incomingSha256: incomingHash,
          existingPath: relative(REPO_ROOT, sourcePath).replace(/\\/g, '/'),
        }
      );
    }
    // 같은 내용이면 copy skip (idempotent)
  } else {
    copyFileSync(inputAbs, sourcePath);
  }
}

const relSource = relative(REPO_ROOT, sourcePath).replace(/\\/g, '/');
const dateStr = today();
let backend = '';
let warnings = '';
let backendStats = null;  // HWPX 경로의 정확한 stats (h2, h3, tables, images, bullets)

if (ext === '.hwpx') {
  // ---- HWPX 경로: Python 파서 호출 ----
  const python = findPython();
  if (!python) {
    fail('python을 찾을 수 없음. python 또는 python3가 PATH에 있어야 함.');
  }
  const pyScript = join(REPO_ROOT, 'assets', 'extract_hwpx.py');
  const result = spawnSync(python, [
    pyScript,
    sourcePath,
    '-o', mdPath,
    '--figures-dir', figuresDir,
    '--source-rel', relSource,
  ], { encoding: 'utf8' });
  if (result.status !== 0) {
    fail('HWPX 파싱 실패', {
      stderr: result.stderr,
      stdout: result.stdout,
      script: pyScript,
    });
  }
  try {
    backendStats = JSON.parse(result.stdout.trim());
  } catch {
    backendStats = null;
  }
  warnings = (result.stderr || '').trim();
  backend = 'python (extract_hwpx.py)';
} else {
  // ---- DOCX 경로: Pandoc 호출 ----
  const pandoc = findPandoc();
  if (!pandoc) {
    fail('pandoc을 찾을 수 없음. winget install --id JohnMacFarlane.Pandoc 으로 설치 후 새 셸에서 재시도.');
  }
  const pandocArgs = [
    '--from', 'docx',
    '--to', 'markdown+grid_tables+pipe_tables+raw_html+footnotes',
    '--wrap=none',
    `--extract-media=${figuresDir}`,
    '--standalone',
    '-o', mdPath,
    sourcePath,
  ];
  const result = spawnSync(pandoc, pandocArgs, { encoding: 'utf8' });
  if (result.status !== 0) {
    fail('Pandoc 변환 실패', {
      stderr: result.stderr,
      stdout: result.stdout,
      pandoc,
      args: pandocArgs,
    });
  }

  // Frontmatter 주입 + 이미지 경로 상대화
  let content = readFileSync(mdPath, 'utf8');
  content = content.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '');

  // 이미지 경로: Pandoc이 절대경로(혼합 슬래시)로 박는 것을 MD 기준 상대경로로 치환
  // MD: 02_References/converted/<name>.md, figures: 02_References/_figures/<name>/
  // → link prefix: ../_figures/<name>
  const linkPrefix = relative(dirname(mdPath), figuresDir).replace(/\\/g, '/');
  const figuresAbsRegex = new RegExp(
    figuresDir
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')      // escape regex specials
      .replace(/\\\\/g, '[\\\\/]') ,                // accept either slash
    'g'
  );
  content = content.replace(figuresAbsRegex, linkPrefix);
  // 백슬래시 → 슬래시 (mixed-separator path inside ![](...))
  content = content.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, path) => {
    return `![${alt}](${path.replace(/\\/g, '/')})`;
  });

  const frontmatter = `---
title: ${sourceName}
tags: [reference, converted, docx]
source: ${relSource}
converted: ${dateStr}
created: ${dateStr}
updated: ${dateStr}
---
`;
  writeFileSync(mdPath, frontmatter + content);
  warnings = (result.stderr || '').trim();
  backend = `pandoc (${pandoc})`;
}

// ---- 공통: 통계 계산 + 사이드카 작성 ----
const finalContent = readFileSync(mdPath, 'utf8');
const tableMd = countMatches(finalContent, /\n[\t ]*\|[^\n]+\|\n[\t ]*\|[\s\-:|]+\|\n/g);  // 파이프 테이블 (들여쓰기 포함)
const tableGrid = countMatches(finalContent, /\n\+=+[=+]*\+\n/g);                 // grid 테이블 (헤더 구분선 +====+만)
const tableHtml = countMatches(finalContent, /<table[\s>]/g);
const h1Count = countMatches(finalContent, /\n# [^\n]+\n/g);
const h2Count = countMatches(finalContent, /\n## [^\n]+\n/g);
const figures = listFigures(figuresDir);

const stats = {
  tableMd,
  tableGrid,
  tableHtml,
  figures: figures.length,
  h1: h1Count,
  h2: h2Count,
};

const sidecar = `---
title: ${sourceName} 검수 큐
tags: [review-queue, converted]
source: ${relSource}
created: ${dateStr}
updated: ${dateStr}
---

# ${sourceName} 검수 큐

> 변환 과정의 자동 통계와 사람 검수가 필요한 항목 목록. 항목별 확인 후 본 줄에 \`[x]\` 체크. 모두 완료되면 본 사이드카 파일 삭제 가능.

## 변환 백엔드

\`${backend}\`

## 자동 통계

| 항목 | 수 |
|---|---|
| H1 헤딩 | ${stats.h1} |
| H2 헤딩 | ${stats.h2} |
| 파이프 테이블 (markdown) | ${stats.tableMd} |
| 그리드 테이블 (markdown, 복잡 구조) | ${stats.tableGrid} |
| HTML 테이블 (raw_html fallback) | ${stats.tableHtml} |
| 추출 이미지 | ${stats.figures} |

## 검수 체크리스트

### 헤딩 구조
- [ ] H1이 원본의 절 구분(N-M. ...)과 1:1 대응되는지
- [ ] H2(N-M-K. ...)가 누락 없이 매핑되었는지
- [ ] 챕터 헤더 줄(파일명과 중복)이 본문 첫 줄에서 제거되었는지

### 표
- [ ] 모든 표가 원본과 셀 내용 일치 (특히 그리드/HTML 테이블)
- [ ] 셀 병합이 있던 표가 의미적으로 보존됐는지 (rowspan/colspan)
- [ ] 표 헤더 행 위치 정확 (다중 헤더는 수동 점검 필요)
- [ ] 표 내 인용 수치 → 원본 \`[[${sourceName}|원본]]\` 대조

### 이미지
${figures.length === 0
  ? '- (추출된 이미지 없음)'
  : figures.map(f => `- [ ] \`${relative(refRoot, f).replace(/\\/g, '/')}\`: 본문 참조 위치 확인, 캡션 보존 여부 확인`).join('\n')}

### 본문 일관성
- [ ] 페이지/문단 누락 없음
- [ ] 각주/주석 보존
- [ ] 한자/특수문자 인코딩 정상

## 변환기 경고

${warnings ? '```\n' + warnings + '\n```' : '(경고 없음)'}

## 관련 문서

- 원본: \`${relSource}\`
- 변환본: [[${sourceName}]]
- 가이드: [[docx 변환 파이프라인]]
`;

writeFileSync(sidecarPath, sidecar);

// 결과 출력
console.log(JSON.stringify({
  ok: true,
  backend,
  source: relSource,
  converted: relative(REPO_ROOT, mdPath).replace(/\\/g, '/'),
  figuresDir: relative(REPO_ROOT, figuresDir).replace(/\\/g, '/'),
  sidecar: relative(REPO_ROOT, sidecarPath).replace(/\\/g, '/'),
  stats,
  backendStats,
  warnings: warnings || null,
}, null, 2));
