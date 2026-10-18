#!/usr/bin/env python3
"""Verify artifact-level reproduction, NOT compilation from the unknown NDS sources.

Reconstruct in a temporary directory from the immutable project import and the
reviewed, separately pinned icon SCSS. Do not update assets or accept new hashes.
Requires full Git history, Python only, no network, Ruby, Sass or latest release.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
IMPORT = '564c53b9307dd64b56874985f5111e5f3cbd9028'
BLANK_SOURCE_SHA = 'e5dfccc31c34f1e5752f5ddf6ac499c8cbe530cde7bc5550236d40be5394a24e'


def main():
    manifest = json.loads((ROOT / 'docs/nds-assets.json').read_text())
    if manifest['inherited_from_project_commit'] != IMPORT:
        raise SystemExit('Import pin changed: review the reproduction recipe')
    blank = (ROOT / 'tools/vendor/_fonts-hgi-blank.scss').read_bytes()
    if hashlib.sha256(blank).hexdigest() != BLANK_SOURCE_SHA:
        raise SystemExit('Unreviewed blank-font source')
    with tempfile.TemporaryDirectory(prefix='nds-reproduce-') as directory:
        scratch = Path(directory)
        generated = {'assets/fonts/hgi-blank.woff2', 'assets/css/hgi-rounded-stroke-min.css'}
        for name in manifest['sha256']:
            output = scratch / name
            output.parent.mkdir(parents=True, exist_ok=True)
            if name not in generated:
                data = subprocess.run(['git', 'show', f'{IMPORT}:{name}'], cwd=ROOT,
                                      check=True, capture_output=True).stdout
                output.write_bytes(data)
        (scratch / 'assets/fonts/hgi-blank.woff2').write_bytes(
            base64.b64decode(re.search(rb'data:font/woff2;base64,([^"\s]+)', blank).group(1)))
        (scratch / 'tools').mkdir()
        for name in ['build_hgi.py', 'repair_nds_css.py']:
            shutil.copy2(ROOT / 'tools' / name, scratch / 'tools' / name)
        for name in ['index.html', 'en/index.html', '404.html', 'assets/js/site.js']:
            (scratch / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, scratch / name)
        subprocess.run([sys.executable, str(scratch / 'tools/build_hgi.py'), '--source',
                        str(ROOT / 'tools/vendor/_hgiRoundedStroke.scss')], check=True)
        subprocess.run([sys.executable, str(scratch / 'tools/repair_nds_css.py')], check=True)
        for name, digest in manifest['sha256'].items():
            if hashlib.sha256((scratch / name).read_bytes()).hexdigest() != digest:
                raise SystemExit(f'Reproduction mismatch: {name}')
        sys.path.insert(0, str(ROOT / 'tools'))
        from font_policy import BLOCKED, sanitize_css
        for name, digest in manifest['distribution_sha256'].items():
            public = sanitize_css(Path(name).name, (scratch / name).read_bytes())
            if hashlib.sha256(public).hexdigest() != digest:
                raise SystemExit(f'Distribution reproduction mismatch: {name}')
        if set(manifest['distribution_excluded_fonts']) != {'assets/fonts/' + n for n in BLOCKED}:
            raise SystemExit('Distribution exclusions differ from the reviewed policy')
    print(f"PASS reproduced {len(manifest['sha256'])} inherited/repaired artifacts and public CSS policy")
    print('Original upstream full-build commit remains UNKNOWN; no NDS runtime was upgraded.')


if __name__ == '__main__':
    main()
