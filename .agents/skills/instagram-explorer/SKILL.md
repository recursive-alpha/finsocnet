---
name: instagram-explorer
description: Explore Instagram trading creators with the user's imported session — profiles, posts with captions and comments, reels transcribed with Whisper — and store them as FinSocNet content. Use for instagram.com profile, post or reel links.
license: MIT
compatibility: FinSocNet repository, agent-browser, imported instagram.com session, yt-dlp + audio-transcriber.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P3"
  status: ready
  phase: "7"
  spec: docs/spec/05-platform-skills.md
---

# Instagram Explorer

Strict budget; Instagram flags automation quickly. Secondary account recommended.

## When to use

- Instagram profiles, posts, reels.

## Before you start

- Session logged_in.
- Session `instagram` (required): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform instagram`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/instagram-explorer/scripts/instagram.py
uv run $S profile <handle> [--ingest]
uv run $S list <handle> [--limit 50] [--enqueue]
uv run $S fetch <post|reel url> [--max-comments 100] [--ingest]
```

| Command | Returns |
|---|---|
| `profile <handle>` | bio, followers, links |
| `list <handle>` | posts and reels |
| `fetch <post|reel url>` | caption, comments, transcript for reels |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill instagram-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. profile → person-matcher → list → fetch → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `instagram:<shortcode>` |
| source id | `instagram:user:<handle>` |
| segments | caption `post`; comments; reel transcript windows |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill instagram-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
