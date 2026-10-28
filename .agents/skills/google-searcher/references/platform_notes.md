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
