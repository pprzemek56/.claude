# CLAUDE.md

## General Rules

- Do NOT agree with everything. Challenge incorrect assumptions and statements.
- Be concise. Do only what is asked. If the task is unclear, ask — don't improvise.
- No comments in code unless explicitly requested.
- When fixing a bug, diagnose the root cause first, then propose a fix. No guessing.
- Preserve existing code style, naming conventions, and patterns. Match what's already there.
- If you're unsure between multiple approaches, briefly present the trade-offs and let the user decide.
- Never implement, plan, research on any unit tests for the project.
- Use the codesearch MCP tools before manual grep/glob when:
  - the relevant file is unknown,
  - the task requires cross-file understanding,
  - I ask where something is implemented,
  - I ask how a flow works,
  - the task involves finding similar existing patterns,
  - the task involves understanding architecture across multiple files.
- Use grep/glob only for:
  - exact string searches,
  - known file paths,
  - trivial one-line edits.
- When starting a non-trivial coding task, first use codesearch to locate the relevant files and existing patterns, then inspect the files directly before editing.

---

## Project-Specific Context

<!-- Fill this section per project -->

### Tech Stack

- Language:
- Framework:
- Database:
- Other:

### Architecture Notes

<!-- Key architectural decisions, patterns used, folder structure conventions -->

### Key Commands

<!-- Build, test, lint, deploy commands -->