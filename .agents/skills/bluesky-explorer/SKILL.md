---
name: bluesky-explorer
description: Explore Bluesky (fintwit traders who moved from X) — profiles, author feeds, full threads and post search via the public AT Protocol AppView — and store posts as FinSocNet content. Use for bsky.app links, Bluesky handles, "what does <trader> post on Bluesky".
license: MIT
compatibility: FinSocNet repository with httpx.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Bluesky Explorer

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Public API, no login for profiles, feeds and threads.

## When to use

- bsky.app profile/post URLs, Bluesky handles.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/bluesky-explorer/scripts/bluesky.py
uv run $S search "<query>" [--limit 50]
uv run $S profile <handle> [--ingest]
uv run $S list <handle> [--limit 100] [--save-cursor] [--enqueue]
uv run $S fetch <post url|at uri> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | posts (falls back to the browser if the API requires auth) |
| `profile <handle>` | profile |
| `list <handle>` | author feed |
| `fetch <post url|at uri>` | author self-thread + replies (cap 100) |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill bluesky-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Same as x-explorer: profile → person-matcher → list → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `bluesky:<did>:<rkey>` |
| source id | `bluesky:user:<handle>` |
| segments | `post`/`reply {uri}` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill bluesky-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
