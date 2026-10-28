# StockTwits Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://api.stocktwits.com/api/2/streams/symbol/<SYM>.json`
- `/streams/user/<name>.json`

## Verify in the Phase spike

- [ ] public API still open

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: plain HTTP to `api.stocktwits.com` answers **403**; the adapter therefore loads the JSON endpoints through the agent browser. NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here.
