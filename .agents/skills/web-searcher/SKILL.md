---
name: web-searcher
description: Search the open web with DuckDuckGo (no API key) to find traders, their profiles on other platforms, interviews, articles, forums and PDFs, with site filters, regions, time limits and news mode. Use for "find <trader>'s X/YouTube/blog", "search the web for …", filling knowledge gaps, or cross-platform verification; prefer google-searcher when results are thin or advanced operators are needed.
license: MIT
compatibility: FinSocNet repository with uv and ddgs.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: partial
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Web Searcher (DuckDuckGo)

> **Status: partial.** v1 scripts work today (see *Legacy commands*). The v2 adapter `scripts/web_search.py` below is built in Phase 4 and replaces them.

Keyless search; returns ItemRefs only. Use `web-reader` (or the dispatch rules) to fetch results.

## When to use

- Discovery queries, finding a person's other platforms, gap exploration.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/web-searcher/scripts/web_search.py
uv run $S search "<query>" [--site domain] [--region us-en|vn-vi|…] [--timelimit d|w|m|y] [--news] [--limit 20]
```

| Command | Returns |
|---|---|
| `search "<query>"` | ItemRef[] with `id = web:<sha1>` and `known` flag |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

Implements only `search` of the adapter contract; other subcommands exit 2 `UNSUPPORTED`.

## Procedure

1. `uv run finsocnet kb run start --skill web-searcher --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Run the search, judge results, enqueue promising ones: `kb queue add --target <url> --target-kind url --origin search_result --reason … --priority …`.
3. Thin or off-target results → try `google-searcher`.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| ids | `web:<sha1(canonical_url)[:16]>` (same as web-reader) |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill web-searcher --kind script_bug …` with the error, then report |

## Notes

- No `fetch`, `list`, `profile`.

## Legacy commands (v1, until Phase 4)

```bash
uv run .agents/skills/web-searcher/scripts/search_web.py "<query>" [--site x.com]
```

v1 scripts write the v1 schema. After migration 003 their output is converted; do not mix v1 ingestion with v2 runs on the same database.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/search_syntax.md` — operators
