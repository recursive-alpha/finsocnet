# TikTok Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- profile page scroll
- yt-dlp TikTok extractor

## Verify in the Phase spike

- [ ] yt-dlp TikTok extraction from the remote IP

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

yt-dlp metadata and Whisper on the audio; the parser is covered by a synthetic yt-dlp info dict. Profile listing relies on yt-dlp's TikTok extractor, which changes often.
