# Web Reader — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `core.browser.page()` + `wait_until=networkidle` (cap BROWSER_TIMEOUT_MS)
- `trafilatura.extract(html, output_format='markdown', include_comments=True, include_tables=True)`

## Verify in the Phase spike

- [ ] extraction quality on 10 trader blogs

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified with the real agent browser on a local page (render, trafilatura extraction, discovery). trafilatura output falls back to DOM text under 200 characters.
