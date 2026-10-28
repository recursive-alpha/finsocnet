# Paper & Code Explorer (arXiv) — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `http://export.arxiv.org/api/query?search_query=`
- Hugging Face papers API

## Verify in the Phase spike

- (nothing open)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: Hugging Face `GET /api/papers/search?q=` and `/api/daily_papers` (the old `/api/papers?q=` no longer returns the same shape); `/api/papers/<id>` gives `githubRepo`. The arXiv API answered **429** ("Rate exceeded") from this network, so `fetch` may exit 4; its fixture `arxiv.xml` is hand-written in the live Atom shape.
