# Trading Forum Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- Discourse `/latest.json`, `/c/<slug>/<id>.json`, `/t/<id>.json`, `/t/<id>/posts.json?post_ids[]=`, `/search.json?q=`, `/u/<user>.json`
- XenForo `/forums/<slug>.<id>/page-N`, `/threads/<slug>.<id>/page-N`, `article.message`, `.bbWrapper`

## Verify in the Phase spike

- [ ] engine of each initial forum
- [ ] F319 page structure and encoding

## Change log

| Date | Change | Lesson |
|---|---|---|
