# Extraction Notes & Fallbacks

## YouTube Transcript Fetching
1. **Primary method:** `youtube-transcript-api` (uses internal YouTube innertube API, fast, retrieves timed snippets).
2. **Fallback method:** `yt-dlp --write-auto-sub --sub-lang en --skip-download` if API limits or anti-bot blocks occur.

## Channel Tab Conventions
- `@handle/videos`: Standard long-form uploads.
- `@handle/shorts`: Short-form vertical videos.
- `@handle/streams`: Past live streams and Q&A sessions.
- Sort options: `latest` (default chronological) or `popular` (`?view=0&sort=p`).

## Storage Layout
- Video JSON: `data/transcripts/<video_id>.json` (contains metadata + full raw snippet array).
- Video Text: `data/transcripts/<video_id>.txt` (grouped human/agent-readable blocks with `[MM:SS]` timestamps).
- Channel Catalogs: `data/channels/<channel_id_or_handle>.json`.
