# Reviewed icon-source inputs (not a complete NDS reference)

These two files are verbatim from `mazin-musleh/NDS-vanilla` commit
`0da6366911e039d5f1afd749a9b116e67dade15d`, `_sass/`:

- `_hgiRoundedStroke.scss`, SHA-256 `d7a8191265d7886833e1d6a06f89cffcb00ae70f229fca5e87e8db5bcebeaa43`.
- `_fonts-hgi-blank.scss`, SHA-256 `e5dfccc31c34f1e5752f5ddf6ac499c8cbe530cde7bc5550236d40be5394a24e`.

[MIT notice](../../assets/licenses/NDS-vanilla-MIT.txt). No source changes,
font glyph edits, full NDS rebuild, or runtime upgrade. These isolated inputs
make `python3 tools/reproduce_nds.py` work offline with full Git history.
They are **not** `.nds/`, not matching built visual twins, and not proof of the
unknown upstream commit used for the inherited complete runtime.

Source API: `https://api.github.com/repos/mazin-musleh/NDS-vanilla/contents/_sass/?ref=0da6366911e039d5f1afd749a9b116e67dade15d`.
