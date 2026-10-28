# Bluesky Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile`
- `app.bsky.feed.getAuthorFeed`
- `app.bsky.feed.getPostThread`
- `app.bsky.feed.searchPosts`

## Verify in the Phase spike

- [ ] whether searchPosts needs auth

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: `getProfile`, `getAuthorFeed`, `getPostThread` work on the public AppView. `searchPosts` answers **403** without authentication, so `search` exits 3 with a hint (use web-searcher `--site bsky.app`).
