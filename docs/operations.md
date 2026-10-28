# Operations

## Database

```bash
finsocnet kb doctor [--repair-fts]       # integrity, FTS, foreign keys, orphans, migrations
finsocnet kb backup [--to path]          # a consistent copy (data/backups/knowledge-<UTC>.db)
finsocnet kb migrate [--dry-run]         # applies pending migrations; a backup is taken first
finsocnet kb stats --ui
```

Migrations are numbered files in `migrations/` (`.sql` or `.py`), applied in one transaction with a foreign-key check, never edited after release. The current set: `001`–`003` (v1 → v2 schema and legacy mapping), `004` (embeddings, translations, visited items, person images), `005` (source pictures). The v1 data is kept in `legacy_*` tables until you approve dropping them ([`specs/09-checklist.md`](../specs/09-checklist.md) §3).

## Health of the knowledge

- `kb embed status` — vectors per kind, pending rows, other models.
- `kb translate detect-pending --by-source` — contents whose language nobody decided yet (they are not embedded).
- `kb gap list` — questions the base could not answer; `kb queue list` — what exploration will do next; `kb seen stats` — what explorers looked at.
- `kb decision list --reviewed none` — dedup decisions nobody re-checked.

## Evaluation

Golden sets in `evals/` (transform 30 cases, dedup 40, search 30, attribution 15). The agent produces outputs with the *current* skill instructions, then:

```bash
finsocnet eval prepare transform --out data/work/<run>/eval_inputs/
finsocnet eval score transform --outputs data/work/<run>/eval_outputs/ --out report.json
finsocnet eval score search --outputs <dir> --search-mode hybrid      # embeds the fixture with the configured model
```

Targets: transform validity 100 %, recall ≥ 0.80, precision ≥ 0.75; dedup accuracy ≥ 0.85, wrong-merge ≤ 0.03; search recall@10 ≥ 0.80; attribution ≥ 0.85. Baseline outputs and scores of 2026-10-28 are in `evals/baseline/` and `specs/improvements/eval-2026-10-28/`; they were produced by the author of the cases, so they are a regression baseline, not independent evidence.

## Self-improvement

Skill `self-improver` (`/finsocnet:improve`): collects signals (failed runs, lessons, feedback, gaps, vocabulary health), re-judges a sample of dedup decisions, applies **reversible data fixes** (`kb card merge|retire|update|link|unlink` — each snapshots to `card_history`, undo with `kb card undo`) and turns instruction lessons into **git branches** `self-improve/<date>-<topic>` with before/after evaluation tables. It never commits to `main` and never merges its own branches: you review them.

## Installing third-party skills

Only through skill `skill-installer` and only when you ask: fetch into quarantine, validate the format, scan for unsafe code and hidden instructions, read every file, show you a report, install after your "yes" into `.agents/skills/<name>/`, record source commit and hashes in `config/skills.lock.json`. Nothing staged is executed; installed third-party skills are never edited in place. `finsocnet install all` then links skills for harnesses that need it.

## Harnesses

`finsocnet install claude|omp|pi|hermes|codex|openclaw|shared|all [--uninstall]` registers the slash commands (`/finsocnet`, `:search`, `:card`, `:person`, `:strategy`, `:compare`, `:explore`, `:explore-step`, `:mine`, `:gaps`, `:sessions`, `:improve`, `:feedback`, `:skills`, `:install-skill`) rendered per harness from `commands/*.md`, and links the skills. Some harnesses load skills only at session start.

## Backups and the legacy data

Take a backup before anything bulk: `kb backup`. Deleting `legacy/` and dropping the `legacy_*` tables waits for your approval of [`specs/improvements/legacy-conversion.md`](../specs/improvements/legacy-conversion.md).
