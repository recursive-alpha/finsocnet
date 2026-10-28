---
name: audio-transcriber
description: Transcribe speech to timestamped text with local Whisper (openai/whisper-large-v3-turbo, int8) from a local audio/video file or any yt-dlp-supported URL — YouTube, podcast enclosures, Twitch VODs, Vimeo, Rumble, Kick, X/TikTok/Instagram videos. Use when a platform has no captions, for podcasts and livestreams, or when the user asks to "transcribe" a recording.
license: MIT
compatibility: FinSocNet repository with uv, faster-whisper, yt-dlp and ffmpeg; GPU optional (WHISPER_DEVICE=auto).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Audio Transcriber

The only model FinSocNet scripts run (ADR-002 exception: speech-to-text, not reasoning). Other skills call it and build their own ContentRecord from its segments.

## When to use

- A platform skill reports no captions/transcript.
- "Transcribe this audio/video/podcast/livestream".

## Before you start

- ffmpeg installed. Whisper model downloads on first use (~1.6 GB).

## Commands

```bash
S=.agents/skills/audio-transcriber/scripts/transcribe.py
uv run $S transcribe <url-or-path> [--language auto|en|vi|…] [--content-id ID]
uv run $S transcribe <url> --cookies
```

| Command | Returns |
|---|---|
| `transcribe <url-or-path>` | `{segments:[{start_sec,end_sec,text}], language, model, duration_sec, cache_path}` |
| `transcribe <url> --cookies` | use data/sessions/cookies.txt for gated media |

Not a platform adapter: it returns segments and does not write to the database itself. Output is the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. Called by another skill: run `transcribe`; the caller merges segments into ≤ 45 s windows and stores its own ContentRecord.
2. User asks to transcribe a URL: run the matching platform skill's `fetch --ingest` instead (it calls this skill and stores the result). A local recording: `document-reader fetch <path> --ingest --run R` (it calls this skill). The cache means the audio is transcribed only once.

## Stored as

| Field | Value |
|---|---|
| cache | `data/transcripts/<sha256(audio)[:16]>.json` — same audio is never transcribed twice |
| output | segments with `start_sec`, `end_sec`, `text`; language detected |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill audio-transcriber --kind script_bug …` with the error, then report |

## Notes

- VAD filter on, `word_timestamps=False`.
- `--diarize` (speaker labels via whisperX/pyannote) is a later option, not part of v2.

## Legacy commands (v1 names; thin wrappers until Phase 8)

```bash
```

The v1 names call the v2 adapter (`--ingest-db` maps to `--ingest`); use the new subcommands in new work.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/model_guide.md` — Whisper model, device and compute type
