---
name: stocktwits-explorer
description: Read StockTwits symbol streams and user streams and store messages as FinSocNet content. Use for stocktwits.com links, $TICKER sentiment streams, or StockTwits users. Most messages yield no cards; that is expected and nothing is discarded.
license: MIT
compatibility: FinSocNet repository; agent-browser if the public API is unavailable.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: ready
  phase: "7"
  spec: docs/spec/05-platform-skills.md
---

# StockTwits Explorer

High noise. Fetch on demand (a symbol or a known user), not as a broad crawl.

## When to use

- StockTwits URLs, symbol streams, known StockTwits users.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/stocktwits-explorer/scripts/stocktwits.py
uv run $S profile <user> [--ingest]
uv run $S list <$SYM|user> [--limit 200] [--enqueue]
uv run $S fetch <message id|url> [--ingest]
```

| Command | Returns |
|---|---|
| `profile <user>` | user |
| `list <$SYM|user>` | messages |
| `fetch <message id|url>` | one message |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill stocktwits-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Known user: `profile` → person-matcher → `list user --enqueue`.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `stocktwits:<message_id>` |
| source id | `stocktwits:symbol:<SYM>`, `stocktwits:user:<name>` |
| segments | one `post` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill stocktwits-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
