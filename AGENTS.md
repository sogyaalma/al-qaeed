## NDS — National Design System (UI layer)

- `NDS_ROOT` = `.nds/`
- `NDS_ASSETS` = `/home/user/al-qaeed/assets/`
- Pinned release: **v1.12.0** at commit `030d1c7ff4ab5a3092c17b93429b1ac55291ea4d`, recorded in `tools/nds-pin.json`. Follow that pin. Do not switch to a newer tag, an unreleased branch, or IQ tag `IQv3.2` without an explicit owner decision. Consult the pinned tag's component docs (`components/`, `layout/`, `ui-shell/`, `utilities/`) before writing markup.

All UI in this project is built with NDS. Before any UI, page, component, styling,
or asset work — or when unsure whether a task touches NDS — read `NDS-IQ.md` at this
project's root, top to bottom, once per session. Do no NDS work before that read.
A compacted or summarized context starts a new session: read the file again before
more NDS work.
If the file is missing, stop and ask the dev.

These hold even before the read:
- Never edit anything under `NDS_ROOT`; never hand-edit NDS files in `NDS_ASSETS`.
- Never write `.nds-*` markup from memory — copy from the sources `NDS-IQ.md` names.
