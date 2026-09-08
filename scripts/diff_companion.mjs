#!/usr/bin/env node
// diff_companion.mjs - 본문 변경과 파생 텍스트 동반 알림 (2026-08-21 MECH-4)
//
// 무엇을 하나:
//   스테이징된 .md diff에서, 절 본문이 바뀌었는데 그 절의 헤딩 줄과 문서 TL;DR이
//   그대로인 절을 "확인 요구" 목록으로 출력함. CONVENTIONS 5.2 문서 갱신 절차
//   4번(파생 텍스트 점검)의 기계 프롬프트임.
//
// 알림이지 판정이 아님:
//   대부분의 본문 수정은 헤딩과 TL;DR을 바꿀 필요가 없으므로, 이 목록은 확인할
//   후보이지 결함 판정이 아님. 그래서 커밋을 막지 않고 exit 0으로 끝남.
//   유형 B 결함(본문 수정 후 이름표와 요약 미동기 7건, 2026-08-21 검토안)을 겨냥함.
//
// 제외:
//   99_Logs/(이력), 04_Projects/_archive/(보존), 02_References/(변환 산출물)

import { execFileSync } from "node:child_process";

function git(args) {
	return execFileSync("git", args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}

let files;
try {
	files = git(["-c", "core.quotepath=false", "diff", "--cached", "--name-only", "--diff-filter=M", "--", "*.md"])
		.split("\n")
		.filter(Boolean);
} catch {
	process.exit(0);
}

const SKIP = [/^99_Logs\//, /^04_Projects\/_archive\//, /^02_References\//];
const report = [];

for (const f of files) {
	if (SKIP.some((re) => re.test(f))) continue;
	let diff, staged;
	try {
		diff = git(["diff", "--cached", "-U0", "--", f]);
		staged = git(["show", `:${f}`]);
	} catch {
		continue;
	}
	// 새 파일 기준 변경 줄 번호 수집 (hunk 헤더의 + 쪽)
	const changed = new Set();
	for (const m of diff.matchAll(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/gm)) {
		const start = Number(m[1]);
		const len = m[2] === undefined ? 1 : Number(m[2]);
		// 순수 삭제(len 0)도 그 자리의 절이 바뀐 것으로 봄
		for (let i = 0; i < Math.max(len, 1); i++) changed.add(start + i);
	}
	if (!changed.size) continue;
	// 스테이징 내용에서 헤딩과 TL;DR 위치 추출
	const lines = staged.split("\n");
	const headings = [];
	let tldrLine = 0;
	let inCode = false;
	for (let i = 0; i < lines.length; i++) {
		const line = lines[i];
		if (/^```/.test(line)) {
			inCode = !inCode;
			continue;
		}
		if (inCode) continue;
		const h = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
		if (h) headings.push({ line: i + 1, text: h[2] });
		if (!tldrLine && !headings.length && /^>\s/.test(line)) tldrLine = i + 1;
	}
	if (!headings.length) continue;
	// 변경 줄을 소속 절에 배정함
	const touched = new Map(); // 헤딩 인덱스 -> {headingChanged, bodyChanged}
	for (const n of changed) {
		let idx = -1;
		for (let i = 0; i < headings.length; i++) {
			if (headings[i].line <= n) idx = i;
			else break;
		}
		if (idx < 0) continue; // 프론트매터와 TL;DR 영역은 절 배정 없음
		const t = touched.get(idx) ?? { headingChanged: false, bodyChanged: false };
		if (headings[idx].line === n) t.headingChanged = true;
		else t.bodyChanged = true;
		touched.set(idx, t);
	}
	const suspects = [...touched.entries()]
		.filter(([, t]) => t.bodyChanged && !t.headingChanged)
		.map(([i]) => headings[i].text);
	if (!suspects.length) continue;
	report.push({ file: f, suspects, tldrUntouched: Boolean(tldrLine) && !changed.has(tldrLine) });
}

if (report.length) {
	console.log('[파생 텍스트 확인 요구] 본문이 바뀐 절의 제목, 라벨, 표 셀, TL;DR, MOC 요약이 여전히 맞는지 봄');
	console.log("  (CONVENTIONS 5.2 문서 갱신 4번. 알림이지 반려가 아님: 대부분은 바꿀 것이 없는 게 정상임)");
	for (const r of report) {
		console.log(`  ${r.file}${r.tldrUntouched ? " (TL;DR 미변경)" : ""}`);
		for (const s of r.suspects.slice(0, 12)) console.log(`    절 "${s}": 본문 변경, 헤딩 그대로`);
		if (r.suspects.length > 12) console.log(`    … 외 ${r.suspects.length - 12}개 절`);
	}
}
process.exit(0);
