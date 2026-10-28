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
