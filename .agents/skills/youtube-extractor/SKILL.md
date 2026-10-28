---
name: youtube-extractor
description: Catalog YouTube channels (videos, shorts, live streams), read video metadata and full transcripts with timestamps (manual or auto captions, local Whisper fallback), search YouTube, and store everything as FinSocNet content. Use for YouTube URLs, @handles, channel ids, "get the transcript of …", "list all videos from …", "find YouTube videos about …", trader interviews and livestreams.
license: MIT
compatibility: FinSocNet repository with uv, yt-dlp, youtube-transcript-api; audio-transcriber for videos without captions; optional data/sessions/cookies.txt from session-bridge.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: specs/05-platform-skills.md
---

# YouTube Extractor

Turns YouTube into FinSocNet content. Captions first, Whisper only when no captions exist. Uses the imported cookies file when present, which avoids "confirm you're not a bot" blocks on server IPs and unlocks members-only videos.

## When to use

- A YouTube video, short, live stream or channel URL / @handle / channel id.
- "Transcript of this video", "all videos of this channel", "YouTube interviews with <trader>".

## Before you start

- None for public videos. `data/sessions/cookies.txt` (session-bridge) is used automatically when present.

## Commands

```bash
S=.agents/skills/youtube-extractor/scripts/youtube.py
uv run $S search "<query>" [--limit 20] [--type video|channel]
uv run $S profile <@handle|channel url|UC…> [--ingest]
uv run $S list <channel> [--tab videos|shorts|streams|all] [--limit 50] [--since YYYY-MM-DD] [--save-cursor] [--enqueue]
uv run $S fetch <url|video_id> [--ingest] [--force-whisper]
```

| Command | Returns |
|---|---|
| `search "<query>"` | ItemRef[] via yt-dlp ytsearch |
| `profile <@handle|channel url|UC…>` | ProfileRecord: title, description, links, subscribers, channel id |
| `list <channel>` | newest first; cursor = last seen video id |
| `fetch <url|video_id>` | ContentRecord with transcript segments |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill youtube-extractor --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Channel: `profile --ingest` → `person-matcher` on the channel owner → `list --tab all --enqueue --save-cursor --run R`.
3. Video: `fetch <url> --ingest --run R` → then `market-idea-miner` on the returned content id.
4. If `extra.caption_source` is `auto` and the transcript looks garbled (many `[Music]`, wrong language), refetch with `--force-whisper`.
5. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
6. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `youtube:<videoId>` (11 chars) |
| source id | `youtube:channel:<UC…>` |
| content_type | `video`, `short`, `stream` |
| segments | caption lines merged into windows ≤ 45 s / ≤ 600 chars; `kind=transcript`, `locator={start_sec,end_sec}` |
| extra | `caption_source` (manual/auto/whisper), `caption_lang`, `chapters`, `long_form` (> 3 h) |
| links / mentions | URLs, @handles, $TICKERS from the description |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill youtube-extractor --kind script_bug …` with the error, then report |

## Notes

- Caption order: manual original language → manual en → auto original → auto en → Whisper.
- Streams longer than 3 h are still fully transcribed (nothing ignored).


## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/extraction_notes.md` — caption and yt-dlp notes from v1
