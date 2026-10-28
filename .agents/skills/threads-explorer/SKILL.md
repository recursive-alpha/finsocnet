---
name: threads-explorer
description: Explore Threads (Meta) — trader profiles and posts with replies — through the agent browser and store them as FinSocNet content. Use for threads.net / threads.com links and handles.
license: MIT
compatibility: FinSocNet repository, agent-browser.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: ready
  phase: "7"
  spec: specs/05-platform-skills.md
---

# Threads Explorer

Browser with GraphQL capture where possible.

## When to use

- Threads profiles and posts.

## Before you start

- Agent browser running.
- Session `threads` (optional): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform threads`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/threads-explorer/scripts/threads.py
uv run $S profile <@handle> [--ingest]
uv run $S list <@handle> [--limit 100] [--enqueue]
uv run $S fetch <post url> [--ingest]
```

| Command | Returns |
|---|---|
| `profile <@handle>` | profile |
| `list <@handle>` | posts |
| `fetch <post url>` | post + replies |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill threads-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. profile → person-matcher → list → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `threads:<post_id>` |
| source id | `threads:user:<handle>` |
| segments | `post`/`reply` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill threads-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
