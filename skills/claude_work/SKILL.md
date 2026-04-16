---
name: claude_work
description: Set up and manage a claude_work/ workspace at the project root for tracking Claude-collaboration artifacts (prompts, implementation plans, roadmaps, per-task docs). Use when the user asks to "init claude_work", "setup claude work", "start a new claude task", "zacznij nowy task", "zarchiwizuj task", or wants to scaffold/manage the claude_work directory structure.
---

# Instructions

This skill manages a `claude_work/` directory at the project root. Its purpose is to capture the documentation produced while collaborating with Claude on a specific task: prompts used, implementation plans, progress roadmaps, and per-task notes.

## Directory convention

```
<repo-root>/
  claude_work/
    archive/              # completed tasks moved here, still tracked in git
    <task-id>/            # active task (e.g. JIRA-185, FEATURE-login, etc.)
      prompts.md
      implementation_plan.md
      roadmap.md
      notes.md
```

Rules:
- `claude_work/` lives at the **git repo root** (resolve via `git rev-parse --show-toplevel`), never inside `.claude/`.
- Everything under `claude_work/` (including `archive/`) is tracked — do not add it to `.gitignore`.
- One subdirectory per task. Task id is the user's naming (Jira key, feature name, etc.). Do not invent names.
- When a task is finished, move its directory into `archive/`.

## Invocation modes

Decide the mode from the user's message:

### 1. Init / setup

Triggered by: "init claude_work", "setup claude work", "stwórz katalog roboczy", or when `claude_work/` is missing and the user wants to start tracking.

Steps:
1. Resolve repo root: `git rev-parse --show-toplevel`.
2. Create `<root>/claude_work/` and `<root>/claude_work/archive/` if they do not exist.
3. Do NOT modify `.gitignore`.
4. Report what was created vs. already present. Do not scaffold task files in this mode.

### 2. New task

Triggered by: "new task <id>", "start task <id>", "zacznij nowy task <id>", or when the user names a task to begin tracking.

Steps:
1. Ensure `claude_work/` and `claude_work/archive/` exist (run init mode first if not).
2. Ask the user for the task id if not provided. Never guess.
3. Create `claude_work/<task-id>/`.
4. Scaffold the four files listed below with minimal placeholder content (see templates). Do not overwrite existing files — if a file exists, skip it and report.
5. Report the created path and the files scaffolded.

### 3. Archive task

Triggered by: "archive task <id>", "zarchiwizuj task <id>", "zakończ task <id>".

Steps:
1. Confirm `claude_work/<task-id>/` exists.
2. Move it to `claude_work/archive/<task-id>/` using `git mv` so the history is preserved (fall back to `mv` if the files are untracked).
3. Report the new location. Do not delete anything.

### 4. Update task docs

Triggered by: user asks to save a prompt, update the plan, record progress, etc., and a task directory is known or discoverable.

Update the relevant file (`prompts.md`, `implementation_plan.md`, `roadmap.md`, `notes.md`) by appending. Use dated sections (`## YYYY-MM-DD`) when adding new entries so history is preserved.

## File templates

Keep scaffolds minimal — placeholders only. The user fills them in or asks Claude to update them.

**prompts.md**
```markdown
# Prompts — <task-id>

Record prompts used for planning, implementation, review, etc. Group by phase.

## Planning

## Implementation

## Review
```

**implementation_plan.md**
```markdown
# Implementation plan — <task-id>

## Goal

## Scope

## Steps

## Out of scope
```

**roadmap.md**
```markdown
# Roadmap — <task-id>

Track progress with dated entries.

## YYYY-MM-DD
- 
```

**notes.md**
```markdown
# Notes — <task-id>

Free-form documentation, decisions, links, references.
```

Replace `<task-id>` in the headings with the actual task id when scaffolding.

## Non-goals

- Do not add or remove `.gitignore` entries.
- Do not commit the changes — that is a separate step; the user or the `commit` skill handles it.
- Do not create directories or files outside `claude_work/`.
- Do not assume a task id — always use what the user provided.
