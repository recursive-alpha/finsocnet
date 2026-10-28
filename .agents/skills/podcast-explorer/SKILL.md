---
name: podcast-explorer
description: Find and ingest podcasts on any topic (finance examples such as Chat With Traders, Market Wizards-style interviews, macro shows) — search the Apple Podcasts directory, read show RSS feeds, list episodes, and get transcripts from Podcasting 2.0 transcript tags, a matching YouTube upload, or local Whisper. Use for podcast names, Apple Podcasts links, RSS feeds, "interviews with <trader>", or guest appearances.
license: MIT
compatibility: FinSocNet repository, feedparser, audio-transcriber; youtube-extractor for cross-posted episodes.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: specs/05-platform-skills.md
---

# Podcast Explorer

Cheapest transcript first: published transcript → same episode on YouTube (captions) → Whisper. Guest names parsed from titles are hints only; person-matcher confirms.

## When to use

- Podcast shows, episodes, guest interviews.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/podcast-explorer/scripts/podcast.py
uv run $S search "<query>" [--episodes] [--limit 20]
uv run $S profile <feed url|apple url> [--ingest]
uv run $S list <feed url|apple url> [--limit 100] [--since D] [--save-cursor] [--enqueue]
uv run $S fetch <episode guid|enclosure url|episode page> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | shows (or episodes) from the iTunes Search API |
| `profile <feed url|apple url>` | show title, author, description, links |
| `list <feed url|apple url>` | episodes newest first; cursor = last guid |
| `fetch <episode guid|enclosure url|episode page>` | episode with transcript segments |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill podcast-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Show: `profile --ingest` → `list --enqueue --save-cursor --run R`.
3. Episode: `fetch --ingest --run R` → person-matcher (host + guests from `extra.guests_hint`) → market-idea-miner.
4. If the fetch says it used a YouTube duplicate, the episode is linked with `duplicate_of`; mine the YouTube content instead.
5. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
6. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `podcast:<sha1(feed_url)[:12]>:<sha1(guid)[:12]>` |
| source id | `podcast:feed:<sha1(feed_url)[:12]>` |
| content_type | `episode` |
| segments | `transcript` windows `{start_sec,end_sec}` |
| extra | `guests_hint`, `show`, `transcript_source` (podcast2|youtube|whisper) |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill podcast-explorer --kind script_bug …` with the error, then report |

## Notes

- Spotify-exclusive shows are DRM-protected: record the source with `status='blocked'`.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
