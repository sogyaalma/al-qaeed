"""Verify publication gates without editing inherited vendor assets."""
import hashlib
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from font_policy import INPUTS, sanitize_css


class FontPolicyTests(unittest.TestCase):
    def test_exact_reviewed_faces_removed_only(self):
        name = 'nds.critical.min.css'
        original = (ROOT / 'assets/css' / name).read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), INPUTS[name][0])
        faces = [m.group() for m in re.finditer(rb'@font-face\s*\{[^{}]*\}', original)
                 if b'SaudiWeb-' in m.group()]
        self.assertEqual(len(faces), 2)
        expected = original
        for face in faces:
            expected = expected.replace(face, b'', 1)
        self.assertEqual(sanitize_css(name, original), expected)
        self.assertEqual((ROOT / 'assets/css' / name).read_bytes(), original)

    def test_unreviewed_vendor_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            sanitize_css('nds.critical.min.css', b'@font-face{font-family:fake}')

    def test_unrelated_css_is_not_rewritten(self):
        data = b':root{--project:1}/* unchanged */'
        self.assertEqual(sanitize_css('theme.css', data), data)


if __name__ == '__main__':
    unittest.main()
