---
name: double-planning
description: Produce an implementation plan that survives adversarial review. Use when the user asks to "plan task X", "write implementation plan for <task>", "double-planning <task>", "prepare a plan with codex review", or provides a research brief in claude_work/<task>/prompts.md and wants a planning pass (not implementation). The skill produces two artefacts — implementation_plan.md (full plan) and roadmap.md (lightweight 1:1 checklist) — after a single adversarial review round by an external reviewer (Codex CLI). You are the planner, not the developer. Do not write code. Do not implement without a plan file.
---

# double-planning

Produce an implementation plan that has been stress-tested by adversarial review before it reaches a developer. The output is two files: a full `implementation_plan.md` that a developer can follow 1:1 and a lightweight `roadmap.md` they use as a progress checklist.

## When to use

- User has a research/brief file at `claude_work/<task_name>/prompts.md` and wants the planning pass.
- User asks for "plan X", "implementation plan for <task>", "double-planning <task>", "przygotuj plan z review", etc.
- A task name is provided or can be inferred (`ls -t claude_work/ | head -1`).

## When NOT to use

- User wants implementation, not planning (use the `development` skill instead).
- No `prompts.md` exists for the task — ask the user to run research first.
- User wants a quick sketch, not a rigorous plan — this skill is deliberately heavyweight.

## Inputs

- `claude_work/<task_name>/prompts.md` — the research brief. Typical sections:
  - **Business goal** — the product-level "why".
  - **Design decisions (LOCKED / AGREED / do not challenge)** — sacred. Implement faithfully, do not relitigate.
  - **What the plan MUST contain** — compliance checklist the plan is scored against.
  - **What the plan MUST NOT contain** — anti-scope.
  - **Key reference files** — concrete paths to read before planning.

Treat every section literally. LOCKED decisions are not open for negotiation — neither by the planner nor by the reviewer.

## Workflow

The workflow is five steps. Do not skip and do not reorder.

### Step 0 — Reconnaissance

Goal: understand the task before writing anything.

1. Read `claude_work/<task_name>/prompts.md` **in full**. Pay attention to the five sections above.
2. Read **every** file listed in *Key reference files*. If the section is missing, identify 5–15 files that matter (entrypoints, schemas, example plans from `claude_work/archive/`) and read them.
3. Follow obvious in-file references (imports, linked paths) if they reveal constraints relevant to the plan.
4. **Checkpoint in chat:** 2–3 sentences summarising what the task is about + a list of files you read. This is a visible commitment that you actually grounded yourself before planning.

Rule: if you do not know something, read the file. Do not guess paths, commands, or APIs.

### Step 1 — Plan v1

Emit the first draft under the heading `## PLAN v1` in the chat (do not write to disk yet). Use this structure:

1. **Goal and scope** — what we are building, and what is explicitly out of scope (mirror the research's anti-scope).
2. **Files to change / create** — absolute or repo-relative paths, one sentence per file, `NEW` for new files. Verify every existing path.
3. **Implementation order** — numbered steps. **Each step independently testable** (after completing a step, a `check` command must exist that proves the step landed correctly without the next step being done). Include the check command inline per step.
4. **Architectural decisions** — choice + at least one rejected alternative + rationale. For LOCKED decisions from `prompts.md`, **do not replay the debate**; state only how the plan realises the LOCKED decision.
5. **Edge cases and traps** — concrete risks, not generic platitudes.
6. **Acceptance criteria** — reproducible, binary pass/fail. Prefer shell commands and SQL queries over prose.

Before closing Step 1, **self-verify compliance**:

- If `prompts.md` has *What the plan MUST contain*, walk the checklist point by point. For each point, cite the section of the plan that covers it. If a point is not covered, extend the plan.
- If `prompts.md` has *What the plan MUST NOT contain*, check every scope element against that list. Remove anything that slipped in.

Discipline:

- No code. Signatures (function headers, class shells, table column lists) are allowed for clarity.
- "Use X because Y", never "consider X".
- Paths verified against the actual filesystem.
- Prefer specificity: package names with version ranges, exact commands, exact env var names.

### Step 2 — Adversarial review by Codex

Invoke the external reviewer with the template below. Emit the response under `## CODEX REVIEW` in the chat.

```bash
codex exec "$(cat <<'EOF'
You are a senior software engineer doing an adversarial code review of an implementation plan. Your job is to FIND problems, not to smooth the plan over. If the plan is good, say so briefly and stop. If not, be specific.

IMPORTANT: the research contains sections marked LOCKED / AGREED / "do not challenge". These are user-level business and architectural decisions — NOT your battlefield. Your job is to check that the plan faithfully implements them, not whether they are good. Challenging LOCKED decisions wastes everyone's time. If the plan breaks a LOCKED decision — THAT is a blocker. If the plan implements a LOCKED decision in a way you consider suboptimal but consistent with the research — do not report it.

Focus on:
- Does the plan realise EVERY point from "What the plan MUST contain" (if present)?
- Does the plan NOT enter any area from "What the plan MUST NOT contain" (if present)?
- Does it faithfully realise every LOCKED / AGREED decision?
- Are file paths sane and consistent with repo conventions?
- Is the implementation order actually testable step by step?
- Do the edge cases cover real risks?
- Are there hidden assumptions the developer will have to guess?

Research (context + LOCKED decisions):
<paste the FULL content of claude_work/<task_name>/prompts.md>

Plan under review:
<paste the FULL content of PLAN v1 from Step 1>

Response format — markdown only, no preamble:

## BLOCKERS
Things that will break the implementation, violate research requirements (especially LOCKED), break anti-scope, or are architecturally wrong. If none — write "None".

1. <title>
   **Problem:** <2-3 sentences>
   **Proposal:** <concrete fix>

## SUGGESTIONS
Things that would improve the plan but are not critical. Max 5. Not about LOCKED decisions. If none — "None".

1. <title>
   **Problem:** <1-2 sentences>
   **Proposal:** <concrete fix>

## NITPICKS
Stylistic nits. Max 3. If none — "None".

1. <title>: <one sentence>

Do not praise. Do not summarise. Only numbered issues in the format above.
EOF
)"
```

Practical packaging tip: assemble the prompt in a temp file (prefix text + `prompts.md` content + plan content + suffix text with the response format), then `codex exec "$(cat /tmp/codex_input.md)"` with a generous timeout (5–10 minutes).

### Step 3 — Triage

For **every** blocker and suggestion, emit under `## TRIAGE`:

```
### [BLOCKER|SUGGESTION] <n>: <title>
**Decision:** ACCEPT | REJECT | MODIFY
**Rationale:** <2-3 sentences>
```

Decision rules:

- **Codex challenges a LOCKED decision** → automatic REJECT with note "out of scope: LOCKED decision". Do not debate.
- **BLOCKER with decision REJECT (non-LOCKED)** — requires a solid substantive counterargument. "I disagree" is not enough. If you do not have a strong counter, ACCEPT.
- **SUGGESTION** — you can REJECT more freely, but still with rationale.
- **MODIFY** = accept the spirit, alter the letter. Describe what you changed.
- **NITPICKS** — do not triage individually. Address them collectively in the final file or reject them.

Self-discipline: the instinct to defend your own draft is real. If Codex is right, admit it. If Codex hallucinates an API, a path, or a command that does not exist in the repo — call it out in the triage and reject.

### Step 4 — Artefacts

Produce two files under `claude_work/<task_name>/`.

**A) `implementation_plan.md`**

Take Plan v1, apply every ACCEPT and MODIFY, leave rejected items out. Use the Plan v1 structure (Goal, Files, Order, Decisions, Edge cases, Acceptance) plus two trailing sections:

```
## Changes from the first version (after review)
- <what changed and why, one sentence per point>

## Consciously rejected Codex suggestions
- <item>: <rationale>
```

Both trailing sections exist so a future reader can audit the decision trail without reopening the full triage.

**B) `roadmap.md`**

Lightweight progress checklist for the developer, **not** a duplicate of the plan. Derived from the *Implementation order* section of the final plan:

```
# Roadmap: <task_name>

Checklist for implementation. Developer ticks boxes and appends problems encountered.

## Steps

- [ ] 1. <one-line description, consistent numbering with implementation_plan.md>
- [ ] 2. ...
- [ ] N. ...

## Issues encountered

<developer fills in during implementation>

## Notes / deviations

<developer records conscious deviations from the plan and why>
```

Roadmap steps must be one-liners and **1:1 numerically consistent** with *Implementation order* in `implementation_plan.md`. Full detail lives in the plan; the roadmap is a progress indicator. If the developer later diverges from the numbered order, that is a note they record themselves — the artefact at planning time stays numerically faithful.

## Global rules

- **You do not write code.** Signatures are fine; actual implementation is the next task.
- **Every path must exist** in the repo, or be marked `NEW`.
- **If you do not know — read the file.** Do not guess APIs, commands, flags, or column names.
- **Checkpoint after every step** (1–2 sentences in chat) before moving on. Silence between tool calls is a failure mode.
- **Codex hallucinations** (invented APIs, non-existent paths, commands that do not match the repo) → flag in triage and reject.
- **LOCKED decisions are sacred.** Neither you nor Codex touch them — only realise them.
- **Language of artefacts:** match the language of `prompts.md` and the project (default: user's working language). Language of triage and reasoning: same.

## Research contradictions

Research briefs are written by humans under time pressure and occasionally contain internal contradictions (e.g. "real-time SSE progress" + "HTTP 422 on validation failure" — incompatible without buffering). Handle them explicitly:

1. Identify the contradiction in the plan under its own sub-heading ("Interpretation of the research: X vs Y").
2. State the two sides of the conflict.
3. Pick one. Justify why (prefer the business goal over the non-functional requirement when they collide).
4. Describe the alternative as a pivot path in case the user rejects the interpretation.

Do not silently pick one side. Do not ask the user mid-plan — the plan is the artefact where the question gets answered.

## Exit criteria

You are done when:

1. `claude_work/<task_name>/implementation_plan.md` exists and covers every point of *What the plan MUST contain*.
2. `claude_work/<task_name>/roadmap.md` exists with 1:1 step numbering against the plan.
3. Every Codex blocker has a triage decision and, if accepted/modified, is reflected in the plan.
4. Every rejected Codex suggestion has a one-line rationale in the plan's "Consciously rejected" section.
5. No path in the plan points to a non-existent file without a `NEW` marker.
6. No code has been written in the repo (only the two plan files).

## Tooling notes

- `codex` — the adversarial reviewer CLI (`codex exec "..."`). Requires the CLI to be installed and configured; if absent, the skill cannot run and you must surface that to the user.
- Keep the Codex prompt assembly deterministic: compose it in a temp file to avoid shell-quoting surprises with long markdown bodies.
- Default Codex timeout: set `timeout` to 600000 ms (10 minutes) in the Bash invocation. A short timeout will cut the review mid-reasoning.
- Reading the whole `prompts.md` plus all reference files is the most expensive step in tokens. It is also the step most responsible for plan quality. Do not cut it.

## Anti-patterns to avoid

- Emitting the plan without the self-compliance check against *MUST contain*.
- Dropping LOCKED decisions into the *Architectural decisions* section as if they were open. They are not.
- Accepting every Codex comment to look cooperative. Triage is a real decision, not a formality.
- Rejecting every Codex comment to defend the draft. Symmetric failure.
- Writing roadmap steps that drift from the plan's numbering. The 1:1 mapping is the whole point — the roadmap is a skeleton of the plan, not a rewrite.
- Turning the plan into pseudocode. Plan documents intent and constraints; pseudocode drifts into implementation territory and competes with the developer's work later.
