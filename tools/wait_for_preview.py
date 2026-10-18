#!/usr/bin/env python3
"""CI-only: obtain this commit's immutable preview from Cloudflare's GitHub check.

Read-only GitHub access. Never accept arbitrary input URLs or fall back to the
production/branch alias, which might serve a different commit.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import time


def main():
    repo, commit = os.environ['GITHUB_REPOSITORY'], os.environ['PREVIEW_COMMIT']
    if repo != 'sogyaalma/al-qaeed' or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise SystemExit('Unexpected repository or commit')
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        result = subprocess.run(['gh', 'api', f'repos/{repo}/commits/{commit}/check-runs?per_page=100'],
                                check=True, capture_output=True, text=True)
        checks = [c for c in json.loads(result.stdout)['check_runs']
                  if c['name'] == 'Cloudflare Pages' and c['app']['id'] == 85455
                  and c['head_sha'] == commit]
        if checks:
            check = max(checks, key=lambda c: c['id'])
            if check['status'] == 'completed':
                if check['conclusion'] != 'success':
                    raise SystemExit('Cloudflare preview failed: ' + str(check['conclusion']))
                match = re.search(r'https://[0-9a-f]{8}\.al-qaeed\.pages\.dev', check['output']['summary'] or '')
                if not match:
                    raise SystemExit('Cloudflare check succeeded but supplied no immutable preview URL')
                url = match.group()
                Path('test-results').mkdir(exist_ok=True)
                Path('test-results/cloudflare-check.json').write_text(json.dumps({
                    'commit': commit, 'check_id': check['id'], 'url': url,
                    'conclusion': check['conclusion'],
                }, indent=2) + '\n')
                with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                    output.write('url=' + url + '\n')
                print('Cloudflare immutable preview: ' + url)
                return
        time.sleep(10)
    raise SystemExit('Cloudflare preview did not finish within ten minutes; no production fallback')


if __name__ == '__main__':
    main()
