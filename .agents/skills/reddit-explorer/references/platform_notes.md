# Reddit Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `/r/<sub>/<sort>.json?limit=100&after=`
- `/comments/<id>.json?limit=500&depth=10&sort=top&raw_json=1`
- `/api/morechildren.json`
- `/search.json`, `/r/<sub>/search.json?restrict_sr=1`, `/subreddits/search.json`
- `/user/<u>/about.json`, `/submitted.json`, `/comments.json`
- `/api/me.json` (login probe)

## Verify in the Phase spike

- [ ] unauthenticated access from the remote IP
- [ ] morechildren via browser

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Plain HTTP to `www.reddit.com/*.json` answers **403** from this network, so every call goes through the agent browser. NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here.

## RSS fallback (verified 2026-10-28)

From a server IP, `www.reddit.com/*.json` returns "You've been blocked by network security", also inside the agent browser. `*.rss` (Atom) answers 200 to a browser user agent, but 429 when polled quickly (use `retry_after_sec`).
The adapter tries JSON through the agent browser first and falls back to RSS on `CHECKPOINT`. RSS gives subreddit/user listings, search, and a thread's post plus the first comments; such records carry `fetch_method: rss` and `extra.partial: true`, so do not treat missing comments as absent discussion.
`tests/fixtures/reddit/thread.rss` is hand-written in the Atom shape Reddit returns, not a live capture.
