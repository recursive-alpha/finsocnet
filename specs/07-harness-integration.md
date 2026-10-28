# 07 — Harness Integration, CLI and TUI

FinSocNet is used through AI harnesses. The skills in `.agents/skills/` are the main interface; the `finsocnet` CLI is the shared entry point for scripts, local session export, and installation.

---

## 1. `finsocnet` CLI (Python package `finsocnet/`)

| Command | Runs on | Purpose |
|---|---|---|
| `finsocnet kb …` | remote | database CLI (01 §6) |
| `finsocnet eval …` | remote | evaluation (06 §3) |
| `finsocnet explore add <target> [--priority]` | remote | user seed → `explore_queue` |
| `finsocnet persons review` | remote | interactive review of `needs_review` appearances (confirm/reject/reassign) |
| `finsocnet feedback <type> <id> <+1|-1> [comment]` | remote | user feedback |
| `finsocnet session init-local|export|push` | **local** | session bridge, local side (04 §3) |
| `finsocnet install <harness|all>` | remote (and local if the user runs a harness locally against a remote over SSH) | register harness integrations (§2) |
| `finsocnet tui` | remote | Textual TUI: stats, search, person rulebooks, gaps, queue, sessions |
| `finsocnet` (no args) | remote | `kb stats` in text form |

Remove from the CLI: `vector_search`, `rag_search` (old `finsocnet/search.py`), Chroma stats, `hypotheses` listing (replaced by cards).

`install.sh` installs the package with `uv tool install` so `finsocnet` works outside the repo. On the user's local machine only the `session` commands are needed; `install.sh --local` installs the `local` extra (`rookiepy`, `ccl_chromium_reader`, `pyrage`).

---

## 2. Harness Registration

Unchanged targets:

| Harness | Path |
|---|---|
| Claude Code | `~/.claude/commands/finsocnet.md` (+ optional `~/.claude/skills/` symlinks to `.agents/skills/*`) |
| OMP | `~/.omp/agent/extensions/finsocnet.ts` |
| Pi Coding Agent | `~/.pi/agent/extensions/finsocnet.ts` |
| Hermes | `~/.hermes/skills/research/finsocnet/` |
| OpenAI Codex | `~/.codex/skills/finsocnet/` |
| OpenClaw | `~/.openclaw/skills/finsocnet/` |

Installer rules:
- Generated files reference the repo path (`FINSOCNET_HOME`) and run commands with `uv run --project $FINSOCNET_HOME …`.
- For harnesses that support agentskills.io skills, install **symlinks** to `.agents/skills/<skill>` (system skills only); do not copy, so updates apply immediately.
- `finsocnet install --uninstall <harness>` removes what it created.
- Persons with `visibility='private_source'` are excluded from anything the installer exports or caches.

---

## 3. Slash Commands

Defined once in `commands/` (source of truth) and rendered per harness by the installer.

| Command | Behaviour |
|---|---|
| `/finsocnet` | `kb stats` summary: persons, sources, contents by status, cards, citations, consensus top 10, open gaps, queue, session health |
| `/finsocnet:search <question>` | run `knowledge-search` (03 §4) |
| `/finsocnet:card <id>` | `kb card get <id> --citations --links` rendered with links and timestamps |
| `/finsocnet:person <id or name>` | profile, aliases, appearances, `person_stats` |
| `/finsocnet:strategy <person> [category] [--rebuild]` | `kb skill get … --render markdown`; `--rebuild` runs `person-skill-synthesizer` first |
| `/finsocnet:compare <person,person> <topic>` | `person-skills-explorer` compare procedure |
| `/finsocnet:explore <target>` | `finsocnet explore add` + one `source-explorer` step for it |
| `/finsocnet:explore-step` | one `source-explorer` step (for loops/schedules) |
| `/finsocnet:mine <content_id>` | run `market-idea-miner` on one content |
| `/finsocnet:gaps` | open gaps with asked counts |
| `/finsocnet:sessions` | `session_bridge.py status` |
| `/finsocnet:improve` | one `self-improver` run; reports proposals and branches |
| `/finsocnet:feedback <type> <id> <+1|-1> [comment]` | records feedback |
| `/finsocnet:skills` | `skill_installer.py list`: core vs installed skills, version, source, locally modified, outdated |
| `/finsocnet:install-skill <link>` | `skill-installer` install procedure (§5) |

Removed: `/finsocnet:rag`, `/finsocnet:view <hypothesis id>` (replaced by `/finsocnet:card`). `/finsocnet:skills` changes meaning: the v1 "System vs Improved Strategy skills" split is gone; it now lists core vs installed skills.

---

## 4. Documentation to Update in Phase 8

- `AGENTS.md`: rewrite from this spec (skill table = SPEC §5, pipelines = 03, sessions = 04). Remove Chroma, `hypothesis-miner`, `user-skill-synthesizer`, password login, `vector-search`/`rag-search`.
- `README.md`: product overview, install (remote + local), quickstart (keygen → export → push → explore → search).
- `.env.example`: 00 §6.
- Each SKILL.md: 00 §9 template.

---

## 5. Skill Installer (`skill-installer`)

Lets the user paste a link to any agentskills.io skill and get it installed into `.agents/skills/` after validation, a security review by the agent, and the user's yes. Procedures and review rules for the agent: `.agents/skills/skill-installer/SKILL.md` and its `references/` (`review_checklist.md` §1 is the source of truth for scanner rules; implement every rule in it).

### 5.1 Code

| Path | Content |
|---|---|
| `finsocnet/core/skill_install.py` | `resolve(link)`, `fetch(link, skill)`, `safe_extract()`, `scan(staging)`, `validate_frontmatter()`, `verify_review()`, `install()`, `remove()`, lock read/write |
| `.agents/skills/skill-installer/scripts/skill_installer.py` | thin CLI: `resolve, fetch, check, diff, install, list, outdated, remove, discard` (standard envelope, exit codes 00 §3.3) |
| `finsocnet/skills.py` | replace `SYSTEM_SKILL_NAMES` with: core = every folder in `.agents/skills/` not in the lock; installed = lock entries |

### 5.2 Fetching (never executes anything)

- GitHub: `GET /repos/<o>/<r>/commits/<ref>` → commit SHA; tree via `GET /repos/<o>/<r>/git/trees/<sha>?recursive=1`; files via `https://codeload.github.com/<o>/<r>/tar.gz/<sha>` streamed and filtered to the chosen path. `GITHUB_TOKEN` used if set (rate limit only).
- Other git: `git clone --depth 1 --no-recurse-submodules -c core.hooksPath=/dev/null` with `GIT_LFS_SKIP_SMUDGE=1`, then the `.git` folder is deleted from staging.
- Archives: Python `zipfile`/`tarfile` with manual member checks before writing (reject links, absolute paths, `..`, device files; enforce B4 limits while streaming). Never `extractall` without filters.
- Web pages: through `web-reader` (agent browser); only links are returned.
- Staging layout: `data/skill-staging/<staging_id>/{skill/, manifest.json, check.json, review.json}`. `staging_id` = `st-<UTC yyyymmddHHMMSS>-<4 hex>`. Staging folders older than 7 days are deleted by `fetch` and `list`.
- `manifest.json`: `{staging_id, source:{kind, url, repo, ref, commit, path}, fetched_at, files:{<relpath>:{sha256, bytes, type}}}`.

### 5.3 Check

1. Block rules B1–B6, then high H1–H8, medium M1–M4, info. Each finding: `{id: "F<n>", rule, severity, file, line, excerpt}`; excerpts ≤ 200 chars with anything that looks like a secret masked.
2. `files_to_read`: every text file with its sha256; on updates, unchanged files (same hash as the lock) are marked `unchanged: true`.
3. Output also has `frontmatter`, `dependencies` (PEP 723 blocks, imports not in `pyproject.toml`, other manifests), `hosts`, and `conflict`.
4. `--as <new-name>`: validation runs as if the folder and frontmatter `name` were renamed; `install --as` rewrites only the frontmatter `name` line and records `renamed_from` in the lock.

### 5.4 Install

`install` verifies, in order: staging exists and has no block finding → `review.json` validates against `finsocnet/core/schemas/skill_review.schema.json` → every manifest file is in `files_read` with the same sha256 and the staged file still has that hash → every high finding has `assessment` ∈ {`false_positive`, `accepted`} → `verdict = approve` → `--user-confirmed` present → target name free (or `--replace` and the existing entry is an installed skill from the same source). Then: copy to `.agents/skills/<name>.tmp-<4hex>/`, rename into place (atomic), back up any replaced folder to `data/skill-backups/<name>-<UTC>/`, write the lock, record the run, delete staging. Dependencies are never installed; they are reported.

### 5.5 Lock file `config/skills.lock.json` (git-tracked)

```json
{
  "version": 1,
  "skills": {
    "pdf-tools": {
      "source": {"kind": "github", "url": "https://github.com/o/r/tree/main/skills/pdf-tools",
                 "repo": "o/r", "ref": "main", "commit": "3f2a1bc…(40 hex)", "path": "skills/pdf-tools"},
      "installed_at": "2026-10-28T09:15:00Z",
      "run_id": 42,
      "renamed_from": null,
      "files": {"SKILL.md": "<sha256>", "scripts/extract.py": "<sha256>"},
      "review": {"verdict": "approve", "high_accepted": ["H1: uvx markitdown for DOCX"],
                 "summary": "Extracts text and tables from PDFs with pypdf. No network.",
                 "reviewed_by": {"harness": "claude-code", "model": "…"}},
      "dependencies": ["pypdf (PEP 723)"]
    }
  }
}
```

`outdated` compares `source.commit` with the current commit of `source.ref` (no download) and the installed files with `files` hashes (`locally_modified`). `kind = local` entries have no upstream check.

### 5.6 Tests

Offline fixtures in `tests/fixtures/skill-installer/`: a clean skill; one per block rule (symlink, `../` zip entry, ELF file, oversize, bad name, core-name collision); one per high rule; a skill whose SKILL.md hides a zero-width-character instruction; a repo with three skills; a `review.json` missing one file; a staged file modified after `check` (must fail with `REVIEW_INCOMPLETE`). Assert that no test ever executes a staged file (patch `subprocess` to fail on any staged path).

