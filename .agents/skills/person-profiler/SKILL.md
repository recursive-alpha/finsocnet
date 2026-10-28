---
name: person-profiler
description: Build the full profile of one person — find and verify their official website, social accounts (X, YouTube, LinkedIn, Instagram, Facebook, TikTok, Threads, Bluesky, Reddit, Telegram, Discord), newsletters, podcasts, courses, books, code, papers and scholar/Wikipedia pages, match each to the person with evidence and confidence, and store them as links, aliases, sources and profile fields. Use after a person was created (people-discoverer, person-matcher), when the user says "find everything about <person>", "profile <name>", "what are their social networks / links / website", "is this account really them", or to complete and re-verify an incomplete profile.
license: MIT
compatibility: FinSocNet repository (finsocnet kb CLI); web-searcher, web-reader and the platform skills' `profile` commands; agent browser for pages that need it.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "9"
  spec: specs/16-people-first-discovery.md
---

# Person Profiler

You do the research; scripts only fetch and store. There is no profile-scraping script: you read pages, compare them and decide, and every decision is stored with its evidence. One person per run (several people in parallel are fine, each with its own run).

## Procedure

1. `uv run finsocnet kb run start --skill person-profiler --goal "profile <person id>" --harness <h> --model <m>` → `R`.
2. **Start from what we already hold**: `kb person get <id>` (aliases, sources, appearances, links, images); `kb source get <source id>` for each linked source; the stored channel/profile descriptions and video descriptions (`kb content get <id>`, fields `description`, `links`, `mentions`) usually list the person's other places, and they were written by the person: the strongest evidence you have.
3. **Official site first.** `homepage` known or found (their channel's "About" links, a bio link) → `uv run .agents/skills/web-reader/scripts/web.py fetch <url>` and read it: footer/header icons, "follow me", "contact", "about", newsletter signup, course/store, book pages. Every link there that points to an account of theirs is a candidate with **strong** evidence (their own site says so).
4. **Then search for what the site does not list**, per platform from `references/places.md`: `web_search.py search "\"<full name>\" site:<domain>"`, the platform skill's `search "<name>" --type user|channel` and `profile <handle>` (compare bio, links, location, employer, follower scale with what you know). Papers and scholar: `research.py profile "<name>"`. Wikipedia/Wikidata: web-searcher.
5. **Match with evidence** (`references/matching.md`). In short:
   - **confirmed** (`confidence` ≥ 0.9): a reciprocal link (their site or channel links to the account, or the account's bio links back to the site/channel) or two independent signals (same distinctive name **and** same employer/bio facts **and** same picture or a platform verification badge).
   - **needs_review** (0.5–0.89): one signal, or a plausible account with no cross-link. Stored, shown as unconfirmed, never used to attribute content.
   - **do not store**: a name collision, a fan page, a parody, an account that sells or promotes "in the style of", a squatted placeholder. Say in the run stats what you rejected and why.
   - Look at the picture when it matters: `kb person avatar list --person <id>` then open the stored file and the candidate's `avatar_url` and compare; never attach a face you are unsure of.
6. **Store** what you found:
   - Links (one call, a list): `kb person link add --person <id> --file links.json --run R`, each
     `{"url": "https://x.com/qullamaggie", "kind": "social", "platform": "x", "handle": "@Qullamaggie", "label": "X", "confidence": 0.95, "evidence": "linked from kristjankullamagi.com footer and from his YouTube About"}`.
     `kind`: `website`, `social`, `video`, `audio`, `newsletter`, `code`, `paper`, `scholar`, `wiki`, `course`, `book`, `store`, `other`. `evidence` is mandatory (one sentence a reviewer can check). A confirmed link with `platform` + `handle` also becomes an alias.
   - Profile fields: `kb person upsert --file person.json --run R` with `homepage`, `bio` (own words from their own about page, short), `affiliation`, `domains`, `profession`, `relevance`, `external_ids` (`openalex`, `orcid`, `google_scholar`, `ssrn`, `wikipedia`: only ids you saw on a page).
   - Sources that publish content (channel, newsletter, podcast, forum account): `platform skill profile <handle> --ingest --run R`, then `kb source upsert` with `person_id` (confirmed links only), and `kb person appearance add` (`role: owner`, `evidence`).
   - Picture: `kb person avatar fetch --person <id> --run R`.
7. **Queue the content, do not crawl everything now**: `kb queue add --target <source url or handle> --origin person_crosslink --origin-ref person:<id> --action crawl_source --reason "<person>: <what>" --priority 0.5..0.8 --run R` for confirmed content sources (`list --catalog` discovers them cheaply later).
8. **Report**: `kb person link list --person <id>`; `kb run end --run R --outcome success|partial --stats '{"links_confirmed": n, "links_needs_review": n, "rejected": n, "sources_linked": n, "not_possible": ["x: LOGIN_REQUIRED"]}'`.

## Rules

- Public, professional information only: what the person publishes themselves or what is public about their role. No private addresses, phone numbers, family members, personal accounts of relatives, leaked data.
- A platform that answers `LOGIN_REQUIRED` / `CHECKPOINT` (exit 3): stop on that platform, list it under `not_possible` in the run stats, and tell the user which session to export. Never log in, never ask for passwords or cookies.
- Never guess a handle or URL from the name (`x.com/<name>` may belong to somebody else). A URL enters the database only after you opened it (or its `profile` command returned it) and compared it with the person.
- Do not copy long texts: short bio in your own words, links, ids, labels.
- Anything uncertain is `needs_review` with the doubt in `evidence`, not a confident link and not silence. The user reviews with `finsocnet persons review`.
- Re-running is safe: links are unique per URL and updated in place; use `kb person link list --all` to see rejected ones before re-adding them.
