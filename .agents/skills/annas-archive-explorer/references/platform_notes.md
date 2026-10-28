# Anna's Archive Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- search page `https://annas-archive.gl/search?q=`
- `/md5/<md5>` details

## Verify in the Phase spike

- [ ] current mirror domain
- [ ] download flow through agent browser

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. DDoS-Guard clearance is kept in the agent browser profile; `download` stays an explicit, user-initiated call.
