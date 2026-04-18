---
name: review-codebase
description: Perform a structured senior-developer review of uncommitted changes in the current repo. Use when the user asks to "review the codebase", "review my changes", "review uncommitted work", "act as a reviewer", "zrób review", "przejrzyj kod", "sprawdź zmiany", or provides a list of files/dirs to exclude from review via @mentions. Produces a prioritized findings list (P0-P3) with file:line refs, or an OK confirmation if clean. Supports iterative re-review after fixes.
---

# Codebase review

You are a senior developer reviewing uncommitted changes. Validate logic correctness, composition, and adherence to good programming practices. Findings will be handed to the implementing agent for discussion — be specific, not generic. Do NOT invent findings to look thorough; if the code is clean, say so.

## Inputs

- **Excluded paths**: The user may pass files or directories to skip via `@mentions` or a plain list (e.g. `@roadmap.docx @.claude @claude_work/`). Strip these from scope before reading.
- **Role / language scope**: If the user specifies a role ("as a Python developer", "jako backend dev"), limit the review to that stack. Do not assume — ask once if cross-stack changes should be included.

## Workflow

### 1. Scope negotiation (one focused question, if needed)

Before reading any file, confirm:
- Language/stack scope if the user specified a role.
- Whether adjacent changes in other stacks (e.g. TS next to Python) are in scope.

Ask at most one clarifying question. If unambiguous, proceed.

### 2. Capture git state

Run `git status` and `git diff --stat`. Identify modified tracked files and untracked new files. Drop exclusions from the list. Do not rely on the user's description — read git directly.

### 3. Enumerate source files in scope

Use Glob to list source files under in-scope directories. Exclude by default:
- `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `dist/`, `build/`, `target/`
- Lockfiles (`poetry.lock`, `package-lock.json`, `pnpm-lock.yaml`) unless the user explicitly wants them reviewed.
- User-specified exclusions.

### 4. Set up task tracking

If the review spans more than ~3 files or distinct concerns, use TaskCreate to break work into layers, e.g.:
- Config / bootstrap / auth
- Transport / routes / middleware
- Domain logic / orchestration
- Persistence / external integrations
- Tests & fixtures
- Build / infra diff
- Final report

Update task status as you progress. Mark completed immediately, not in batches.

### 5. Read bottom-up, layer by layer

Read in dependency order. Batch parallel reads for files within the same layer. For each file, evaluate these axes:

**Logic & correctness**
- Does it actually do what its name/docstring claims?
- Are error paths handled (and not silently swallowed)?
- Async/sync boundaries: no blocking calls on the event loop, no forgotten `await`, no sync client inside `async def`.
- Edge cases: empty input, `None`, multi-currency, unicode, size limits, concurrency.

**Composition & architecture**
- Concerns separated?
- Abstractions at the right level (no premature generalization, no under-abstraction duplicating logic)?
- Resources reused (connection pools, HTTP clients) instead of rebuilt per request?
- Module-level side effects avoided?

**Security & inputs**
- Trusted vs untrusted inputs clearly marked?
- Upload size capped BEFORE buffering the full body?
- Secrets required (no dev defaults like `"change-me"` in production code paths)?
- Auth applied to every route that needs it?
- SQL / command / path injection vectors?

**Type safety & style**
- Do types match runtime behavior?
- `Any` / `# type: ignore` sparingly used and justified?
- Naming matches the codebase convention?

**Spec / contract consistency**
- README / API docs match the code?
- Error codes, enum members, event types used consistently across layers?
- Streaming/status events emitted in the documented order?

**Test coverage**
- Happy path AND each error path covered?
- Assertions specific — flag loose matches like `status_code in (400, 422)` that hide divergence.
- Fixtures realistic.

### 6. Run the project's own tooling

Detect the stack and run its checks as baseline:
- Python: `ruff check`, `mypy` (strict if configured), `pytest -q` (or `pytest -q --tb=short`).
- TypeScript / Node: `tsc --noEmit`, `eslint`, `pnpm test` / `npm test`.
- Go: `go vet ./...`, `go test ./...`.
- Rust: `cargo clippy -- -D warnings`, `cargo test`.

Report pass/fail status. Green tooling is a baseline, not a substitute for logic review.

### 7. Write the report

Group findings by severity. Use these tiers consistently:

- **P0** — blocking runtime/correctness: event-loop blocking, broken auth, data loss, broken public contract.
- **P1** — behavioral or spec inconsistencies: wrong error codes, out-of-order events, resource leaks, rebuilt-per-request clients.
- **P2** — data quality / defensive hardening: input validation, misleading logs/warnings, hardcoded dev defaults, brittle parsing.
- **P3** — test polish, loose assertions, minor style divergence.

For each finding include:
- One-line claim.
- File:line reference (`path/to/file.ext:42`).
- Short *why* — what breaks, under what conditions.
- Concrete fix suggestion.

Include a **Positives** section — things worth keeping so the implementer does not "fix" them.

End with a **Bottom line**: one sentence. Merge OK / block on P0-P1 / ship with follow-ups.

### 8. Iterative re-review (when the implementer reports fixes)

When the implementer sends a summary of fixes, DO NOT trust it. For each fix:
1. Read the changed file(s) end-to-end.
2. Verify the fix matches the original finding's intent, not just its surface.
3. Re-run ruff/mypy/pytest (or stack equivalents).
4. Check whether the fix introduced a new smell (UX regression, missing shutdown hook, new `type: ignore` without justification). Flag those as follow-ups, not blockers, unless severity warrants.

Produce a per-finding status table using ✅ (fixed correctly), ⚠️ (fixed with caveat), ❌ (not fixed / regressed). Then a short "remaining nits" section for follow-ups.

## Output discipline

- Lead with scope confirmation: what was read, what was skipped, tooling status.
- No filler, no "Great question", no closing summary beyond the Bottom line.
- Every code reference uses `path/to/file.ext:line`.
- If the code is genuinely clean, say so in one short paragraph. Do not manufacture findings.
- Match the user's language for prose; keep code identifiers and file paths in their original form.

## Example invocation

/review-codebase @roadmap.docx @.claude @claude_work/

Excludes the listed paths, reviews everything else uncommitted under the git status.
