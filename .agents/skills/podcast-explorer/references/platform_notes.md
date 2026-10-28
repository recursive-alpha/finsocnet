# Podcast Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://itunes.apple.com/search?media=podcast&entity=podcast&term=`
- `…&entity=podcastEpisode`
- `https://itunes.apple.com/lookup?id=<id>` → `feedUrl`
- RSS `<podcast:transcript>` (VTT/SRT/JSON)

## Verify in the Phase spike

- [ ] YouTube duplicate match rule (title + duration ±3%)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: iTunes Search API and a real show feed (`feeds.megaphone.fm`). Podcasting 2.0 `<podcast:transcript>` handling (VTT, SRT, JSON) is covered by unit tests only; the sample feed has no transcript tags.
