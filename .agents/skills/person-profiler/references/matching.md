# Is this account really them?

Signals, strongest first:

1. **Reciprocal link**: the person's own site/channel links to the account, or the account's bio/website links to the person's site/channel. Strong (0.9–1.0).
2. **Their own content says so**: a video description, newsletter footer, book "about the author", or a post introducing the handle. Strong.
3. **Platform verification** (blue check, verified channel, official-artist badge) with the same name. Medium-strong.
4. **Consistent facts**: same employer, city, years of activity, topics, signature phrases, follower scale plausible for who they are. Medium; needs a second signal.
5. **Same picture**: compare the stored avatar with the candidate's. Medium; stock photos and logos prove nothing.
6. **Name only**: weak. Never enough.

Red flags (do not store, or `needs_review` with the doubt written down):
- the account was created recently and has few posts but copies the person's brand;
- "fan", "tribute", "quotes", "archive", "wisdom", "official ❌" accounts (an archive of someone's quotes is not the person: a source with `role: archive` at most);
- a placeholder newsletter or channel with one "coming soon" post and no link from the person;
- the bio sells signals, courses or crypto under the person's name without a link from the person's own channels;
- a different person with the same name (check employer, country, field).

Write the doubt: `"evidence": "name and topic match, no cross-link; created 2024, one post"` and `needs_review`.
