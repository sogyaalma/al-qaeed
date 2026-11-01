"""Verify publication gates without editing inherited vendor assets."""
import hashlib
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from font_policy import EXPECTED_FACES, inputs, sanitize_css


class FontPolicyTests(unittest.TestCase):
    def test_policy_inputs_are_pinned_by_the_vendor_manifest(self):
        policy = inputs()
        manifest = ROOT / 'docs/nds-assets.json'
        self.assertTrue(manifest.is_file(), 'run tools/vendor_nds.py sync')
        self.assertEqual(set(policy), {Path(name).name for name in EXPECTED_FACES})
        for name, (digest, faces) in policy.items():
            self.assertRegex(digest, r'^[0-9a-f]{64}$')
            self.assertTrue(faces, f'{name} declares no reviewed face')
            self.assertEqual(hashlib.sha256((ROOT / 'assets/css' / name).read_bytes()).hexdigest(), digest,
                             f'{name} changed without a font-policy review')

    def test_exact_reviewed_faces_removed_only(self):
        for name, faces in EXPECTED_FACES.items():
            with self.subTest(name):
                short = Path(name).name
                original = (ROOT / name).read_bytes()
                found = [m.group() for m in re.finditer(rb'@font-face\s*\{[^{}]*\}', original)
                         if any(font.encode() in m.group() for font in faces)]
                self.assertEqual(len(found), len(faces))
                expected = original
                for face in found:
                    expected = expected.replace(face, b'', 1)
                self.assertEqual(sanitize_css(short, original), expected)
                # The vendored input itself is never modified in place.
                self.assertEqual((ROOT / name).read_bytes(), original)

    def test_unreviewed_vendor_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            sanitize_css('nds.critical.min.css', b'@font-face{font-family:fake}')

    def test_unexpected_face_count_is_rejected(self):
        policy = inputs()['nds.critical.min.css']
        tampered = (ROOT / 'assets/css/nds.critical.min.css').read_bytes()
        # A release that adds or drops a blocked face must force a human review.
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            sanitize_css('nds.critical.min.css', tampered + b'/* changed */')
        self.assertTrue(policy[1])

    def test_unrelated_css_is_not_rewritten(self):
        data = b':root{--project:1}/* unchanged */'
        self.assertEqual(sanitize_css('theme.css', data), data)


if __name__ == '__main__':
    unittest.main()
