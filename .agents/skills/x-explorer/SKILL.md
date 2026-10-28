---
name: x-explorer
description: Explore X (Twitter) through the agent browser with the user's imported session — profiles and bios, timelines, replies, full author threads, live and top search with operators and $cashtags, and store posts as FinSocNet content. Use for x.com or twitter.com links, @handles, "what does <trader> post on X", "search X for …", fintwit threads.
license: MIT
compatibility: FinSocNet repository, agent-browser running, x.com session imported via session-bridge.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# X (Twitter) Explorer

Reads X by capturing the web app's own GraphQL JSON while the agent browser scrolls; DOM parsing is only a fallback. Strict budget (`config/budgets.yaml: x`).

## When to use

- x.com / twitter.com URLs, @handles, cashtag research, fintwit threads.

## Before you start

- `agent_browser.py status` OK; `session_bridge.py status --platform x` shows `logged_in`.
- Session `x`: check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform x`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/x-explorer/scripts/x.py
uv run $S search "<query>" [--limit 50] [--top] [--since YYYY-MM-DD]
uv run $S profile <@handle|url> [--ingest]
uv run $S list <@handle> [--with-replies] [--limit 200] [--since D] [--save-cursor] [--enqueue]
uv run $S fetch <status url|tweet id> [--max-replies 100] [--transcribe-video] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | live (default) or top results; operators `from:`, `since:`, `min_faves:`, `$TICKER` work |
| `profile <@handle|url>` | bio, links, followers, verified, created_at |
| `list <@handle>` | timeline, cursor = oldest tweet id |
| `fetch <status url|tweet id>` | author self-thread + top replies |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill x-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Person on X: `profile --ingest` → `person-matcher` → `list --enqueue --save-cursor --run R` for their posts.
3. Thread: `fetch <url> --ingest --run R` → `market-idea-miner`.
4. Topic research: `search` → enqueue promising threads (`kb queue add --origin search_result`).
5. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
6. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `x:<tweet_id>`; a thread uses the root tweet id |
| source id | `x:user:<handle lowercase>` |
| content_type | `post` or `thread` |
| segments | each tweet `kind=post` (author) or `reply`, `locator={tweet_id}`; quoted tweet as extra segment with `locator.quoted_id`; note-tweets in full |
| media | image/video URLs; videos with speech → `--transcribe-video` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill x-explorer --kind script_bug …` with the error, then report |

## Notes

- Self-thread = consecutive replies by the same author to their own tweet.
- Never send API calls with the session token yourself; only read responses the page loads.


## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
