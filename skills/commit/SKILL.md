---
name: commit
description: Analyze uncommitted changes and commit them with a concise, scope-generalized message. Use when the user asks to "commit", "zacommituj", "przygotuj commita", or wants changes committed.
---

# Instructions

Invoking this skill is an explicit instruction to commit. Do not ask for confirmation — gather context, draft the message, stage the relevant files, and run the commit.

## 1. Gather context

Run in parallel:
- `git status` (never with `-uall`)
- `git diff` for modified files
- `git log --oneline -10` to match repo conventions

For any untracked files that are not lockfiles, inspect them with `Read` or `Glob` to understand what was added. Skip reading lockfiles (`package-lock.json`, `poetry.lock`, `yarn.lock`, etc.) — trust the dependency declarations in `package.json` / `pyproject.toml` instead.

Do not read files inside directories that may be permission-denied without attempting via `Glob` / `Read` first; if blocked, continue with the information you have.

## 2. Analyze scope

Group changes into logical scopes (e.g. "ORM integration", "tooling", "infra config"). Determine whether the commit covers:
- **One scope** → write a single-sentence message.
- **Two or three scopes** → one sentence per scope, up to 3 sentences total.

Never enumerate files, sub-changes, or bullet lists in the message body.

## 3. Draft the message

Rules (non-negotiable):
- **No attribution trailers.** Do not append `Co-Authored-By`, `Generated with`, tool names, or any authorship line. Author identity is irrelevant.
- **Max 3 sentences** in the body. Generalize when the scope is narrow — prefer a higher-level summary over a detailed breakdown.
- **Subject line**: imperative mood, under ~70 characters, no trailing period.
- **Blank line** between subject and body.
- Match the existing repo's commit style (tense, capitalization) observed in `git log`.
- Do NOT stage files that likely contain secrets (`.env`, `credentials.json`, etc.). If such files appear in the diff, exclude them and warn the user after the commit.

## 4. Stage and commit

Stage only the specific files involved (never `git add .` or `git add -A`) and commit via HEREDOC in a single command:

```bash
git add <explicit file list> \
  && git commit -m "$(cat <<'EOF'
Subject line

Body sentence one. Body sentence two. Body sentence three.
EOF
)"
```

After the commit, run `git status` to verify and report the resulting commit SHA plus anything intentionally excluded (submodules, secrets, unrelated WIP) in one or two sentences.

## Failure handling

- If a pre-commit hook fails, the commit did not happen. Fix the underlying issue, re-stage, and create a **new** commit. Never use `--amend` to paper over a failed hook. Never use `--no-verify`.
- If there are no changes to commit, report that and stop — do not create an empty commit.
- Do not push unless the user explicitly asks.
