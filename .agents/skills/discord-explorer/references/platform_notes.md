# Discord Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- client REST responses `GET /api/v9/channels/<id>/messages?before=&limit=50` (captured, not sent)
- `GET /api/v9/guilds/<id>/messages/search?content=` (captured from in-app search)
- bot mode: official API with bot token

## Verify in the Phase spike

- [ ] localStorage token key for session import
- [ ] DOM selectors for sidebar and channel list

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. User mode reads the client's own REST responses (`/api/v*/channels/<id>/messages`); bot mode (official API) is the supported route for servers you administer. In-app search is not implemented.
