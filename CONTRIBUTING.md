# Contributing / المساهمة

Discuss material content, translation, portrait, PDF or NDS version changes with
the repository owner first. Routine fixes should be small and evidenced by a
reproduction or regression test. Do not invent biographical facts.

1. Edit `content/content.json` for biography text, `tools/build.py` for generated
   markup, and `assets/css/theme.css` / `assets/js/site.js` for project customization.
2. Run the build, static, unit and browser checks in [README.md](README.md).
3. Commit generated HTML and CSP headers together with their source changes.
   Never commit `dist/`, credentials, local tooling or fresh scratch reports.
4. In a pull request, describe the defect, change, commands actually run and any
   unverified areas. Include current screenshots for visible UI changes.

Read [AGENTS.md](AGENTS.md) and [NDS-INTEGRATION.md](docs/NDS-INTEGRATION.md) before
NDS work. Do not hand-edit/minify vendor bundles, upgrade an unpinned branch or
silently drop assets. The documented encoding/font-URL repair is reproducible.

No project-wide reuse license has been selected. Third-party license notices
apply only to their respective assets; owner approval is required for a project
license and for publication rights to biography/portrait/PDF.
