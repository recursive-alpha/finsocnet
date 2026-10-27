---
name: youtube-extractor
description: Extract YouTube video transcripts with precise timestamps, fetch video metadata, and catalog channel uploads. Includes automated fallback to local openai/whisper-large-v3-turbo when captions are unavailable.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# YouTube Extractor

Extract transcripts, video metadata, and channel catalogs from YouTube for analysis, summarization, and knowledge mining.

## Capabilities
1. **Video Transcripts:** Fetch full word-for-word transcripts with second-level timestamps (`[MM:SS] (XXX.Xs)`).
2. **Video Metadata:** Extract title, channel ID, duration, description, view count, and tags.
3. **Channel Discovery:** Enumerate latest or most popular videos from any creator handle (`@handle`), channel ID (`UC...`), or URL.

## Workflow

### 1. Extract a Video Transcript
Run the extraction script with a video URL or 11-character video ID:

```bash
uv run .agents/skills/youtube-extractor/scripts/extract_transcript.py "https://www.youtube.com/watch?v=zU0i9rBbEkI"
```

Outputs created in `data/transcripts/`:
- `<video_id>.json`: Complete structured JSON (metadata + snippets with `start`, `duration`, `text`).
- `<video_id>.txt`: Formatted transcript grouped into coherent ~20s blocks with timestamp headers.

To print directly to terminal:
```bash
uv run .agents/skills/youtube-extractor/scripts/extract_transcript.py <video_id> --print --limit-lines 30
```

### Fallback to Local Whisper
- `--force-whisper`: Bypass YouTube captions and transcribe using local `openai/whisper-large-v3-turbo`.
- Automatic fallback: If YouTube subtitles are missing, `extract_transcript.py` automatically downloads the audio track and invokes the local Whisper transcriber.

### 2. Explore a Creator Channel
Catalog videos for any channel handle or URL:

```bash
uv run .agents/skills/youtube-extractor/scripts/explore_channel.py "@HumbledTraderOfficial" --limit 20 --sort latest --save-json data/channels/humbled_trader.json
```

Options:
- `--limit <N>`: Number of entries to inspect (default: 0 for all).
- `--tab <all|videos|shorts|streams|playlists>`: Channel tab to explore (default: `all` captures long-form videos, shorts, and live streams).
- `--sort <latest|popular>`: Sort order.
- `--save-json <path>`: Save video list for downstream batch mining.

## References
See [references/extraction_notes.md](references/extraction_notes.md) for details on fallback transcript mechanisms and channel URL normalization.
