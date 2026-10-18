# Asset license notices

These notices do not assign a license to this website or its biography/images.

- `NDS-vanilla-MIT.txt`: inherited NDS/Hugeicons notices; includes the selected
  HGI rules and the unchanged icon font.
- `ibmplexsans-OFL.txt`, `ibmplexsansarabic-OFL.txt`, `cairo-OFL.txt`,
  `readexpro-OFL.txt`: OFL notices retrieved 2026-10-18 from `google/fonts`,
  respective `ofl/<family>/OFL.txt` paths. The shipped fonts' name tables also
  identify their projects/copyright holders. No glyphs were modified.
- `OpenDyslexic-OFL.txt`: complete license extracted from name ID 13 of the
  shipped `OpenDyslexic-Regular.woff2` (the bold file carries the same notice).
- `hgi-blank.woff2`: identical NDS fallback bytes externalized for CSP; covered
  by the NDS notice above.

**Distribution gate:** no redistribution grant is recorded for inherited
`SaudiWeb-Regular.woff2`, `SaudiWeb-Bold.woff2` or `Maqroo-Regular.woff2`.
SaudiWeb metadata says Ministry of Culture KSA, all rights reserved; Maqroo has
no usable license/copyright name-table entry. Upstream MIT is not sufficient.

`tools/package.py` now excludes all three from **dist/** and removes exactly
two Saudi `@font-face` declarations from a SHA-pinned copy of the critical CSS.
Maqroo has no URL in the current shipped stylesheets. Source/vendor files are
preserved unchanged for audit/reproduction; do not publish the repository root.
The normal Arabic/English IBM Plex fonts remain unchanged. No Arabic specialist
dyslexia replacement or clinical benefit is claimed. Fonts newly added to the
source must pass the explicit publication allowlist before packaging.

This removes these fonts from the website distribution, **not** an assertion of
rights to the inherited files in Git history or this repository. Permission is
still required before distributing them separately or enabling them later.
The owner still decides rights to biography, translations, portrait, PDF, and
the project's own license. No license has been invented or assigned.
