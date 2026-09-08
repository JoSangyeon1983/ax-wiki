#!/usr/bin/env node
// quote_check.mjs - 원전 인용 자동 대조
// 사용법: node scripts/quote_check.mjs [파일...] [--source <전사본>] [--show] [--json]
//
// 무엇을 하나:
//   문서의 큰따옴표 인용 가운데 행 번호가 붙은 것을 골라, 그 행의 전사본 원문과
//   문자 단위로 대조함. 행 번호는 전사본 .md 파일의 줄 번호를 뜻함(2026-08-20 확인).
//
// 왜 있나:
//   2026-08-19에 확인된 오류 약 30건 중 17건이 원전을 인용하는 자리였고, 어긋난
//   인용이 하나같이 작성자 주장을 강화하는 방향이었음. 사람이 매번 원문을 다시
//   여는 것에 기대지 않고 기계가 대조하도록 옮긴 것임.
//   AGENTS.md 셀프체크 [인용 재대조] 항목의 실행 도구임.
//
// 판정:
//   OK       인용문이 지목한 행에 그대로 있음
//   MISPLACE 지목한 행에는 없고 다른 행에 있음 (행 번호 오귀속)
//   NOTFOUND 전사본 어디에도 없음 (개작이나 창작). 가장 비슷한 행을 함께 보여줌
//   RANGE    행 번호가 전사본 범위를 벗어남
//
//   여러 행을 쉼표로 나열하면 "그 행들 각각에 있다"는 주장으로 보고 전부 대조함.
//   물결(424~444행)은 "그 구간 안에 있다"는 주장으로 보고 구간 안에서 찾음.
//
//   따옴표 인용이 없어도 행 번호 참조 자체는 검사함 (2026-08-21 확장): 전사본 범위를
//   벗어나거나 시작이 끝보다 큰 참조를 RANGE로 잡음. CONVENTIONS 3.6의 근거 마커
//   (행 범위 또는 원문 미명시)의 행 번호 유효성 검사임. 참조가 가리키는 요약의
//   충실성은 기계가 못 보므로 사람 검토로 남음.
//
//   절 제목의 주장 어휘도 경고함 (2026-08-21 MECH-5 부분 수용): 전사본을 다루는
//   문서의 헤딩이 승패나 결말을 주장하면(scripts/heading_claim_terms.txt 등록 어휘)
//   경고를 출력함. 어휘 매칭은 오탐이 있을 수 있어 경고만 하고 exit code에 안 넣음.
//
// 대조 방식:
//   전사본 줄에서 마크다운 강조 기호(*)만 걷고 나머지는 손대지 않음. 띄어쓰기와
//   문장부호까지 그대로 봄. 인용문 안의 말줄임(… 또는 ...)은 생략으로 보고,
//   앞뒤 조각이 같은 줄에 순서대로 있으면 일치로 침.
//
// exit code:
//   0: OK 외 판정 0건
//   1: 1건 이상
//
// 전사본 지정:
//   1) --source <경로>
//   2) 문서 frontmatter의 sources에 적힌 이름이 02_References/converted/ 아래 파일과 맞으면 그것
//   3) 문서 경로나 제목에 종목 이름(덧뵈기, 덜미, 살판)이 있으면 그 전사본
//   셋 다 안 되면 그 문서는 건너뛰고 알림

import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const TRANSCRIPT_DIR = path.join(ROOT, "02_References/converted/남사당놀이");
const SCAN_DIRS = ["00_Index", "03_Concepts", "01_HowTo", "02_References", "04_Projects", "05_산출물", "07_작업노트", "90_Temp", "prototype"];

const args = process.argv.slice(2);
const flags = new Set(args.filter((a) => a.startsWith("--")));
const sourceIdx = args.indexOf("--source");
const explicitSource = sourceIdx >= 0 ? args[sourceIdx + 1] : null;
const targets = args.filter((a, i) => !a.startsWith("--") && i !== sourceIdx + 1);
const asJson = flags.has("--json");
const showRefs = flags.has("--show");

// ── 전사본 색인 ────────────────────────────────────────────────
const transcripts = new Map(); // basename(확장자 없음) -> {path, lines}
function loadTranscript(p) {
	const abs = path.isAbsolute(p) ? p : path.join(ROOT, p);
	const key = path.basename(abs, ".md");
	if (transcripts.has(key)) return transcripts.get(key);
	const lines = fs.readFileSync(abs, "utf8").split("\n");
	const t = { path: path.relative(ROOT, abs).replace(/\\/g, "/"), lines };
	transcripts.set(key, t);
	return t;
}
if (fs.existsSync(TRANSCRIPT_DIR)) {
	for (const f of fs.readdirSync(TRANSCRIPT_DIR)) {
		if (f.endsWith(".md")) loadTranscript(path.join(TRANSCRIPT_DIR, f));
	}
}

// ── 대상 문서 수집 ─────────────────────────────────────────────
function walk(dir, out) {
	if (!fs.existsSync(dir)) return out;
	for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
		const p = path.join(dir, e.name);
		if (e.isDirectory()) {
			if (/^(node_modules|\.git|\.obsidian|_figures|_reviews)$/.test(e.name)) continue;
			walk(p, out);
		} else if (e.name.endsWith(".md")) out.push(p);
	}
	return out;
}
let docs;
if (targets.length) {
	docs = targets.map((t) => (path.isAbsolute(t) ? t : path.join(ROOT, t)));
} else {
	docs = [];
	for (const d of SCAN_DIRS) walk(path.join(ROOT, d), docs);
	// 전사본 자신과 로그는 대상이 아님
	docs = docs.filter((p) => !p.replace(/\\/g, "/").includes("02_References/converted/"));
	docs = docs.filter((p) => /\d{2,4}행/.test(fs.readFileSync(p, "utf8")));
}

// ── 전사본 결정 ────────────────────────────────────────────────
function resolveSource(docPath, text) {
	if (explicitSource) return loadTranscript(explicitSource);
	const fm = text.match(/^---\n([\s\S]*?)\n---/);
	if (fm) {
		for (const key of transcripts.keys()) {
			if (fm[1].includes(key)) return transcripts.get(key);
		}
	}
	const hay = docPath.replace(/\\/g, "/");
	for (const key of transcripts.keys()) {
		const jong = key.replace(/^남사당놀이 - /, "");
		if (hay.includes(jong)) return transcripts.get(key);
	}
	return null;
}

// ── 인용 추출 ──────────────────────────────────────────────────
const REF_RE = /((?:\d{1,4}(?:\s*[~\-–]\s*\d{1,4})?\s*,\s*)*\d{1,4}(?:\s*[~\-–]\s*\d{1,4})?)\s*행/;

function parseRefs(win) {
	const m = win.match(REF_RE);
	if (!m) return null;
	const out = [];
	for (const part of m[1].split(",")) {
		const r = part.trim().match(/^(\d{1,4})(?:\s*[~\-–]\s*(\d{1,4}))?$/);
		if (!r) continue;
		const a = Number(r[1]);
		if (r[2]) out.push({ from: a, to: Number(r[2]) });
		else out.push({ from: a, to: a });
	}
	return out.length ? out : null;
}

// 창 안에서 행 참조를 찾고 인용문과 떨어진 거리를 함께 돌려줌.
// forward는 인용문이 끝난 자리부터의 거리임.
// backward는 "원전 666행 "인용"" 꼴만 인정하므로 정규식이 끝의 공백만 허용함.
// 이렇게 묶지 않으면 "…(488행)라 하고, 잽이가 "다른 인용""에서 앞 인용의
// 행 번호를 끌어옴.
const BACK_RE = new RegExp(REF_RE.source + "\\s*$");

// 앞쪽 창의 행 참조를 전부 모음. 한 인용에 참조가 여럿 붙는 꼴이 흔하기 때문임
// (예: `- **"인용"**: 첫째 마당 꺽쇠(201행)와 넷째 마당 취발이(666행)가 똑같이 부름`).
// 첫 참조만 보면 뒤에 붙은 어긋난 참조를 놓침.
function collectForwardRefs(win) {
	const re = new RegExp(REF_RE.source, "g");
	const out = [];
	let m;
	// 인용문 바로 뒤에 행 번호가 붙어 있으면(`"인용"(426행) 하고 …`) 그 하나만이
	// 이 인용의 근거임. 뒤에 더 나오는 행 번호는 다음 문장 몫이라 끌어오면 안 됨.
	// 반대로 라벨 꼴(`- **"인용"**: 꺽쇠(201행)와 취발이(666행)가 …`)은 뒤에
	// 나열되는 것이 전부 이 인용의 근거이므로 다 모음.
	const first = win.match(REF_RE);
	const adjacent = first && first.index <= 2;
	while ((m = re.exec(win)) !== null) {
		// "13행"은 13번째 줄일 수도 13개 줄일 수도 있음. 구문으로 가름.
		// 인용은 괄호에 담기거나("(488행)") 조사가 붙음("666행에").
		// 개수는 그냥 끝남("전사본에 13행."). 개수면 대조 대상이 아님
		const pre = win.slice(0, m.index);
		const rest = win.slice(m.index + m[0].length);
		const inParen = pre.lastIndexOf("(") > pre.lastIndexOf(")");
		if (!inParen && !/^[에의와과,)]/.test(rest)) continue;
		const parsed = parseRefs(m[0]);
		if (parsed) out.push(...parsed);
		if (adjacent) break;
	}
	return out.length ? out : null;
}

function parseBackwardRefs(win) {
	const m = win.match(BACK_RE);
	return m ? parseRefs(m[0]) : null;
}

const strip = (s) => s.replace(/\*/g, "");

function fragmentsOf(quote) {
	return strip(quote)
		.split(/…+|\.{3,}/)
		.map((f) => f.trim())
		.filter(Boolean);
}

function lineHas(line, frags) {
	const hay = strip(line);
	let at = 0;
	for (const f of frags) {
		const i = hay.indexOf(f, at);
		if (i < 0) return false;
		at = i + f.length;
	}
	return true;
}

function findAnywhere(lines, frags) {
	const hits = [];
	for (let i = 1; i < lines.length + 1; i++) {
		if (lines[i - 1] !== undefined && lineHas(lines[i - 1], frags)) hits.push(i);
	}
	return hits;
}

function closestLine(lines, quote) {
	const q = strip(quote);
	let best = { n: 0, len: 0 };
	for (let i = 1; i <= lines.length; i++) {
		const hay = strip(lines[i - 1] ?? "");
		let len = 0;
		// 인용문의 앞에서부터 가장 길게 포함되는 조각을 찾음
		for (let k = Math.min(q.length, 60); k >= 4; k--) {
			if (hay.includes(q.slice(0, k))) { len = k; break; }
		}
		if (len > best.len) best = { n: i, len };
	}
	return best.len >= 4 ? best : null;
}

// ── 제목 주장 어휘 목록 ────────────────────────────────────────
function loadHeadingClaimTerms() {
	const p = path.join(ROOT, "scripts/heading_claim_terms.txt");
	if (!fs.existsSync(p)) return [];
	return fs.readFileSync(p, "utf8")
		.split("\n")
		.map((l) => l.trim())
		.filter((l) => l && !l.startsWith("#"));
}
const claimTerms = loadHeadingClaimTerms();

// ── 검사 ───────────────────────────────────────────────────────
const findings = [];
const skipped = [];
const headingWarns = [];
const rangeSeen = new Set(); // 같은 자리의 RANGE를 인용 경로와 참조 경로가 중복 보고하지 않게 함
let quoteCount = 0;
let docCount = 0;

for (const docPath of docs) {
	const rel = path.relative(ROOT, docPath).replace(/\\/g, "/");
	const text = fs.readFileSync(docPath, "utf8");
	const src = resolveSource(docPath, text);
	if (!src) { skipped.push(rel); continue; }
	docCount++;
	const lines = text.split("\n");
	const max = src.lines.length;

	// 절 제목 주장 어휘 경고 (코드블록 안 헤딩은 제외)
	{
		let inCode = false;
		for (let i = 0; i < lines.length; i++) {
			if (/^```/.test(lines[i])) { inCode = !inCode; continue; }
			if (inCode) continue;
			const h = /^#{1,6}\s+(.+?)\s*$/.exec(lines[i]);
			if (!h) continue;
			for (const term of claimTerms) {
				if (h[1].includes(term)) {
					headingWarns.push({ file: rel, line: i + 1, heading: h[1], term });
				}
			}
		}
	}

	for (let ln = 0; ln < lines.length; ln++) {
		const line = lines[ln];
		const qre = /"([^"\n]{2,})"/g;
		let m;
		while ((m = qre.exec(line)) !== null) {
			const quote = m[1];
			// 행 번호는 인용문 뒤("인용"(488행))에도 앞(원전 666행 "인용")에도 옴.
			// 한 줄에 인용이 여럿이면 옆 인용의 행 번호를 끌어올 수 있으므로,
			// 창을 이웃한 따옴표에서 끊어 그 인용에 딸린 범위만 봄.
			const after = line.slice(m.index + m[0].length);
			const fwdWin = after.slice(0, Math.min(60, after.indexOf('"') < 0 ? 60 : after.indexOf('"')));
			const before = line.slice(0, m.index);
			const prevQ = before.lastIndexOf('"');
			const backWin = before.slice(prevQ < 0 ? 0 : prevQ + 1).slice(-24);
			const refs = collectForwardRefs(fwdWin) ?? parseBackwardRefs(backWin);
			if (!refs) continue;
			quoteCount++;
			const frags = fragmentsOf(quote);
			if (!frags.length) continue;

			const bad = [];
			for (const r of refs) {
				if (r.from > max || r.to > max) { bad.push({ kind: "RANGE", ref: r }); continue; }
				let ok = false;
				for (let i = r.from; i <= r.to; i++) {
					if (lineHas(src.lines[i - 1] ?? "", frags)) { ok = true; break; }
				}
				if (!ok) bad.push({ kind: "MISS", ref: r });
			}
			if (!bad.length) continue;

			const elsewhere = findAnywhere(src.lines, frags);
			for (const b of bad) {
				const label = b.ref.from === b.ref.to ? `${b.ref.from}행` : `${b.ref.from}~${b.ref.to}행`;
				if (b.kind === "RANGE") {
					rangeSeen.add(`${rel}:${ln + 1}:${label}`);
					findings.push({ file: rel, line: ln + 1, verdict: "RANGE", quote, ref: label,
						note: `전사본은 ${max}행까지임` });
				} else if (elsewhere.length) {
					findings.push({ file: rel, line: ln + 1, verdict: "MISPLACE", quote, ref: label,
						note: `${elsewhere.join(", ")}행에 있음` });
				} else {
					const c = closestLine(src.lines, quote);
					findings.push({ file: rel, line: ln + 1, verdict: "NOTFOUND", quote, ref: label,
						note: c ? `가장 가까운 행 ${c.n}: ${strip(src.lines[c.n - 1]).trim().slice(0, 90)}` : "비슷한 행 없음" });
				}
			}
		}

		// 따옴표 인용이 없는 행 번호 참조의 범위 검사 (2026-08-21 확장).
		// "13행"이 개수(분량)일 수 있으므로 인용 경로와 같은 구문 가름(괄호나 조사)을 적용함
		{
			const bare = line.replace(/"[^"\n]*"/g, "");
			const re = new RegExp(REF_RE.source, "g");
			let bm;
			while ((bm = re.exec(bare)) !== null) {
				const pre = bare.slice(0, bm.index);
				const rest = bare.slice(bm.index + bm[0].length);
				const inParen = pre.lastIndexOf("(") > pre.lastIndexOf(")");
				if (!inParen && !/^[에의와과,)]/.test(rest)) continue;
				for (const r of parseRefs(bm[0]) ?? []) {
					const label = r.from === r.to ? `${r.from}행` : `${r.from}~${r.to}행`;
					let note = null;
					if (r.from > max || r.to > max) note = `전사본은 ${max}행까지임`;
					else if (r.from > r.to) note = "범위 시작이 끝보다 큼";
					if (!note) continue;
					const key = `${rel}:${ln + 1}:${label}`;
					if (rangeSeen.has(key)) continue;
					rangeSeen.add(key);
					findings.push({ file: rel, line: ln + 1, verdict: "RANGE", quote: "", ref: label, note });
				}
			}
		}

		if (showRefs) {
			const bare = line.replace(/"[^"\n]*"/g, "");
			const refs = parseRefs(bare);
			if (refs) {
				for (const r of refs) {
					for (let i = r.from; i <= Math.min(r.to, max); i++) {
						findings.push({ file: rel, line: ln + 1, verdict: "SHOW", quote: "", ref: `${i}행`,
							note: strip(src.lines[i - 1] ?? "").trim().slice(0, 110) });
					}
				}
			}
		}
	}
}

// ── 보고 ───────────────────────────────────────────────────────
const real = findings.filter((f) => f.verdict !== "SHOW");

if (asJson) {
	console.log(JSON.stringify({ docCount, quoteCount, findings, skipped, headingWarns }, null, 2));
	process.exit(real.length ? 1 : 0);
}

console.log(`Quote check: ${docCount}개 문서, 행 번호가 붙은 인용 ${quoteCount}건 대조`);

if (showRefs) {
	const shows = findings.filter((f) => f.verdict === "SHOW");
	if (shows.length) {
		console.log(`\n[참조 행 보기] ${shows.length}건 (사람이 눈으로 대조할 것)`);
		let cur = "";
		for (const f of shows) {
			if (f.file !== cur) { cur = f.file; console.log(`\n  ${cur}`); }
			console.log(`    :${f.line}  ${f.ref}  ${f.note}`);
		}
	}
}

if (headingWarns.length) {
	console.log(`\n[제목 주장 어휘 경고] ${headingWarns.length}건 (제목은 가리키기만 하고 주장하지 않음, CONVENTIONS 4.1. 경고만 하고 커밋은 안 막음)`);
	for (const w of headingWarns) {
		console.log(`  ${w.file}:${w.line}  "${w.heading}" (어휘: ${w.term})`);
	}
}

if (!real.length) {
	console.log("✓ 어긋난 인용 0건");
	if (skipped.length) console.log(`  (전사본을 정하지 못해 건너뜀: ${skipped.length}건)`);
	process.exit(0);
}

const byFile = new Map();
for (const f of real) {
	if (!byFile.has(f.file)) byFile.set(f.file, []);
	byFile.get(f.file).push(f);
}
console.log(`\n[어긋난 인용] ${real.length}건 (${byFile.size}개 파일)`);
for (const [file, fs_] of byFile) {
	console.log(`\n  ${file}`);
	for (const f of fs_) {
		console.log(`    :${f.line}  ${f.verdict}  ${f.ref}  "${f.quote.slice(0, 70)}${f.quote.length > 70 ? "…" : ""}"`);
		console.log(`           ${f.note}`);
	}
}
if (skipped.length) console.log(`\n  (전사본을 정하지 못해 건너뜀: ${skipped.length}건)`);
process.exit(1);
