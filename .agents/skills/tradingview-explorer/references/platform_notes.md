# TradingView Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://www.tradingview.com/ideas/search/<q>/`
- `https://www.tradingview.com/scripts/search/<q>/`
- `/u/<user>/`, `/symbols/<EXCH>-<SYM>/ideas/`

## Verify in the Phase spike

- [ ] search URLs
- [ ] where the Pine source is in the page

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. Idea/script URLs, JSON-LD and Open Graph tags are used first; Pine source is only available for open-source scripts.
