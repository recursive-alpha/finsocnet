---
name: google-searcher
description: Search Google (web and news) through the agent browser with the user's Google session, using advanced operators (site:, inurl:, intitle:, filetype:, date ranges) to find creator discussions, interviews, PDFs, forum threads and Facebook/Substack/Discord pages that DuckDuckGo misses. Use when web-searcher results are thin, for operator-heavy queries, Google News, or gap exploration.
license: MIT
compatibility: FinSocNet repository, agent-browser running; google session optional.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: planned
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Google Searcher

> **Status: planned — built in Phase 4.** Nothing below runs yet; it is the contract the implementation must follow.

Strict budget (Google CAPTCHAs quickly). Use web-searcher first unless you need Google-only operators or coverage.

## When to use

- Operator queries like `site:facebook.com/groups "breakout trading"`, `filetype:pdf`, Google News.

## Before you start

- Agent browser running.
- Session `google` (optional): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform google`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/google-searcher/scripts/google.py
uv run $S search "<query with operators>" [--news] [--since YYYY-MM-DD] [--limit 50]
```

| Command | Returns |
|---|---|
| `search "<query with operators>"` | organic results (ads ignored) as ItemRef[] |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

Implements only `search` of the adapter contract; other subcommands exit 2 `UNSUPPORTED`.

## Procedure

1. `uv run finsocnet kb run start --skill google-searcher --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Run the search, judge results, enqueue promising ones with a reason and priority.
3. `CHECKPOINT` (Google /sorry/) → stop Google for this run; continue with web-searcher.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| ids | `web:<sha1(canonical_url)[:16]>` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill google-searcher --kind script_bug …` with the error, then report |

## Notes

- No fetch; use dispatch rules for results.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
