---
name: forum-explorer
description: Read trading forums of any engine — Elite Trader, BabyPips, Futures.io, Forex Factory, Trade2Win, F319 (Vietnam) and any Discourse, XenForo, vBulletin or phpBB forum — detect the engine, list boards and threads, read every page of a thread with each post's author, search, and store threads as FinSocNet content. Use for forum links, "what do forum traders say about …", long-running journal threads.
license: MIT
compatibility: FinSocNet repository, agent-browser running (Cloudflare-protected forums); config/forums.yaml.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Trading Forum Explorer

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Engine adapters: Discourse via its JSON API, XenForo/vBulletin/phpBB via HTML selectors, anything else via web-reader with agent-guided pagination. Reads all pages of a thread (cap `--max-pages 200` with a warning).

## When to use

- Forum thread/board URLs, hosts in config/forums.yaml.

## Before you start

- Agent browser running.

## Commands

```bash
S=.agents/skills/forum-explorer/scripts/forum.py
uv run $S detect <url>
uv run $S search "<query>" --host <host> [--limit 50]
uv run $S profile <user url> [--ingest]
uv run $S list <board url|host> [--limit 100] [--enqueue] [--save-cursor]
uv run $S fetch <thread url> [--max-pages 200] [--ingest]
```

| Command | Returns |
|---|---|
| `detect <url>` | engine: discourse|xenforo|vbulletin|phpbb|generic |
| `search "<query>" --host <host>` | threads |
| `profile <user url>` | forum user |
| `list <board url|host>` | threads in a board |
| `fetch <thread url>` | all posts of a thread |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill forum-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. New forum: `detect` → add/confirm in `config/forums.yaml` (host, engine, language) via a lesson/branch → `list` boards of interest `--enqueue`.
3. Thread: `fetch --ingest --run R` → market-idea-miner. Long trading-journal threads are valuable: one author's posts over years.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `forum:<host>:<thread_id>` |
| source id | `forum:board:<host>:<board_id>`, `forum:user:<host>:<user_id>` |
| content_type | `thread` |
| segments | each post `kind=post|reply {post_id, page}`, author per post; quoted text moved to `extra` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill forum-explorer --kind script_bug …` with the error, then report |

## Notes

- Initial forums.yaml entries (engines to verify): elitetrader.com xenforo, forums.babypips.com discourse, futures.io generic, forexfactory.com generic, trade2win.com xenforo, f319.com xenforo (vi).

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
