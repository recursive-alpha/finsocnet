# Google Searcher — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://www.google.com/search?q=&num=&hl=en`
- News: `tbm=nws`; date: `tbs=cdr:1,cd_min:MM/DD/YYYY`

## Verify in the Phase spike

- [ ] result selectors
- [ ] checkpoint detection on /sorry/

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. Result parsing keys on `a > h3` inside `#search`/`#rso`; ads (`#tads`, `data-text-ad`) are skipped. `/sorry/` pages exit 3.
