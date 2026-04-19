---
name: single-planning
description: Produce an implementation plan for a small, trivial, or narrowly scoped task without the adversarial review round. Use when the user asks to "plan task X", "write implementation plan for <task>", "single-planning <task>", "zrób plan do <task>", or provides a research brief in claude_work/<task>/prompts.md for a small change (feature flag, config tweak, small bug fix, single-file refactor). Produces two artefacts — implementation_plan.md (full plan) and roadmap.md (1:1 numbered checklist) — directly from reconnaissance, with no Codex review. You are the planner, not the developer. Do not write code. Do not implement without a plan file.
---

# single-planning

Produce an implementation plan for a small or trivial task. The output is two files: a full `implementation_plan.md` that a developer can follow 1:1 and a lightweight `roadmap.md` they use as a progress checklist.

This skill is the lightweight counterpart to `double-planning`. It skips the adversarial Codex review round — that overhead is not worth paying for narrowly scoped work.

## When to use

- User has a research/brief file at `claude_work/<task_name>/prompts.md` and wants a planning pass on a small task.
- Task has narrow scope: a feature flag, a single-file refactor, a config tweak, a small bug fix, adding a dev-only mode, wiring one env var through.
- User explicitly says "single-planning", "quick plan", "light plan", or signals they do not want Codex review ("don't run codex", "skip review", "trivial").
- A task name is provided or can be inferred (`ls -t claude_work/ | head -1`).

## When NOT to use

- User wants implementation, not planning — use the `develop` skill.
- Task is architecturally risky, crosses many packages, or involves non-trivial trade-offs — use `double-planning` so the plan gets a second opinion.
- No `prompts.md` exists for the task — ask the user to run `research` first.
- User explicitly asks for Codex review or adversarial review — use `double-planning`.

## Heuristic: single vs double

| Signal | Prefer single-planning | Prefer double-planning |
|---|---|---|
| Files touched | < 10 | ≥ 10 |
| Packages touched | 1 | ≥ 2 |
| New architectural decisions | 0–2 | 3+ |
| LOCKED decisions with subtle interpretation | no | yes |
| Research contradictions inside `prompts.md` | no | yes |
| User said "trivial", "small", "quick" | yes | — |
| User said "rigorous", "with review", "double-check" | — | yes |

If unsure, ask the user before defaulting to the heavyweight path.

## Inputs

- `claude_work/<task_name>/prompts.md` — the research brief. Typical sections (same as double-planning):
  - **Business goal** — the product-level "why".
  - **Design decisions (LOCKED / AGREED / do not challenge)** — sacred. Implement faithfully.
  - **What the plan MUST contain** — compliance checklist the plan is scored against.
  - **What the plan MUST NOT contain** — anti-scope.
  - **Key reference files** — concrete paths to read before planning.

Treat every section literally. LOCKED decisions are not open for negotiation.

## Workflow

Three steps. Do not skip and do not reorder.

### Step 0 — Reconnaissance

Goal: understand the task before writing anything.

1. Read `claude_work/<task_name>/prompts.md` **in full**. Pay attention to the five sections above.
2. Read **every** file listed in *Key reference files*. If the section is missing, identify 5–10 files that matter (entrypoints, schemas, existing tests, any archived plan in `claude_work/archive/` for style reference) and read them.
3. Run targeted `Grep` calls when the plan depends on patterns that are not obvious from a single file — for example: "is there already a `logging.basicConfig` anywhere?", "which test file uses `monkeypatch` this way?". Do not grep the whole repo; target the question.
4. If any referenced file is permission-blocked, surface that to the user in the checkpoint but continue if the brief gives enough context to plan around it.
5. **Checkpoint in chat:** 2–3 sentences summarising the task + a list of files you read + any grep findings worth flagging. This is a visible commitment that you grounded yourself before planning.

Rule: if you do not know something, read the file. Do not guess paths, commands, or APIs.

### Step 1 — Plan draft

Emit the plan directly in chat under the heading `## PLAN` (no versioning — there is only one pass). Use this structure:

1. **Goal and scope** — what we are building, and what is explicitly out of scope (mirror the research's anti-scope).
2. **Files to change / create** — table with absolute or repo-relative paths, change type (EDIT / NEW), one sentence describing the change.
3. **Implementation order** — numbered steps. Each step independently testable (after completing it, a `check` command must exist that proves the step landed without the next step being done). Include the check command inline per step.
4. **Architectural decisions** — only for points not rostrzygnięte in `prompts.md`. Format: choice + at least one rejected alternative + rationale. For LOCKED decisions from `prompts.md`, **do not replay the debate**; state only how the plan realises them, if that is not obvious.
5. **Pseudocode** — exact code snippets for the edits (signatures, class shells, full function bodies for tricky spots). Enough for the developer to implement 1:1 without re-deriving anything.
6. **Test plan** — which new tests, which file, which scenarios, mapped to the research's test requirements. Include the exact test skeleton (imports, fixture wiring, one test body) when the style is non-obvious.
7. **Edge cases and traps** — concrete risks grounded in the repo, not generic platitudes.
8. **Acceptance criteria** — reproducible, binary pass/fail. Prefer shell commands and SQL queries over prose.

Before closing Step 1, **self-verify compliance**:

- If `prompts.md` has *What the plan MUST contain*, walk the checklist point by point. For each point, cite the section of the plan that covers it. Extend the plan if anything is missing.
- If `prompts.md` has *What the plan MUST NOT contain*, check every scope element against that list. Remove anything that slipped in.

Discipline:

- **No production code.** Pseudocode for the tricky spots is fine. Full function bodies are fine when they are the artefact the developer will copy. What is NOT fine: designing abstractions not in the brief, inventing helpers, proposing refactors adjacent to the task.
- "Use X because Y", never "consider X".
- Paths verified against the actual filesystem (or marked `NEW`).
- Prefer specificity: package names with version ranges, exact commands, exact env var names.

### Step 2 — Artefacts

Produce two files under `claude_work/<task_name>/`.

**A) `implementation_plan.md`**

Full plan, same structure as the Step 1 draft. No trailing "changes from v1" section (there is no v1 — there is only one version). No "rejected reviewer suggestions" section (there is no reviewer).

The typical section layout:

```
# Implementation plan — `<task_name>`

## 1. Goal and scope
## 2. Files to change / create
## 3. Implementation order
## 4. Architectural decisions
## 5. Pseudocode
## 6. `<one or two special sections if the task needs them, e.g. env file appendix, README section>`
## 7. Test plan
## 8. `<optional: README or doc additions>`
## 9. Edge cases / traps
## 10. Acceptance criteria
## 11. Compliance check vs the brief
```

The exact numbering can flex to the shape of the task; the *required* sections are Goal, Files, Order, Pseudocode, Tests, Edge cases, Acceptance, Compliance check.

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

Roadmap steps must be one-liners and **1:1 numerically consistent** with *Implementation order* in `implementation_plan.md`. Full detail lives in the plan; the roadmap is a progress indicator.

## Global rules

- **You do not write production code.** Pseudocode in the plan is fine; touching `src/`, `app/`, or any real source file is not.
- **Every path must exist** in the repo, or be marked `NEW`.
- **If you do not know — read the file.** Do not guess APIs, commands, flags, or column names.
- **Checkpoint after Step 0** (2–3 sentences in chat) before moving on. Silence between tool calls is a failure mode.
- **LOCKED decisions are sacred.** Do not relitigate them in the *Architectural decisions* section — just realise them.
- **Language of artefacts:** match the language of `prompts.md` and the project. If the brief is in Polish, the plan is in Polish; if English, English. Language of reconnaissance checkpoint and internal reasoning: same.

## Research contradictions

Research briefs occasionally contain internal contradictions. When you spot one:

1. Identify it in the plan under its own sub-heading ("Interpretation of the research: X vs Y").
2. State the two sides of the conflict.
3. Pick one. Justify why (prefer the business goal over the non-functional requirement when they collide).
4. Describe the alternative as a pivot path in case the user rejects the interpretation.

If the contradiction is deep enough that picking one side is architecturally risky, stop and recommend upgrading to `double-planning` — that is exactly the case where the review round pays for itself.

## Exit criteria

You are done when:

1. `claude_work/<task_name>/implementation_plan.md` exists and covers every point of *What the plan MUST contain*.
2. `claude_work/<task_name>/roadmap.md` exists with 1:1 step numbering against the plan.
3. No path in the plan points to a non-existent file without a `NEW` marker.
4. No production code has been written in the repo (only the two plan files).
5. The plan contains a compliance section explicitly mapping its contents to the brief's *MUST contain* / *MUST NOT contain*.

## Anti-patterns to avoid

- Emitting the plan without the self-compliance check against *MUST contain*.
- Dropping LOCKED decisions into the *Architectural decisions* section as if they were open.
- Writing roadmap steps that drift from the plan's numbering. The 1:1 mapping is the whole point — the roadmap is a skeleton of the plan, not a rewrite.
- Turning the plan into full production code. Pseudocode is for the developer's hands; writing the final implementation here duplicates their work and rots when assumptions change.
- Inventing abstractions, helpers, or refactors not in the brief. If the brief says "add two fields and one validator", the plan adds two fields and one validator — nothing else.
- Silently skipping a *Key reference file* because it felt tangential. If it is in the brief's list, it is in scope for reading.
- Running `codex exec` or any adversarial reviewer. That is `double-planning`'s job, not this skill's.
- Defaulting to this skill for large architectural tasks. When you feel the plan growing past ~10 files or ~3 genuine trade-offs, stop and recommend `double-planning` instead.

## Relationship to `double-planning`

`single-planning` is the same shape minus the review round. Concretely:

- Reconnaissance step is identical.
- Plan structure is identical in sections; the plan just does not carry the "v1" label or the two trailing review-trail sections.
- Step 2 (Codex review) and Step 3 (Triage) from `double-planning` are removed.
- Step 4 (Artefacts) is the same, minus the "Changes from the first version" and "Consciously rejected Codex suggestions" sections — those sections have no source to draw from here.

If mid-planning the task reveals itself to be larger than expected, stop and tell the user: "this has outgrown `single-planning`; I recommend re-running as `double-planning`." Do not silently bolt a review round onto this skill.
