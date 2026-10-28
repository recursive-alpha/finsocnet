---
name: substack-explorer
description: Explore Substack newsletters on trading, macro and investing — search publications, read author profiles, list a publication's archive, read full posts (including paid posts with the user's subscription session), comments, Substack Notes and Substack podcast episodes, and store them as FinSocNet content. Use for *.substack.com links, custom-domain Substack newsletters, "newsletters about …".
license: MIT
compatibility: FinSocNet repository, agent-browser running; substack session optional.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: planned
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Substack Explorer

> **Status: planned — built in Phase 4.** Nothing below runs yet; it is the contract the implementation must follow.

Uses Substack's JSON endpoints through the agent browser (cookies apply). The endpoints are unofficial: if one changes, record it in `references/platform_notes.md` and add a lesson.

## When to use

- Substack publication or post URLs, newsletter authors, Substack Notes.

## Before you start

- Agent browser running; subscription session for paid posts.
- Session `substack` (optional, paid posts): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform substack`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/substack-explorer/scripts/substack.py
uv run $S search "<query>" [--posts] [--limit 20]
uv run $S profile <pub url|@author> [--ingest]
uv run $S list <pub url> [--limit 50] [--cursor offset] [--save-cursor] [--enqueue]
uv run $S fetch <post url> [--comments] [--notes] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | publications (or posts) |
| `profile <pub url|@author>` | publication/author profile |
| `list <pub url>` | archive newest first |
| `fetch <post url>` | post paragraphs (+ comments) |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill substack-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Newsletter: `profile --ingest` → person-matcher → `list --enqueue --save-cursor --run R`.
3. Post: `fetch --comments --ingest --run R` → market-idea-miner. Warning `truncated: true` = paid post without subscription; tell the user.
4. Podcast posts: audio goes through audio-transcriber automatically.
5. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
6. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `substack:<pub_subdomain>:<post_id>` |
| source id | `substack:publication:<subdomain>` |
| content_type | `article` or `episode` |
| segments | paragraphs `{para}`, comments `kind=comment {comment_id}` |
| extra | `audience` (everyone/only_paid/founding), `truncated` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill substack-explorer --kind script_bug …` with the error, then report |

## Notes

- Custom domains map to the publication's subdomain from the API.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
