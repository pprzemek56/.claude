#!/usr/bin/env python3
"""
Bash guard hook dla Claude Code (PreToolUse na Bash).
Czyta JSON na stdin. Exit 0 = allow, exit 2 = block (stderr → Claude).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print('guard: PyYAML nie jest zainstalowane (pip install pyyaml) — allow', file=sys.stderr)
    sys.exit(0)

HOOK_DIR = Path(__file__).parent
RULES_BASE = HOOK_DIR / 'guard_rules.yaml'
RULES_LOCAL = HOOK_DIR / 'guard_rules.local.yaml'
LOG_FILE = HOOK_DIR / 'guard.log'

SCRIPT_RUNNERS = re.compile(
    r'^\s*(python\d?|bash|sh|zsh|node|deno|ruby|perl)\s+'
    r'([^\s|;&<>]+\.(py|sh|js|ts|mjs|rb|pl))(\s|$)'
)


def load_rules():
    rules = {'dangerous': [], 'exceptions': []}
    for path in (RULES_BASE, RULES_LOCAL):
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
            rules['dangerous'].extend(data.get('dangerous') or [])
            rules['exceptions'].extend(data.get('exceptions') or [])
        except Exception as e:
            print(f'BLOCKED by bash_guard: błąd parsowania {path.name}: {e}', file=sys.stderr)
            sys.exit(2)
    compiled = {
        'dangerous':  [(re.compile(r['pattern']), r['reason']) for r in rules['dangerous']],
        'exceptions': [(re.compile(r['pattern']), r['reason']) for r in rules['exceptions']],
    }
    return compiled


def split_compound(cmd: str):
    """Split na sub-komendy po ; && || | $(..) `..`. Naiwny, ale wystarczy."""
    parts = re.split(r';|&&|\|\||\||\$\(|\)|`', cmd)
    return [p.strip() for p in parts if p and p.strip()]


def check_sub(sub: str, rules):
    for pat, reason in rules['exceptions']:
        if pat.search(sub):
            return False, None
    for pat, reason in rules['dangerous']:
        if pat.search(sub):
            return True, reason
    return False, None


def check_script(sub: str, cwd: Path, rules):
    m = SCRIPT_RUNNERS.match(sub)
    if not m:
        return False, None
    script_path = (cwd / m.group(2)).resolve()
    # nie czytaj poza projektem ani gigantycznych plików
    try:
        if not str(script_path).startswith(str(cwd.resolve())):
            return False, None
        if not script_path.exists() or script_path.stat().st_size > 1_000_000:
            return False, None
        content = script_path.read_text(errors='ignore')
    except Exception:
        return False, None
    for pat, reason in rules['dangerous']:
        if pat.search(content):
            return True, f'skrypt {script_path.name}: {reason}'
    return False, None


def log(action: str, reason: str, cmd: str, cwd: str):
    try:
        entry = {
            'ts': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'action': action,
            'reason': reason,
            'cmd': cmd,
            'cwd': cwd,
        }
        with LOG_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass  # logging nie może nigdy zablokować hooka


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = (payload.get('tool_input') or {}).get('command', '')
    cwd = Path(payload.get('cwd', '.'))
    if not cmd.strip():
        sys.exit(0)

    rules = load_rules()

    for sub in split_compound(cmd):
        for check in (check_sub, check_script):
            if check is check_sub:
                blocked, reason = check(sub, rules)
            else:
                blocked, reason = check(sub, cwd, rules)
            if blocked:
                log('BLOCK', reason, cmd, str(cwd))
                print(f'BLOCKED by bash_guard: {reason}\nkomenda: {sub}', file=sys.stderr)
                sys.exit(2)

    # opcjonalne logowanie allow-ów przez env var
    import os
    if os.environ.get('CLAUDE_GUARD_LOG_ALL') == '1':
        log('ALLOW', '', cmd, str(cwd))
    sys.exit(0)


if __name__ == '__main__':
    main()