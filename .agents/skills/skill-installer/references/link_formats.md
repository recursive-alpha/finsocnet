# Supported links

`skill_installer.py resolve <link>` turns any of these into one or more **candidates** (a skill folder at a pinned commit). Check rows top to bottom; the first match wins.

| # | Link the user pastes | Resolution |
|---|---|---|
| 1 | `https://github.com/<o>/<r>/tree/<ref>/<path>` | the folder `<path>` at `<ref>`; `<ref>` resolved to a commit SHA via `GET /repos/<o>/<r>/commits/<ref>` |
| 2 | `https://github.com/<o>/<r>/blob/<ref>/<path>/SKILL.md` | the folder containing that SKILL.md |
| 3 | `https://raw.githubusercontent.com/<o>/<r>/<ref>/<path>/SKILL.md` | same as 2 |
| 4 | `https://github.com/<o>/<r>` (repo root, optionally `.git`) | default branch; every folder in the tree that contains a `SKILL.md` becomes a candidate (also inside Claude plugin layouts: `plugins/*/skills/*/SKILL.md`, `.claude-plugin/marketplace.json`) |
| 5 | `<o>/<r>` · `<o>/<r>@<skill-name>` · `<o>/<r>/<path>` (skills CLI shorthand) | GitHub; `@<skill-name>` picks the candidate whose frontmatter `name` matches |
| 6 | `https://gitlab.com/…`, `https://codeberg.org/…`, any `https://…/*.git` | `git clone --depth 1 --no-recurse-submodules` with `GIT_LFS_SKIP_SMUDGE=1` and `core.hooksPath=/dev/null` into staging; then as 4 (`/-/tree/<ref>/<path>` and `/src/branch/<ref>/<path>` select a folder) |
| 7 | URL ending `.zip`, `.skill`, `.tar.gz`, `.tgz` | download (≤ 20 MB), safe extraction (see review_checklist B1–B4), then as 4 |
| 8 | Any other URL ending `SKILL.md` | single-file skill: only `SKILL.md`; warning `single_file` (bundled references/scripts, if any, are missing) |
| 9 | Any other web page (skill directories, marketplaces, blog posts) | the page is read through `web-reader`; GitHub, archive and SKILL.md links found on it are returned as `links`, not candidates. Show them to the user and ask which one, or pick the only obvious one and say so |
| 10 | Local path on the remote host (folder, archive or SKILL.md the user uploaded) | copied into staging; source `kind = local`, no update tracking |

Candidate fields returned by `resolve`:

```json
{"candidate": 1, "name": "pdf-tools", "description": "…", "path": "skills/pdf-tools",
 "source": {"kind": "github", "repo": "o/r", "ref": "main", "commit": "3f2a1bc…(40 hex)", "url": "https://github.com/o/r/tree/main/skills/pdf-tools"},
 "files": 7, "bytes": 48213, "conflict": null}
```

`conflict` is `null`, `{"with": "core", "name": "web-reader"}` (a FinSocNet core or platform skill — install only with `--as`), or `{"with": "installed", "name": "pdf-tools", "same_source": true}` (that is an update; use the update procedure).

Not supported: private repositories (no credentials, ADR-005). Ask the user to download the archive locally and upload it (row 10).
