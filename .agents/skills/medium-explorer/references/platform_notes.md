# Medium Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://medium.com/feed/@<handle>`, `/feed/<publication>`, `/feed/tag/<tag>`
- search page `https://medium.com/search?q=`
- article page rendered + trafilatura

## Verify in the Phase spike

- [ ] member-only full text with member session

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Plain HTTP to `medium.com/feed/@user` returned an HTML page (bot protection) from this network, so `list` may need the browser path. NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here.
