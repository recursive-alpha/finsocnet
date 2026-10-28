---
name: hackernews-explorer
description: Search Hacker News stories and read full comment trees (quant, market structure, fintech, trading-system discussions) via the Algolia HN API, and store them as FinSocNet content. Use for news.ycombinator.com links or "what did HN say about …".
license: MIT
compatibility: FinSocNet repository with httpx.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: planned
  phase: "7"
  spec: docs/spec/05-platform-skills.md
---

# Hacker News Explorer

> **Status: planned — built in Phase 7.** Nothing below runs yet; it is the contract the implementation must follow.

Keyless API, full comment tree in one request.

## When to use

- HN item links, tech/quant discussions.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/hackernews-explorer/scripts/hackernews.py
uv run $S search "<query>" [--tags story] [--limit 50]
uv run $S fetch <item id|url> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | stories |
| `fetch <item id|url>` | story + all comments |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill hackernews-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. search → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `hn:<item_id>` |
| content_type | `thread` |
| segments | story `post`; comments `{comment_id, parent_id}` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill hackernews-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
