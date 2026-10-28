---
name: facebook-explorer
description: Read Facebook trading groups and pages through the agent browser with the user's imported session — group and page about info, feeds, posts with expanded text, comments and replies, and video posts transcribed with Whisper — and store them as FinSocNet content. Use for facebook.com/groups or page links, fb.watch videos, "what do <group> members say about …", including Vietnamese stock groups.
license: MIT
compatibility: FinSocNet repository, agent-browser running, imported facebook.com session; yt-dlp + audio-transcriber for videos.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Facebook Explorer

**Risk:** Facebook bans automated personal accounts; use a secondary account, strict budget (`facebook` in budgets.yaml), and stop at the first checkpoint. Enabled only after the user accepts the risk (SPEC §9 Q2).

## When to use

- Facebook group/page/post/video URLs.

## Before you start

- User accepted the risk; session logged_in; ideally SOCKS egress via the user's home IP.
- Session `facebook` (required): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform facebook`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/facebook-explorer/scripts/facebook.py
uv run $S search "<query>" [--groups|--posts] [--limit 30]
uv run $S profile <group|page url> [--ingest]
uv run $S list <group|page url> [--limit 50] [--enqueue]
uv run $S fetch <post permalink> [--max-comments 200] [--transcribe-video] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | groups or posts |
| `profile <group|page url>` | name, members, privacy, description |
| `list <group|page url>` | post permalinks from the feed |
| `fetch <post permalink>` | post + comments |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill facebook-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Group: `profile --ingest` → `list --enqueue --run R` (small batches) → fetch posts → market-idea-miner.
3. Any `CHECKPOINT` → stop Facebook entirely for the day and tell the user.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `facebook:<group_or_page_id>:<post_id>` |
| source id | `facebook:group:<id>`, `facebook:page:<id>` |
| content_type | `post` |
| segments | post `kind=post`; comments `kind=comment {comment_id, parent_id?}` |
| persons | members of private groups → `private_source` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill facebook-explorer --kind script_bug …` with the error, then report |

## Notes

- mbasic.facebook.com is gone; use www with GraphQL capture and DOM fallback.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
