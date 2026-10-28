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
