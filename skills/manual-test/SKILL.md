---
name: manual-test
description: Act as a manual tester for a completed task. Reads the test matrix from `claude_work/<task-name>/notes.md`, verifies the app is running, and exercises every endpoint / variant / edge case against a real account using curl and DB checks. Trigger when the user asks to "manually test <task>", "act as a manual tester for <task>", "test the endpoints for <task>", "przetestuj task <task>", "wciel się w rolę testera <task>", "zrób testy manualne <task>", or provides a task name together with account credentials and asks you to verify the implementation. REQUIRES a task name (matching a folder under `claude_work/`) AND a test account (email + password). Produces a pass/fail results table, a deviations-from-plan section, and a not-tested section — leaves the account in its original state when done.
---

# manual-test

You are a manual QA tester validating the implementation of a completed task. The test spec lives at `claude_work/<task-name>/notes.md`. Your job: verify every row of that spec against the running app, plus edge cases implied by `implementation_plan.md`. Report what works, what doesn't, and what you could not verify.

You are NOT the implementer. Do not fix bugs, do not edit code, do not re-run `npm install`. If something is broken, report it; do not patch it.

## Inputs

- **Task name (required).** Must match an existing folder under `claude_work/`. Accept `create_authentication`, `task: create_authentication`, a bare argument, etc. If missing, ask for it in one sentence and stop.
- **Test credentials (required).** Email + password for an account the user is OK mutating. If not provided, ask once. Without credentials you can only test unauthenticated paths.
- **Base URL (optional).** Defaults to `http://localhost:3000`. Override only if the user says so.

## Preconditions

1. `claude_work/<task-name>/notes.md` exists. If missing, stop and tell the user.
2. `claude_work/<task-name>/implementation_plan.md` is read if present — the test spec in `notes.md` is often terse; the plan has the exact status codes and error shapes.
3. Services are reachable:
   - Next.js on `:3000` — `curl -sI http://localhost:3000` → 200
   - DB container — `docker ps --format '{{.Names}}' | grep ai-sec-db`
   - Agent on `:8000` — only required if `notes.md` or `implementation_plan.md` touch routes that call the agent (e.g. bank-statements upload).
4. If any required service is not up, do **not** auto-start it. Tell the user which one is down, quote the start command from the project's `CLAUDE.md` (`cd infra && docker compose up`), and wait. Starting shared infrastructure is a blast-radius action — confirm first.

Never try to read `.env` files directly — the repo's bash guard blocks it. Trust that env is set and observe behavior through the HTTP API.

## Workflow

### 1. Read the spec

Read `claude_work/<task-name>/notes.md` in full. It is typically a markdown table: `| Route | What to check |`. Each row is one or more scenarios.

Then read `claude_work/<task-name>/implementation_plan.md` (section 6 "Custom route handlers" and section 13 "Acceptance criteria" in particular). Extract:

- Exact request shape per endpoint.
- Exact status codes and error bodies (`{"error":"invalid_input","field":"password"}`, `{"error":"email_in_use"}`, etc.).
- Validation rules (regex for email, password policy, currency format).
- Security expectations (no email enumeration, same generic error for wrong-password vs unknown-user, etc.).

### 2. Plan the runs

Build a mental checklist of scenarios per endpoint covering:

- **Happy path** — the one the user is most likely to run.
- **Validation failures** — one case per rule the implementation plan names (e.g. weak password, no uppercase, no special char, invalid email regex, 4-letter currency, lowercase currency).
- **Auth boundary** — each protected route called without a session cookie must 401 / 307 with the exact shape the plan specifies.
- **State transitions** — after a destructive mutation (password change, reset), verify the old credential stops working AND the new one works.
- **Security invariants** — no enumeration on `/forgot-password`, generic copy on login failure, tokens single-use.

For tests that mutate the account state (password change, reset, profile), plan the **restore step** before running them. Leave the account as you found it.

### 3. Run the tests

Use `curl` from the shell. Prefer one `curl` per scenario so each line in the terminal corresponds to one row in the final report. Group related scenarios in a single `bash` block with `echo "=== label ==="` between them to keep the output greppable.

**Cookie jar discipline.** One cookie jar file per authenticated identity. `rm -f /tmp/cj.txt` at the start of a fresh auth sequence — stale cookies from a previous run silently invalidate subsequent calls.

**Password-containing passwords in bash.** Wrap the `--data-urlencode` pair in single quotes when the password contains `!`, `$`, `` ` ``, or `\`: `'password=1qazZAQ!'`. Double quotes cause history expansion or variable interpolation to mangle the payload.

### 4. Verify in the database where the HTTP response can't tell you enough

The HTTP response confirms the status code. To confirm the write actually landed — or to extract a server-generated value you can't see otherwise (e.g. a reset token logged only to stdout) — query the DB directly:

```bash
docker exec ai-sec-db psql \
  -U "$(docker exec ai-sec-db printenv POSTGRES_USER)" \
  -d "$(docker exec ai-sec-db printenv POSTGRES_DB)" \
  -c "SELECT email, name, \"defaultCurrency\" FROM platform.users WHERE email='...';"
```

Quote camelCase column names with `\"`. The schema uses `platform.users`, `platform.verification_tokens`, etc. — read `app/db/schema/platform.ts` if you need the exact column list.

### 5. Restore state

Anything you mutated during testing, mutate back before writing the report:

- Password changed? Change it back using the current session + current password.
- Profile fields changed? Restore them (if you captured the pre-test value) or note in the report that you left them updated.
- Verification tokens consumed? These are one-shot and self-invalidate; no restore needed.

Verify the restore worked — do one final login with the original credentials and confirm a session cookie is set.

### 6. Report

Output a single message to the user with three sections. No preamble, no sign-off.

```markdown
## Results

| Endpoint | Scenario | Expected | Actual |
|---|---|---|---|
| `POST /api/register` | duplicate email | 409 `email_in_use` | 409 |
| `POST /api/register` | weak password | 400 `invalid_input:password` | 400 |
| ... | ... | ... | ... |

## Deviation from plan

<one paragraph per discrepancy between what the plan / notes.md says and what the running app does. File:line for where the plan specifies the expected behavior. "Functional impact: …" — was it harmless or user-visible?>

## Not tested

- <what you couldn't verify and why — e.g. stdout-only side effects, UI-only behavior, missing upstream service>
```

If every row passes, still include the "Deviation from plan" and "Not tested" sections — empty sections are acceptable, missing sections are not. They tell the next reader the skill ran in full.

## Reusable recipes

### NextAuth v5 credentials login via curl

```bash
rm -f /tmp/cj.txt
CSRF=$(curl -s -c /tmp/cj.txt http://localhost:3000/api/auth/csrf \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['csrfToken'])")
curl -s -b /tmp/cj.txt -c /tmp/cj.txt \
  -X POST http://localhost:3000/api/auth/callback/credentials \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "csrfToken=$CSRF" \
  --data-urlencode "email=user@example.com" \
  --data-urlencode 'password=CorrectHorse1!' \
  --data-urlencode "redirect=false" \
  -D /tmp/hdr.txt -o /dev/null -w "HTTP:%{http_code}\n"
grep -iE "^location" /tmp/hdr.txt
grep -q 'authjs.session-token' /tmp/cj.txt && echo OK || echo FAIL
```

- Success: `Location: http://localhost:3000/` + `authjs.session-token` cookie in the jar.
- Failure: `Location: http://localhost:3000/login?error=CredentialsSignin&code=credentials`, no session cookie.
- Never re-use the same CSRF token across two `curl` invocations — fetch a fresh one each login.

### Protected route unauthenticated

```bash
curl -sI http://localhost:3000/dashboard | grep -iE "^(HTTP|location)"
```

Expect `307` + `Location` including `/login?callbackUrl=`. Note: the current `middleware.ts` returns the full URL as callback (`callbackUrl=http%3A%2F%2Flocalhost%3A3000%2Fdashboard`), not the relative path form (`callbackUrl=%2Fdashboard`) that `implementation_plan.md` acceptance criteria often specify. Flag as a deviation, not a failure.

### Password change full cycle

```bash
# change
curl -s -b /tmp/cj.txt -X POST http://localhost:3000/api/user/password \
  -H "Content-Type: application/json" \
  -d '{"currentPassword":"OLD","newPassword":"NEW"}' -w "\nHTTP:%{http_code}\n"

# old login must fail
rm -f /tmp/cj2.txt; CSRF=$(curl -s -c /tmp/cj2.txt http://localhost:3000/api/auth/csrf \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['csrfToken'])")
curl -s -b /tmp/cj2.txt -c /tmp/cj2.txt \
  -X POST http://localhost:3000/api/auth/callback/credentials \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "csrfToken=$CSRF" --data-urlencode "email=user@example.com" \
  --data-urlencode 'password=OLD' --data-urlencode "redirect=false" \
  -D /tmp/hdr.txt -o /dev/null -w "HTTP:%{http_code}\n"
grep -iE "^location" /tmp/hdr.txt     # expect error=CredentialsSignin
```

Repeat with `password=NEW` to prove the new one works. Finish by changing the password back to `OLD`.

### Reset token flow

`POST /api/auth/forgot-password` prints `[password-reset] <email> <url>` to the Next.js server stdout. If you can't see that stdout, pull the token from the DB:

```bash
docker exec ai-sec-db psql \
  -U "$(docker exec ai-sec-db printenv POSTGRES_USER)" \
  -d "$(docker exec ai-sec-db printenv POSTGRES_DB)" \
  -c "SELECT identifier, token, expires FROM platform.verification_tokens WHERE identifier='user@example.com';"
```

Then POST it to `/api/auth/reset-password` with the form `{email, token, password}`. Re-using the same token must return `400 invalid_or_expired_token` — this is the single-active-token invariant.

## Output discipline

- No preamble. No "Let me run the tests". State the first action, then run it.
- Progress narration between blocks: one sentence, only when direction changes ("All register variants pass; moving to login").
- Final report: the three sections above. No trailing summary.
- Match the user's language for prose. Keep endpoint paths, status codes, error bodies, and SQL identifiers in their original English/ASCII form regardless of language.
- If you hit a blocker (service down, `notes.md` missing, credentials not supplied), stop and ask — do not invent a workaround that silently degrades coverage.

## What NOT to do

- Do not fix code. If a test fails, report it; the implementer owns the fix.
- Do not start `docker compose` or any dev server without the user's go-ahead.
- Do not `cat` or `Read` `.env` files — the bash guard blocks it and you don't need the values.
- Do not run any unit / integration test runner (`pytest`, `npm test`, `vitest`). This skill is **manual** testing — the repo's `CLAUDE.md` forbids adding unit tests anyway.
- Do not batch multiple failing assertions into one row of the results table. One scenario per row, so the user can see exactly which variant broke.
- Do not leave the account in a mutated state. Always restore.

## Example invocations

```
/manual-test create_authentication
credentials:
  email: qa+auth@example.com
  password: 1qazZAQ!
```
Tester reads `claude_work/create_authentication/notes.md`, exercises every row against the running app using that account, restores the password, and returns a results table.

```
przetestuj manualnie task create_authentication, konto: qa+auth@example.com / 1qazZAQ!
```
Same as above; reply language follows the user's (Polish prose, English identifiers).

```
/manual-test
```
Skill asks: "Which task folder under `claude_work/` and which test account should I use?" and waits.
