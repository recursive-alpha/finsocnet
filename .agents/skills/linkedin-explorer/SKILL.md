---
name: linkedin-explorer
description: Read LinkedIn posts and articles of known fund managers, analysts and traders with the user's imported session, and store them as FinSocNet content. Use for linkedin.com/in, /posts or /pulse links of persons already in the database. Strictest budget; no broad crawling.
license: MIT
compatibility: FinSocNet repository, agent-browser, imported linkedin.com session.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: ready
  phase: "7"
  spec: specs/05-platform-skills.md
---

# LinkedIn Explorer

**Risk:** LinkedIn restricts automated accounts aggressively. Only profiles of persons already known; ~20 pages/hour; stop at the first checkpoint. Enabled after the user accepts the risk.

## When to use

- LinkedIn profile/post/article of a known person.

## Before you start

- Session logged_in; user accepted the risk.
- Session `linkedin` (required): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform linkedin`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/linkedin-explorer/scripts/linkedin.py
uv run $S profile <profile url> [--ingest]
uv run $S list <profile url> [--limit 30] [--enqueue]
uv run $S fetch <post|article url> [--ingest]
```

| Command | Returns |
|---|---|
| `profile <profile url>` | headline, about, experience summary |
| `list <profile url>` | recent posts/articles |
| `fetch <post|article url>` | text + top comments |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill linkedin-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Only for persons already in `persons`: profile → list → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `linkedin:<activity_urn>`, `linkedin:article:<slug>` |
| source id | `linkedin:user:<vanity>` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill linkedin-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
