# Substack Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://<pub>/api/v1/archive?sort=new&offset=&limit=50`
- `https://<pub>/api/v1/posts/<slug>`
- `https://<pub>/api/v1/post/<id>/comments?all_comments=true&sort=best_first`
- `https://substack.com/api/v1/publication/search?query=&page=0`
- `https://substack.com/api/v1/user/<handle>/public_profile`
- Notes: `https://substack.com/api/v1/reader/feed/profile/<user_id>`

## Verify in the Phase spike

- [ ] all endpoints above
- [ ] post search endpoint (fallback: google-searcher `site:substack.com`)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: `/api/v1/archive`, `/api/v1/posts/<slug>`, `/api/v1/post/<id>/comments` on a public publication. `substack.com/api/v1/publication/search` returned an empty list; `/api/v1/publication` answered 403. Paid posts: `audience` is `only_paid` and the body is truncated (flagged `extra.truncated`).
