---
name: reddit-explorer
description: Explore Reddit trading communities (r/RealDayTrading, r/Daytrading, r/algotrading, r/options, r/stocks, r/vietnamstocks…) — search posts and subreddits, list hot/new/top posts, read full threads with every comment level, read user histories, and store threads as FinSocNet content. Use for reddit.com links, r/ and u/ names, "what does Reddit say about …".
license: MIT
compatibility: FinSocNet repository, agent-browser running (JSON endpoints are loaded through it); reddit session optional.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Reddit Explorer

Uses Reddit's `.json` endpoints loaded through the agent browser, so cookies and proxy apply. Keeps every comment up to the cap (default 500, highest score first) and warns when the cap is hit.

## When to use

- reddit.com / redd.it URLs, `r/<sub>`, `u/<user>`, community sentiment and experience threads.

## Before you start

- Agent browser running. Session optional (needed for private/quarantined subs).
- Session `reddit` (optional): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform reddit`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/reddit-explorer/scripts/reddit.py
uv run $S search "<query>" [--subreddit S] [--type posts|sr] [--sort relevance|top|new] [--t all|year|month] [--limit 100]
uv run $S profile <r/sub|u/user|url> [--ingest]
uv run $S list <r/sub|u/user> [--sort hot|new|top|rising] [--t …] [--kind posts|comments] [--limit 100] [--cursor C] [--save-cursor] [--enqueue]
uv run $S fetch <thread url|post id> [--max-comments 500] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | ItemRef[] |
| `profile <r/sub|u/user|url>` | about data |
| `list <r/sub|u/user>` | posts; cursor = `after` token |
| `fetch <thread url|post id>` | post + comment tree |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill reddit-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Community: `profile r/<sub> --ingest`, `list r/<sub> --sort top --t year --enqueue --save-cursor --run R`.
3. Thread: `fetch <url> --ingest --run R` → `market-idea-miner`.
4. Prolific user (e.g. a mentor in a sub): `list u/<user> --kind comments` → person-matcher.
5. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
6. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `reddit:<post_id36>` |
| source id | `reddit:subreddit:<name>` / `reddit:user:<name>` (lowercase) |
| content_type | `thread` |
| segments | post `kind=post` `{comment_id: t3_<id>}`; comments `kind=comment` `{comment_id: t1_<id>, parent_id, score, depth}`, author per segment |
| deleted | kept with text `[deleted]` (not quotable) |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill reddit-explorer --kind script_bug …` with the error, then report |

## Notes

- `more` stubs expanded with `/api/morechildren.json` until the cap.
- Remove the v1 `--host-resolver-rules` DNS hack.

## Legacy commands (v1 names; thin wrappers until Phase 8)

```bash
uv run .agents/skills/reddit-explorer/scripts/explore_community.py "RealDayTrading" --sort hot --limit 5
uv run .agents/skills/reddit-explorer/scripts/search_reddit.py "<query>" --limit 5
uv run .agents/skills/reddit-explorer/scripts/read_thread.py "<thread url>"
# login_reddit.py is superseded by session-bridge (Phase 3)
```

The v1 names call the v2 adapter (`--ingest-db` maps to `--ingest`); use the new subcommands in new work.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/trading_subreddits.md` — curated list of trading subreddits
