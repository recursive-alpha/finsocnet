---
name: tradingview-explorer
description: Explore TradingView — trade ideas with descriptions, symbol, timeframe and long/short labels, open-source Pine Script indicators and strategies with their code, author profiles and comments — and store them as FinSocNet content so strategy logic in Pine code becomes Knowledge Cards. Use for tradingview.com links, "Pine script for …", "ideas by <author>", "TradingView ideas on <symbol>".
license: MIT
compatibility: FinSocNet repository, agent-browser running.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# TradingView Explorer

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Pine code is split into ≤ 60-line code segments; knowledge-transformer reads the entry/exit logic. Protected or invite-only scripts give description only.

## When to use

- TradingView idea/script/user URLs, Pine Script strategies.

## Before you start

- Agent browser running.
- Session `tradingview` (optional): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform tradingview`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/tradingview-explorer/scripts/tradingview.py
uv run $S search "<query>" [--scripts|--ideas] [--limit 50]
uv run $S profile <user> [--ingest]
uv run $S list <user|symbol EXCH:SYM> [--scripts|--ideas] [--limit 100] [--enqueue]
uv run $S fetch <idea or script url> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | ideas or scripts |
| `profile <user>` | bio, followers, reputation |
| `list <user|symbol EXCH:SYM>` | a user's or a symbol's ideas/scripts |
| `fetch <idea or script url>` | idea text + comments, or script description + code |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill tradingview-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Author: `profile --ingest` → person-matcher → `list --scripts --enqueue` and `list --ideas --enqueue`.
3. Script: `fetch --ingest --run R` → market-idea-miner with `--max-chars 6000`.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `tradingview:idea:<id>`, `tradingview:script:<id>` |
| source id | `tradingview:user:<username>` |
| content_type | `idea`, `script` |
| segments | description paragraphs; code `kind=code {line_start, line_end}`; comments |
| extra | `symbol`, `timeframe`, `direction`, `code_visible`; chart snapshot in media |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill tradingview-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
