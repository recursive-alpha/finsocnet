# Hacker News Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://hn.algolia.com/api/v1/search?query=&tags=story`
- `https://hn.algolia.com/api/v1/items/<id>`

## Verify in the Phase spike

- (nothing open)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: Algolia `/search`, `/items/<id>`, `/users/<name>` answer to plain HTTP; fixtures in `tests/fixtures/hackernews/`. Content ids use `hn:<id>` (platform key `hackernews`).
