---
name: medium-explorer
description: Explore Medium for trading, quant and finance writing — tags, authors, publications and full articles including member-only stories with an imported member session — and store articles as FinSocNet content. Use for medium.com links, @authors, Medium publications such as Towards Data Science, "find Medium articles about backtesting / algorithmic trading".
license: MIT
compatibility: FinSocNet repository, agent-browser running; medium session optional.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: specs/05-platform-skills.md
---

# Medium Explorer

RSS for listing (fast, recent items), the agent browser for search, profiles, full history and article text.

## When to use

- medium.com URLs, @authors, publications, tags like `algorithmic-trading`, `quantitative-finance`.

## Before you start

- Agent browser running; member session for member-only stories.
- Session `medium` (optional, member-only stories): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform medium`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/medium-explorer/scripts/medium.py
uv run $S search "<query>" [--limit 20]
uv run $S profile <@author|publication|url> [--ingest]
uv run $S list <@author|publication|tag/<t>> [--full] [--limit 50] [--enqueue]
uv run $S fetch <article url> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | articles via Medium search page |
| `profile <@author|publication|url>` | author/publication about |
| `list <@author|publication|tag/<t>>` | RSS by default; `--full` scrolls the page for full history |
| `fetch <article url>` | article paragraphs and code blocks |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill medium-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Author: `profile --ingest` → person-matcher → `list --full --enqueue --run R`.
3. Article: `fetch --ingest --run R` → market-idea-miner. If the result has warning `truncated: true`, the story is member-only and the session is not a member: tell the user.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `medium:<12-hex post id>` |
| source id | `medium:user:<handle>`, `medium:publication:<slug>`, `medium:tag:<tag>` |
| content_type | `article` |
| segments | paragraphs `{para}`, code blocks `kind=code` |
| extra | `member_only`, `claps`, `reading_time_min`, `truncated` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill medium-explorer --kind script_bug …` with the error, then report |

## Notes

- RSS returns only the latest ~10 items; use `--full` for history.


## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/medium_topics.md` — useful tags and publications
