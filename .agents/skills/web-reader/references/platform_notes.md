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
