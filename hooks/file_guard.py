#!/usr/bin/env python3
"""File guard hook — blokuje Read/Edit/Write na wrażliwych ścieżkach."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print('file_guard: brak PyYAML → allow', file=sys.stderr)
    sys.exit(0)

HOOK_DIR = Path(__file__).parent
RULES_BASE = HOOK_DIR / 'sensitive_paths.yaml'
RULES_LOCAL = HOOK_DIR / 'sensitive_paths.local.yaml'
LOG_FILE = HOOK_DIR / 'guard.log'


def load_rules():
    deny, allow = [], []
    for path in (RULES_BASE, RULES_LOCAL):
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
            deny.extend(data.get('deny') or [])
            allow.extend(data.get('allow') or [])
        except Exception as e:
            print(f'BLOCKED by file_guard: błąd parsowania {path.name}: {e}', file=sys.stderr)
            sys.exit(2)
    try:
        return (
            [(re.compile(r['pattern']), r['reason']) for r in deny],
            [(re.compile(r['pattern']), r['reason']) for r in allow],
        )
    except (re.error, KeyError, TypeError) as e:
        print(f'BLOCKED by file_guard: błędna reguła: {e}', file=sys.stderr)
        sys.exit(2)

def log(action, reason, tool, path):
    try:
        entry = {
            'ts': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'hook': 'file_guard',
            'action': action,
            'tool': tool,
            'reason': reason,
            'path': path,
        }
        with LOG_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = payload.get('tool_name', '')
    ti = payload.get('tool_input') or {}
    file_path = ti.get('file_path') or ti.get('path') or ''
    if not file_path:
        sys.exit(0)

    deny, allow = load_rules()

    # wyjątek wygrywa z deny
    for pat, _ in allow:
        if pat.search(file_path):
            sys.exit(0)

    for pat, reason in deny:
        if pat.search(file_path):
            log('BLOCK', reason, tool, file_path)
            print(f'BLOCKED by file_guard: {reason}\nplik: {file_path}', file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()