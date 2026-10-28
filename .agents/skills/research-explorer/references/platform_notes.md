# Research Explorer (SSRN, NBER, OpenAlex, Semantic Scholar) — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `https://api.openalex.org/works?search=&mailto=`
- `https://api.semanticscholar.org/graph/v1/paper/search?query=&fields=title,abstract,authors,year,openAccessPdf,externalIds`
- SSRN search page (browser)

## Verify in the Phase spike

- [ ] SSRN download behaviour

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: OpenAlex `/works?search=` (abstract comes as `abstract_inverted_index`). Semantic Scholar answered **429** without a key; use `--provider s2` sparingly. SSRN search is not implemented (needs the browser).
