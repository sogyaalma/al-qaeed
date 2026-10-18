"""Distribution-only font policy; never modify the inherited NDS source assets.

Remove exactly two reviewed @font-face declarations from SHA-pinned inputs.
The site uses licensed IBM Plex; Arabic dyslexia mode falls back to that brand
font, without claiming to supply a replacement specialist Arabic typeface.
"""
import hashlib
from pathlib import Path
import re

BLOCKED = frozenset({'SaudiWeb-Regular.woff2', 'SaudiWeb-Bold.woff2', 'Maqroo-Regular.woff2'})
APPROVED = frozenset({
    'Cairo-Arabic.woff2', 'Cairo-Latin.woff2',
    'IBMPlexSans-Bold-Latin1.woff2', 'IBMPlexSans-Medium-Latin1.woff2',
    'IBMPlexSans-Regular-Latin1.woff2', 'IBMPlexSans-SemiBold-Latin1.woff2',
    'IBMPlexSansArabic-Bold.woff2', 'IBMPlexSansArabic-Medium.woff2',
    'IBMPlexSansArabic-Regular.woff2', 'IBMPlexSansArabic-SemiBold.woff2',
    'OpenDyslexic-Bold.woff2', 'OpenDyslexic-Regular.woff2',
    'ReadexPro-Arabic.woff2', 'ReadexPro-Latin.woff2',
    'hgi-blank.woff2', 'hgi-stroke-rounded.woff2',
})
# These are the reviewed inherited inputs, not arbitrary CSS substitutions.
INPUTS = {
    'nds.critical.min.css': ('56c556638b25ce84b6102ede9b6a1c1bd0fab9516cbfa979a4ad52fac3c19a87',
                             {'SaudiWeb-Regular.woff2', 'SaudiWeb-Bold.woff2'}),
}


def sanitize_css(name, data):
    if name not in INPUTS:
        return data
    digest, expected = INPUTS[name]
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Unreviewed {name}: review the font policy before packaging')
    removed = []

    def face(match):
        block = match.group(0)
        hits = [font for font in BLOCKED if font.encode() in block]
        if hits:
            if len(hits) != 1:
                raise ValueError('Unexpected combined font-face declaration')
            removed.extend(hits)
            return b''
        return block

    result = re.sub(rb'@font-face\s*\{[^{}]*\}', face, data)
    if set(removed) != expected or len(removed) != len(expected):
        raise ValueError(f'Unexpected font-face declarations in {name}: {removed}')
    if any(font.encode() in result for font in BLOCKED):
        raise ValueError(f'Unresolved font URL in {name}')
    return result


def validate_assets(assets):
    fonts = Path(assets) / 'fonts'
    if fonts.exists():
        nested = [p.relative_to(fonts).as_posix() for p in fonts.rglob('*') if p.is_dir()]
        if nested:
            raise ValueError('Font license review required for nested paths: ' + ', '.join(sorted(nested)))
        unknown = {p.name for p in fonts.iterdir() if p.is_file()} - APPROVED - BLOCKED
        if unknown:
            raise ValueError('Font license review required: ' + ', '.join(sorted(unknown)))
    # Validate before the packager replaces a previous known-good output.
    for name in INPUTS:
        path = Path(assets) / 'css' / name
        if path.is_file():
            sanitize_css(name, path.read_bytes())


def apply_to_package(assets):
    for name in INPUTS:
        path = Path(assets) / 'css' / name
        if path.is_file():
            path.write_bytes(sanitize_css(name, path.read_bytes()))
    for name in BLOCKED:
        if (Path(assets) / 'fonts' / name).exists():
            raise ValueError(f'Blocked font was copied into the public package: {name}')
