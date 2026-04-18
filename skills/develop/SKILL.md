---
name: develop
description: Faithfully implement a planned task stored under claude_work/<task-name>/. The skill reads `roadmap.md` (checklist) and `implementation_plan.md` (spec) and executes the plan step by step. Trigger when the user runs `/develop <task-name>`, or asks to "develop <task>", "implement the plan for <task>", "wdróż plan <task>", "zaimplementuj task <task>". DO NOT start without both files present in the task folder.
---

# develop

You are given a task name (argument after `/develop`). Your job: faithfully execute the plan at `claude_work/<task-name>/implementation_plan.md`, driven by `claude_work/<task-name>/roadmap.md`.

## Source of truth

- `implementation_plan.md` is THE specification. Match it literally: file paths, function signatures, library choices, error codes, test scenarios, SQL shapes, env variable names. DO NOT improvise, reshape, "improve", refactor, or abstract beyond what the plan specifies.
- `roadmap.md` is the execution checklist. Steps are ordered — you work top-to-bottom.
- If the two disagree, the plan wins. Surface the conflict to the user and pause.

## Preconditions (check before anything else)

1. Resolve `TASK_DIR = claude_work/<task-name>/` from the user's argument.
2. Verify both files exist:
   - `TASK_DIR/roadmap.md`
   - `TASK_DIR/implementation_plan.md`
3. If either is missing, STOP and tell the user. Do not guess the path or pick a similarly-named task.

## Phase 1 — Read everything first

Read both files in full before writing a single line of code. Also scan:
- The repo root (what already exists, so you know what you're adding vs. modifying).
- Any files the plan's "Files to change / create" section touches, to understand the current state.

Do not start implementing during reading.

## Phase 2 — Clarification (mandatory before any change)

Ask the user the following questions in one message, as a single list. Wait for answers before writing anything.

1. **Command execution.** The plan likely requires running commands (package installers, DB migrations, docker compose, background servers, curl smoke tests). For each category of command, should you execute it yourself, or leave it to the user to run manually?
2. **External stubs / unfinished upstream dependencies.** Scan the plan for "if X is not yet ready, return 501 / skip / placeholder" patterns (e.g., auth not wired, feature flag missing, follow-up task blocker). Confirm the exact behavior the user wants for each.
3. **Snapshot / golden-file tests.** If the plan uses snapshot-style tests whose first run creates snapshots and intentionally fails, confirm the flow: first run writes snapshots → user verifies → subsequent runs compare.
4. **Commits.** Confirm whether the user wants commits per block, one commit at the end, or no commits at all (they'll commit themselves).
5. **Live / paid / network-dependent tests.** Anything marked `@live`, optional, or requiring API keys — confirm skip or run.

Do not batch assumptions. Do not proceed with defaults. Wait for explicit answers.

## Phase 3 — Task tracking setup

Group the roadmap steps into logical blocks (usually matching the plan's own section headings — A, B, C, ...). Create one task per block using `TaskCreate`, not one per roadmap step. A plan with 32 steps typically maps to 8–12 meaningful blocks; per-step tasks are noise.

For each block:
- `subject`: short block name, e.g. "A. Schema + migration".
- `description`: which roadmap step numbers this block covers.
- Set `in_progress` when the block starts.
- Set `completed` only when the block's checks and gates pass.

## Phase 4 — Execution loop

For each step in `roadmap.md`, top-to-bottom:

1. Read the corresponding section of `implementation_plan.md` (steps usually map 1:1 by number/letter).
2. Read any files the step depends on (neighbouring modules, existing schemas, sample data).
3. Apply the change exactly as the plan specifies. No extra features, no "while I'm here" cleanups, no new files that aren't in the plan's file list, no alternative library choices.
4. Run the step's **Check** — the plan almost always specifies one (typecheck, unit test, a curl call, migration smoke, SQL verification).
5. If the check passes: mark the step `[x]` in `roadmap.md` and update the block's task progress.
6. If the check fails: diagnose the root cause. Do not retry in a loop. If the cause is your change, fix it. If the cause is a plan ambiguity, STOP and ask.

After every major block (not every step), run the plan's full acceptance gates — typically linter, type checker, test runner, build. Fix everything before moving to the next block.

## Phase 5 — Issue handling

When you hit a real obstacle (not a simple typo):

- **Fix locally if you can**, AND document it under `## Issues encountered` in `roadmap.md` in the format:
  `- **Step N (thing):** what happened, why, what you did.`
- **Outside your permissions** (files you can't read, networks you can't reach, missing env files the sandbox blocks) — STOP writing that part, document in `## Issues encountered` with the exact manual action the user needs to take, and list it in your final summary.
- **Plan ambiguity** — STOP, ask the user, do not pick a side silently.

## Phase 6 — Deviations

Any action you took that the plan does NOT literally specify — especially workarounds for platform / framework / typing quirks — belongs in `## Notes / deviations` in `roadmap.md`, with a one-line "why".

Examples that count as deviations:
- Returning HTTP 422 where the plan said 400 because the framework's body validation fires first.
- Using `# type: ignore[...]` to satisfy the type checker around a third-party SDK.
- Leaving any `TODO:` marker in the code.
- Substituting a library version because the exact one specified wasn't available.
- Back-to-back status events because the plan's fused implementation unit couldn't be split.

Deviations are acceptable. Silent deviations are not.

## Phase 7 — Review integration (if the user returns with review findings)

When the user presents review output from another agent (code review, security review, second-opinion audit):

1. Build a verdict table. For each finding: id, verdict (valid / reject), one-line rationale.
2. For valid findings — implement immediately. Do not debate.
3. For rejected findings — state the reason briefly: plan conflict, framework constraint, reviewer missing context, harmless by reviewer's own admission.
4. Run the full acceptance gates again.
5. Append `## Review fixes` section to `roadmap.md` listing what changed and what was rejected, with reasons.
6. Smaller follow-ups (addendum from the same review round) can be nested under the original finding as `(addendum)` rather than creating a new section.

## Phase 8 — Final summary

When the roadmap is fully `[x]`:
- Print: gates passing, test count, files touched.
- List any items requiring **manual user action** (env files you couldn't edit, auth integrations deferred, external migrations, etc.).
- List deviations the user should be aware of before merging.
- DO NOT commit unless the user confirmed commits in Phase 2.

## Never improvise

- No extra features, abstractions, refactors.
- No new files outside the plan's file list.
- No alternative library choices.
- No code comments beyond what the plan explicitly asks for.
- If the plan says 32 steps, you execute 32 steps — no merging, no splitting.

## Guiding principles

- The plan is truth. Deviations are documented, never hidden.
- The roadmap is a live counter. Check items off as you complete them, not at the end.
- Issues are a log. Nothing gets swept under the rug.
- Questions cost minutes. Wrong assumptions cost hours.
- Verify, don't trust — run the gate, read the output, don't assume green.

## Language

Respond in the user's language. Keep code, identifiers, commit messages, and roadmap markers in English regardless of conversation language, for consistency with existing repo content.
