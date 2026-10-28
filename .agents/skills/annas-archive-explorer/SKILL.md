---
name: annas-archive-explorer
description: Search Anna's Archive for trading and finance books, textbooks and papers (Market Wizards, Reminiscences, quant textbooks), read book details and mirrors by MD5, and download a chosen edition for document-reader to ingest. Use for "find the book …", "books by <trader>", a book cited by a trader, or target_kind=book queue items.
license: MIT
compatibility: FinSocNet repository; agent-browser for DDoS-Guard pages.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Anna's Archive Explorer

Search and metadata are always allowed; downloads happen only on an explicit `download` call. Downloading copyrighted books may be illegal where the user lives — mention this when the user asks to download.

## When to use

- A book title/author, a book mentioned in content, `target_kind=book`.

## Before you start

- Agent browser running when mirrors show DDoS-Guard.

## Commands

```bash
S=.agents/skills/annas-archive-explorer/scripts/annas.py
uv run $S search "<title or author>" [--ext pdf|epub] [--lang en|vi] [--limit 20]
uv run $S fetch <md5> [--ingest]
uv run $S download <md5> [--mirror N]
```

| Command | Returns |
|---|---|
| `search "<title or author>"` | ItemRef[] with `id = book:<md5>` |
| `fetch <md5>` | metadata_only content: title, author, year, description, mirrors |
| `download <md5>` | file in `data/books/<md5>.<ext>`, then run `document-reader fetch` on it |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill annas-archive-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. `search` → pick the best edition (language, format, completeness) → `fetch --ingest` → `download` → `document-reader fetch data/books/<md5>.<ext> --ingest --run R` → market-idea-miner (8000-char chunks).
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `book:<md5>` |
| content_type | `book` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill annas-archive-explorer --kind script_bug …` with the error, then report |

## Notes


## Legacy commands (v1 names; thin wrappers until Phase 8)

```bash
uv run .agents/skills/annas-archive-explorer/scripts/search_archive.py "Market Wizards" --ext pdf
uv run .agents/skills/annas-archive-explorer/scripts/get_book_details.py "<md5>"
```

The v1 names call the v2 adapter (`--ingest-db` maps to `--ingest`); use the new subcommands in new work.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/annas_archive_guide.md` — mirrors, search filters, download flow
