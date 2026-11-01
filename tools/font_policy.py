"""Distribution-only font policy; never modify the inherited NDS source assets.

Three @font-face declarations in the pinned release name fonts this project has
no redistribution grant for, so the packager removes exactly those declarations
from SHA-pinned inputs and refuses to publish the font files:

  nds.critical.min.css        SaudiWeb-Regular.woff2, SaudiWeb-Bold.woff2
  nds-accessibility.min.css   Maqroo-Regular.woff2 (Arabic dyslexia preset)

The site ships licensed IBM Plex Sans / IBM Plex Sans Arabic; the accessibility
panel's Arabic dyslexia mode therefore falls back to the brand font instead of
claiming to supply a specialist Arabic typeface. That limitation is recorded in
docs/CUSTOM-EXCEPTIONS.md and NDS-REPORT.md.

The expected input digests come from docs/nds-assets.json, which
`tools/vendor_nds.py sync` writes for the pinned tag, so an NDS upgrade re-pins
the policy automatically while the *reviewed* set of blocked faces below still has
to be edited by a human if a release changes it.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "nds-assets.json"

BLOCKED = frozenset({"SaudiWeb-Regular.woff2", "SaudiWeb-Bold.woff2", "Maqroo-Regular.woff2"})
APPROVED = frozenset({
    "Cairo-Arabic.woff2", "Cairo-Latin.woff2",
    "IBMPlexSans-Bold-Latin1.woff2", "IBMPlexSans-Medium-Latin1.woff2",
    "IBMPlexSans-Regular-Latin1.woff2", "IBMPlexSans-SemiBold-Latin1.woff2",
    "IBMPlexSansArabic-Bold.woff2", "IBMPlexSansArabic-Medium.woff2",
    "IBMPlexSansArabic-Regular.woff2", "IBMPlexSansArabic-SemiBold.woff2",
    "OpenDyslexic-Bold.woff2", "OpenDyslexic-Regular.woff2",
    "ReadexPro-Arabic.woff2", "ReadexPro-Latin.woff2",
    "hgi-stroke-rounded.woff2",
})

# Reviewed expectations: which blocked faces each vendored stylesheet declares.
EXPECTED_FACES = {
    "assets/css/nds.critical.min.css": {"SaudiWeb-Regular.woff2", "SaudiWeb-Bold.woff2"},
    "assets/css/nds-accessibility.min.css": {"Maqroo-Regular.woff2"},
}


def reviewed_digests() -> dict[str, str]:
    """Input digests as recorded for the pinned release."""
    if not MANIFEST.is_file():
        raise ValueError("docs/nds-assets.json is missing; run tools/vendor_nds.py sync")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return manifest["sha256"]


def inputs() -> dict[str, tuple[str, frozenset]]:
    digests = reviewed_digests()
    resolved = {}
    for name, faces in EXPECTED_FACES.items():
        if name not in digests:
            raise ValueError(f"{name} is not in the vendor manifest; review the font policy")
        resolved[Path(name).name] = (digests[name], frozenset(faces))
    return resolved


def _inputs() -> dict[str, tuple[str, frozenset]]:
    return inputs()


def sanitize_css(name, data):
    policy = _inputs().get(name)
    if policy is None:
        return data
    digest, expected = policy
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Unreviewed {name}: review the font policy before packaging")
    removed = []

    def face(match):
        block = match.group(0)
        hits = [font for font in BLOCKED if font.encode() in block]
        if hits:
            if len(hits) != 1:
                raise ValueError("Unexpected combined font-face declaration")
            removed.extend(hits)
            return b""
        return block

    result = re.sub(rb"@font-face\s*\{[^{}]*\}", face, data)
    if set(removed) != set(expected) or len(removed) != len(expected):
        raise ValueError(f"Unexpected font-face declarations in {name}: {removed}")
    if any(font.encode() in result for font in BLOCKED):
        raise ValueError(f"Unresolved font URL in {name}")
    return result


def validate_assets(assets):
    fonts = Path(assets) / "fonts"
    if fonts.exists():
        nested = [p.relative_to(fonts).as_posix() for p in fonts.rglob("*") if p.is_dir()]
        if nested:
            raise ValueError("Font license review required for nested paths: " + ", ".join(sorted(nested)))
        unknown = {p.name for p in fonts.iterdir() if p.is_file()} - APPROVED - BLOCKED
        if unknown:
            raise ValueError("Font license review required: " + ", ".join(sorted(unknown)))
    # Validate before the packager replaces a previous known-good output.
    for name in _inputs():
        path = Path(assets) / "css" / name
        if path.is_file():
            sanitize_css(name, path.read_bytes())


def apply_to_package(assets):
    for name in _inputs():
        path = Path(assets) / "css" / name
        if path.is_file():
            path.write_bytes(sanitize_css(name, path.read_bytes()))
    for name in BLOCKED:
        if (Path(assets) / "fonts" / name).exists():
            raise ValueError(f"Blocked font was copied into the public package: {name}")
