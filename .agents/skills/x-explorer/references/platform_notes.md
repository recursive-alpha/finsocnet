# X (Twitter) Explorer — platform notes

Implementation details for the adapter. Update this file (and add `kb lesson add --kind platform_change`) whenever an endpoint, selector or limit changes.

## Endpoints and methods

- `/i/api/graphql/*/SearchTimeline`
- `/i/api/graphql/*/UserTweets`, `UserTweetsAndReplies`
- `/i/api/graphql/*/TweetDetail`
- `/i/api/graphql/*/UserByScreenName`

## Verify in the Phase spike

- [ ] operation names still current
- [ ] note-tweet full text field
- [ ] rate-limit behaviour at the configured budget

## Change log

| Date | Change | Lesson |
|---|---|---|

## Phase 4 implementation notes (2026-10-28)

NOT verified live (hand-written fixtures in the documented shape); check selectors/endpoints on the first real run and correct them here. The parser walks the GraphQL JSON recursively (tweets are any object with `rest_id` + `legacy`), so it tolerates changed query ids and nesting.
