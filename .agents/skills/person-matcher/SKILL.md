---
name: person-matcher
description: Resolve who is speaking or writing — match channel owners, podcast hosts and guests, authors, commenters and handles across YouTube, X, Reddit, Discord, Substack, forums, books and papers to one canonical person, with aliases, appearances, confidence and a review queue. Use before mining content, when a new creator or guest appears, when the user asks "who is this trader", "is this the same person as …", "merge these people", or to review uncertain matches.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "2"
  spec: specs/03-pipelines.md
---

# Person Matcher

Knowledge belongs to people, not channels. One person can own a YouTube channel, guest on podcasts, post on X and write a book; all of it resolves to one `persons` row.

## Procedure: identify the cast of a content item

1. Gather evidence: title ("ft.", "with", "×", "interview", "|"), description, `source.person_id` (channel owner), byline, the first 3–5 segments (self-introductions "I'm …", host introductions "my guest today is …"), profile bio links.
2. For each name or handle: `uv run finsocnet kb person candidates --name "<name>" --handle "<handle>" --platform <p> --context "<title + description>"` → candidates with `score` and `reasons`.
3. Decide:
   - score ≥ 0.9 and evidence consistent → confirm.
   - 0.6–0.9 → confirm only with a second independent signal (e.g. the guest's X handle in the description **and** the name in the title).
   - otherwise → create a new person **only if** they state knowledge in this content or own a crawled source; else skip.
4. New person → write `person.json` and `kb person upsert --file person.json --run R`:
   ```json
   {"id": "example-guest", "canonical_name": "Example Guest", "moniker": "ExampleG",
    "bio": "Prop trader since 2012; runs a small-cap desk.", "trading_style": "Small-cap momentum",
    "primary_markets": "US equities", "verified_records": null, "visibility": "public",
    "aliases": [{"alias": "@exampleg", "platform": "x"}, {"alias": "Example Guest", "platform": ""}]}
   ```
   `id` = lowercase ASCII slug of the canonical name. `visibility: "private_source"` when the person only appears in closed groups/servers.
5. Every handle you saw → `kb person alias add --person <id> --alias "<handle>" --platform <p> --run R`.
6. Appearance → `kb person appearance add --file appearance.json --run R` with `role` (`owner`, `guest`, `host`, `co_host`, `author`, `co_author`, `commenter`, `member`, `archive`, `mentioned`), `match_confidence`, and `evidence` (one sentence: why).
7. `match_confidence < 0.7` → `match_status: "needs_review"`. Mining continues; the user reviews later with `finsocnet persons review`.

## Other tasks

| Task | Command |
|---|---|
| list people | `kb person list` (with card/appearance counts) |
| one person | `kb person get <id>` |
| fix a wrong speaker on a citation | `kb citation attribute <citation_id> --person <id> --role <role> --confidence <c> --run R` |
| merge duplicates | `kb person merge --from <dup> --into <keep> --run R` (moves aliases, appearances, citations, sources, rulebooks) — confirm with the user first |
| uncertain matches | `kb person list --needs-review` |

## Speaker attribution in interviews

Questions and introductions → host. Long first-person answers about their own trading → guest. Use names spoken ("thanks, Tim"), turn-taking, topic continuity. Confidence 0.6–0.9 for interviews, 0.95 for solo content. Details: `specs/03-pipelines.md` §6.
