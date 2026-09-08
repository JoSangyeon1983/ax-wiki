#!/usr/bin/env node
// stale_line_reminder.mjs - 편집 성공 후 행 번호 기억 무효 알림 (2026-08-21 MECH-6)
// Claude Code PostToolUse 훅(.claude/settings.json)이 Edit/Write/NotebookEdit 뒤에 호출함.
// 편집으로 행이 밀린 파일의 행 번호를 기억으로 인용하는 결함(문서 개정 검토안 유형 C)을 막음.
let d = "";
process.stdin.on("data", (c) => (d += c));
process.stdin.on("end", () => {
  let f = "";
  try {
    const j = JSON.parse(d);
    f = (j.tool_input && (j.tool_input.file_path || j.tool_input.notebook_path)) || "";
  } catch {
    // 입력이 깨졌으면 알림 없이 조용히 끝냄
  }
  if (!f.endsWith(".md")) return; // 행 번호 인용 규칙은 문서에만 해당하므로 소음을 줄임
  console.log(
    JSON.stringify({
      suppressOutput: true,
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: `[행 번호 무효] 방금 편집으로 ${f}의 행 번호가 밀렸을 수 있음. 이 파일의 행 번호를 인용하려면 기억이 아니라 파일을 다시 열어 확인할 것 (AGENTS 셀프체크 [인용 재대조])`,
      },
    }),
  );
});
