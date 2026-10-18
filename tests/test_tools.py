"""Isolated build/packaging regression tests; never mutate the working tree."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ['tools', 'content']:
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__', 'fonts-original'))
        for name in ['_headers', 'vercel.json', 'robots.txt']:
            shutil.copy2(ROOT / name, self.root / name)
        # Tiny fixture; packaging must not depend on undocumented repository files.
        (self.root / 'assets/docs').mkdir(parents=True)
        (self.root / 'assets/docs/cv.pdf').write_bytes(b'%PDF-fixture')

    def run_tool(self, name, success=True):
        result = subprocess.run([sys.executable, str(self.root / 'tools' / name)], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stderr + result.stdout)
        return result

    def content(self, mutate):
        path = self.root / 'content/content.json'
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False))

    def test_build_is_deterministic(self):
        self.run_tool('build.py')
        names = ['index.html','en/index.html','404.html','sitemap.xml','_headers','vercel.json']
        before = {n: (self.root / n).read_bytes() for n in names}
        self.run_tool('build.py')
        self.assertEqual(before, {n: (self.root / n).read_bytes() for n in names})

    def test_json_script_cannot_be_closed_by_content(self):
        payload = '</script><script>alert(1)</script>&'
        self.content(lambda d: d['person']['name_full'].update(ar=payload))
        self.run_tool('build.py')
        text = (self.root / 'index.html').read_text()
        self.assertNotIn(payload, text)
        self.assertIn('\\u003c/script\\u003e', text)

    def test_build_rejects_stale_counts(self):
        self.content(lambda d: d['nav'][0]['meta'].update(en='99 focus areas'))
        self.assertIn('stale', self.run_tool('build.py', False).stderr)

    def test_build_rejects_unsafe_site_url(self):
        self.content(lambda d: d['site'].update(url='javascript:alert(1)'))
        self.run_tool('build.py', False)

    def test_build_rejects_cv_traversal(self):
        self.content(lambda d: d['site'].update(cv_file='../private.pdf'))
        self.run_tool('build.py', False)

    def test_package_excludes_source_and_matches_html(self):
        self.run_tool('build.py')
        self.run_tool('package.py')
        self.assertFalse((self.root / 'dist/content').exists())
        self.assertFalse((self.root / 'dist/tools').exists())
        self.assertEqual((self.root / 'index.html').read_bytes(), (self.root / 'dist/index.html').read_bytes())

    def test_missing_input_preserves_existing_package(self):
        self.run_tool('build.py')
        self.run_tool('package.py')
        before = (self.root / 'dist/index.html').read_bytes()
        (self.root / '404.html').unlink()
        self.run_tool('package.py', False)
        self.assertEqual(before, (self.root / 'dist/index.html').read_bytes())

    def test_asset_symlink_does_not_leak_or_replace_previous_output(self):
        self.run_tool('build.py')
        self.run_tool('package.py')
        before = (self.root / 'dist/index.html').read_bytes()
        (self.root / 'assets/leak.txt').symlink_to(self.root / 'content/content.json')
        self.run_tool('package.py', False)
        self.assertFalse((self.root / 'dist/assets/leak.txt').exists())
        self.assertEqual(before, (self.root / 'dist/index.html').read_bytes())

    def test_output_symlink_is_not_followed(self):
        self.run_tool('build.py')
        (self.root / 'dist').symlink_to(self.root / 'content')
        self.run_tool('package.py', False)
        self.assertTrue((self.root / 'content/content.json').is_file())


if __name__ == '__main__':
    unittest.main()
