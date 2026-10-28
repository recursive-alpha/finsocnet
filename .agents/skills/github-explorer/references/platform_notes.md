# GitHub Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `/search/repositories`
- `/repos/<o>/<r>/readme`
- `/repos/<o>/<r>/git/trees/<branch>?recursive=1`
- `/repos/<o>/<r>/contents/<path>`

## Verify in the Phase spike

- (nothing open)

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

Verified live on 2026-10-28: search, repo, readme, user, git tree. 60 requests/hour without `GITHUB_TOKEN`.
