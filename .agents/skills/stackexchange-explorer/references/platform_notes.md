# Stack Exchange Explorer (incl. Stack Overflow) — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `/2.3/search/advanced?site=&q=&sort=votes&filter=withbody`
- `/2.3/questions/<id>?filter=withbody`
- `/2.3/questions/<id>/answers?filter=withbody&sort=votes&pagesize=100`
- `/2.3/posts/<ids>/comments?filter=withbody`
- `/2.3/users/<id>`, `/users/<id>/answers`, `/users/<id>/top-answer-tags`

## Verify in the Phase spike

- (nothing open)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: `/search/advanced`, `/questions/<id>`, `/questions/<id>/answers`, `/users/<id>` with `filter=withbody`; quota 300/day without a key. Fixtures in `tests/fixtures/stackexchange/`.
