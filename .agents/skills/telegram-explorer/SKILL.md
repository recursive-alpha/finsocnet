---
name: telegram-explorer
description: Read Telegram trading channels and groups — public channels through the t.me/s web preview without login (posts, views, forwards, media), and private channels or groups through Telegram Web with the user's imported session — and store posts and messages as FinSocNet content. Use for t.me links, @channel names, signal/analysis channels, Vietnamese or international trading groups on Telegram.
license: MIT
compatibility: FinSocNet repository; browser mode needs agent-browser and an imported web.telegram.org session.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Telegram Explorer

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Public mode needs no login and is preferred. Browser mode (Telegram Web) is for private channels and groups.

## When to use

- t.me / telegram.me links, Telegram channel names.

## Before you start

- None for public channels; session for private ones.
- Session `telegram` (browser mode only): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform telegram`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/telegram-explorer/scripts/telegram.py
uv run $S search "<query>" --channel <name>
uv run $S profile <channel> [--ingest]
uv run $S list <channel> [--limit 200] [--cursor before_id] [--save-cursor] [--enqueue]
uv run $S fetch <t.me/<c>/<id>|channel --since D> [--mode public|browser] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>" --channel <name>` | posts in a public channel matching the query |
| `profile <channel>` | title, description, subscribers |
| `list <channel>` | posts newest first |
| `fetch <t.me/<c>/<id>|channel --since D>` | post or day window |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill telegram-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Public channel: `profile --ingest` → `list --enqueue --save-cursor --run R` → fetch posts → market-idea-miner.
3. Discover channels: web-searcher `--site t.me "<topic>"`.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | public posts `telegram:<channel>:<msg_id>`; groups/private `telegram:<chat_id>:<YYYY-MM-DD>` |
| source id | `telegram:channel:<name>` |
| segments | `kind=post|message {msg_id}` |
| persons | group members → `private_source` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill telegram-explorer --kind script_bug …` with the error, then report |

## Notes

- Forwarded posts: `extra.forwarded_from` → enqueue the origin channel.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
