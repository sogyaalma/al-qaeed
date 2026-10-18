#!/usr/bin/env python3
"""Redacted, offline high-confidence pattern scan; not a complete secret detector.

Use --history to scan all locally reachable Git blobs as well as tracked files.
Never prints matching values or file contents. Public email addresses aren't secrets.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = [
    ('private key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('GitHub token', re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b')),
    ('AWS access key', re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('Slack token', re.compile(rb'\bxox[baprs]-[0-9]{10,}-[A-Za-z0-9-]{20,}\b')),
    ('Google API key', re.compile(rb'\bAIza[0-9A-Za-z_-]{35}\b')),
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    entries = []
    for name in git('ls-files', '-z').decode().split('\0'):
        if name and (ROOT / name).is_file():
            entries.append((name, (ROOT / name).read_bytes()))
    if args.history:
        objects = git('rev-list', '--objects', '--all').decode().splitlines()
        for entry in objects:
            oid, _, name = entry.partition(' ')
            if name and git('cat-file', '-t', oid).strip() == b'blob':
                entries.append((f'history:{oid[:12]}:{name}', git('cat-file', 'blob', oid)))
    findings = 0
    for name, data in entries:
        for label, pattern in PATTERNS:
            match = pattern.search(data)
            if match:
                findings += 1
                line = data[:match.start()].count(b'\n') + 1
                print(f'FAIL {label}: {name}:{line} [REDACTED]')
    print(f'Scanned {len(entries)} file/blob entries with {len(PATTERNS)} high-confidence patterns; {findings} findings')
    return bool(findings)


if __name__ == '__main__':
    sys.exit(main())
