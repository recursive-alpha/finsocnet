---
name: people-discoverer
description: Discover and create the people who publish knowledge about financial markets, investing and economics — traders, portfolio managers, investors, CEOs and founders, economists, professors and researchers, analysts, authors, journalists, regulators — before crawling their content. Finds who is notable on a topic or in a field, checks they really are about markets or economics, creates the person with profession, affiliation and external ids, then finds their channels, accounts, blogs, papers and talks on every platform and queues them. Use for "who are the leading people on <topic>", "find famous PMs / professors / CEOs in finance", "discover people before exploring", "add <name> and everything they publish", or when a seed is a person rather than a channel.
license: MIT
compatibility: FinSocNet repository (finsocnet kb CLI); web-searcher, research-explorer and the platform skills; person-matcher for identity decisions.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "9"
  spec: specs/16-people-first-discovery.md
---

# People Discoverer

People first, content second. A channel, account, blog or paper is crawled because of **who** is behind it. This skill finds the people, decides whether they are in scope, creates them once (with a profession), and turns each person into sources to explore. Identity decisions (is this the same person?) stay with `person-matcher`.

## Scope: who counts

Anyone who publishes knowledge about **financial markets, investing, trading, corporate finance, macro or economics**, whatever their job:

| `profession` | Typical evidence |
|---|---|
| `trader`, `investor` | track record, desk, own channel or newsletter on trading |
| `portfolio_manager`, `strategist`, `analyst` | fund or bank, letters, notes, interviews |
| `executive`, `founder` | CEO/CFO/CIO of a financial firm or an exchange, or a company leader whose shareholder letters, talks or books teach finance |
| `economist`, `central_banker`, `regulator` | institution, speeches, working papers |
| `academic`, `researcher` | university chair, papers on asset pricing, microstructure, macro, behavioural finance |
| `author`, `journalist`, `educator` | books, columns, courses about markets or economics |
| `other` | in scope by what they publish, none of the above fits |

A person is **in scope** only with evidence you can state in one sentence (`relevance`): a book, paper, talk, letter, post series or role that is about markets or economics. Fame alone is not enough (a famous CEO of a car maker is in scope only for finance content they publish). Out of scope: skip, and `kb seen mark … --status skipped --note "<why>"` when it came from a search result. Never create a person from a single mention; mentions are queue items (`origin=mention`).

## Procedure

1. `uv run finsocnet kb run start --skill people-discoverer --goal "<topic or names>" --harness <h> --model <m>` → `R` (reuse the parent's `R` when called by source-explorer).
2. **Find candidates** (any language, no topic limit). Pick the recipes that fit the seed from `references/discovery.md`: web search for "leading X", Wikipedia and Wikidata lists, conference speaker pages, book authors, fund and university staff pages, OpenAlex top authors for a topic, Hacker News / Reddit / YouTube authors who recur across communities, guests of podcasts already stored (`kb person list`, `kb content search`).
3. **Check what we know**: `uv run finsocnet kb person candidates --name "<name>" --handle "<handle>" --context "<what you found>"`. A confident match: add the new handle or profession to the existing person (step 5), do not create a second one.
4. **Gate**: one sentence of `relevance` + at least one verifiable fact (employer, role, publication, book, channel). If you cannot state both, do not create the person.
5. **Create or update** the person (`kb person upsert --file person.json --run R`):
   ```json
   {"id": "jane-professor", "canonical_name": "Jane Professor", "profession": "academic",
    "affiliation": "Example University, Department of Finance", "domains": "asset pricing, market microstructure",
    "relevance": "Chaired the finance dept.; published 'Liquidity and returns' (2019) and a macro newsletter.",
    "homepage": "https://example.edu/~jane", "bio": "…",
    "external_ids": {"openalex": "A5012345678", "orcid": "0000-0002-1825-0097", "wikipedia": "Jane_Professor"},
    "aliases": [{"alias": "@janeprof", "platform": "x"}, {"alias": "Jane Professor", "platform": ""}]}
   ```
   `trading_style` / `primary_markets` only for people who trade. Never invent ids: leave `external_ids` empty rather than guessing.
6. **Find their places** on every platform (this is what makes the person useful) with the skill `person-profiler` (it owns the matching rules and stores links with evidence). In short:
   - `research.py profile "<name>"` for academics and researchers (keeps the OpenAlex id for `external_ids`);
   - each platform skill's `search "<name>" --type channel|user` and `profile <handle> --ingest --run R`, only when the match is certain (name **and** a second signal such as the homepage link in the bio, the same photo, a verified badge, the employer);
   - the person's own site: `web.py fetch <homepage>` → links to channels, newsletter, podcast, papers; `rss.py discover <site>`.
   Link each source: `kb source upsert` with `{"id": "<source id>", "person_id": "<person id>"}`; add aliases (`kb person alias add`), appearances (`role: owner`, evidence one sentence).
7. **Pictures**: `person-matcher` → Pictures section (`kb person avatar fetch --person <id> --run R`).
8. **Queue the work**: `kb queue add --target <channel/handle/url> --origin person_crosslink --origin-ref person:<id> --action crawl_source --reason "<person> (<profession>)" --priority <0.5-0.9>`. Prefer `list --catalog` on each source to discover everything the person published, then let `source-explorer` fetch and `market-idea-miner` mine what matters.
9. `kb run end --run R --outcome success|partial --stats '{"people_created": n, "people_updated": n, "skipped": n, "sources_linked": n}'`.

## Rules

- Public figures only, and only what they publish themselves or what is public about their professional role. No private contact data, no home addresses, no family details.
- One person, one record: merge duplicates with `person-matcher`, ask the user before `kb person merge`.
- `visibility: "public"` unless the person only appears in closed groups.
- Say what you are unsure of in the run stats or `relevance` ("unverified: homepage link only"), never in silence.
- Scholar databases beyond OpenAlex and Semantic Scholar (Google Scholar, SSRN author pages, RePEc, ORCID) are the next step (`specs/16`); until then store ids in `external_ids` when a page shows them and use `research-explorer` for papers.

## After discovery

Run `finsocnet kb person list --profession <p>`; a person with sources but no cards is the explorer's backlog: `source-explorer` → `market-idea-miner`.
