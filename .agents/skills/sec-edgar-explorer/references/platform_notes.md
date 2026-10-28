# SEC EDGAR Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://data.sec.gov/submissions/CIK<cik10>.json`
- full-text search `https://efts.sec.gov/LATEST/search-index?q=&forms=`
- 13F `informationTable` XML in the filing index

## Verify in the Phase spike

- [ ] full-text search endpoint and params

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: `data.sec.gov/submissions/CIK<cik10>.json` with a contact User-Agent. Full-text search (`efts`) and the 13F information-table path are written from the documentation and **not** verified.
