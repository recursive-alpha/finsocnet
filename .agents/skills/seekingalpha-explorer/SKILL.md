---
name: seekingalpha-explorer
description: Read Seeking Alpha articles, author profiles and comments (premium articles with the user's subscription session) and store them as FinSocNet content. Use for seekingalpha.com article or author links, "<author>'s articles on <ticker>".
license: MIT
compatibility: FinSocNet repository, agent-browser.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: planned
  phase: "7"
  spec: docs/spec/05-platform-skills.md
---

# Seeking Alpha Explorer

> **Status: planned — built in Phase 7.** Nothing below runs yet; it is the contract the implementation must follow.

PerimeterX "Press & Hold" challenges appear often: exit 3 `CHECKPOINT`, then solve via `agent_browser.py vnc` or skip.

## When to use

- Seeking Alpha articles and authors.

## Before you start

- Agent browser running.
- Session `seekingalpha` (optional, premium): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform seekingalpha`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/seekingalpha-explorer/scripts/seekingalpha.py
uv run $S profile <author url> [--ingest]
uv run $S list <author url> [--limit 50] [--enqueue]
uv run $S fetch <article url> [--comments] [--ingest]
```

| Command | Returns |
|---|---|
| `profile <author url>` | author bio, followers |
| `list <author url>` | articles |
| `fetch <article url>` | article paragraphs (+ comments) |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill seekingalpha-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. author → person-matcher → list → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `seekingalpha:<article_id>` |
| source id | `seekingalpha:author:<slug>` |
| content_type | `article` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill seekingalpha-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
