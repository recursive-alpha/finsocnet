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

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. Engines: Discourse JSON, XenForo HTML, generic fallback (first page only). `config/forums.yaml` lists the known forums; engines are to be confirmed with `forum.py detect <url>`.

## Live check 2026-10-28

Discourse board `https://meta.discourse.org/c/support/6` lists and fetches through the agent browser. Hosts not in `config/forums.yaml` are detected from the page (`detect_engine`) on `list`. A host that does not resolve returns `NOT_FOUND` (exit 5); `browser.goto` maps navigation errors to the envelope.
