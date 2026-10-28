# 16. People-first discovery

Status: implemented (skill and fields); scholar databases are the next step (§5).

## 1. Why

Exploration used to start from a channel, a topic or a URL, and persons appeared as a by-product of mining. That finds what the algorithm shows, not who matters, and it assumed the interesting people are traders. Knowledge about markets and economics is also published by portfolio managers, investors, CEOs and founders, economists, central bankers and regulators, professors and researchers, analysts, authors and journalists. The pipeline therefore works **person first**: find the person, check they are in scope, create them, find everything they publish on every platform, then explore it.

## 2. Scope rule

A person is in scope when they publish knowledge about financial markets, investing, trading, corporate finance, macro or economics, and the agent can state the evidence in one sentence (`persons.relevance`) with at least one verifiable fact (role, employer, book, paper, letter, channel). Fame alone is not enough; a single mention creates a queue item, not a person. Public professional information only (specs/README §9).

## 3. Data (migration 006)

`persons` gains: `profession` (controlled: trader, portfolio_manager, investor, executive, founder, economist, academic, researcher, analyst, strategist, author, journalist, educator, regulator, central_banker, other), `affiliation`, `domains` (comma-separated fields), `homepage`, `relevance`, `external_ids` (JSON object: `openalex`, `orcid`, `google_scholar`, `ssrn`, `wikipedia`, ...; never guessed). `trading_style` and `primary_markets` remain and are used only for people who trade. `kb person upsert` accepts the new fields (validated against `person.schema.json`); `kb person list --profession P` filters; `kb person get` returns them; the web persons page shows profession and affiliation and filters by profession.

### 3.1 Links (migration 007)

`person_links(person_id, url, kind, platform, handle, label, confidence, match_status, evidence, source_id)`, unique per (person, URL). `kind`: website, social, video, audio, newsletter, code, paper, scholar, wiki, course, book, store, other. Every link has a mandatory one-sentence `evidence` (except rejected ones) and a `confidence`; below 0.7 it is `needs_review`. A confirmed link with `platform` and `handle` also becomes a `person_aliases` row. `kb person link add --file F [--person P]`, `kb person link list --person P [--all]`; `kb person get` returns `links`; merge moves them; the web profile tab lists them with a "to review" badge.

## 4. Pipeline

1. **Skill `people-discoverer`** (new): candidates from web search, Wikipedia lists, conference and faculty pages, OpenAlex authors, recurring authors on platforms and guests already stored → `kb person candidates` (no duplicates) → gate (relevance + fact) → `kb person upsert` → places on every platform (`profile --ingest`, only with two matching signals) → `kb source upsert` with `person_id` → `kb person avatar fetch` → `kb queue add --origin person_crosslink --origin-ref person:<id>`.
1b. **Skill `person-profiler`** (new): one person per run; starts from what is stored (channel descriptions, linked sources), reads the official site, searches each platform with the platform skills' `search`/`profile`, matches with evidence (`references/matching.md`: reciprocal link, own content, verification badge, consistent facts, picture; red flags: fan/archive/squatted/parody accounts), stores links, profile fields, sources, avatar and queue items. There is deliberately **no profile-scraping script**: the agent reads and decides; scripts only fetch and store.
1c. **Skill `person-explorer`** (new): the entry point when the user gives **one profile URL** (`finsocnet explore add <url> --person`, queue `action=profile`, `origin_ref=person-explore`, command `:explore-person`). It resolves the profile with the platform skill, creates or matches the person (scope gate), runs `person-profiler`, discovers everything they published with `list --catalog` on each confirmed place, fetches and mines the best content within a budget, follows new places (two rounds) and mentions, synthesizes the rulebook at ≥ 5 cards, and reports completeness and blockers. It conducts existing skills; it contains no scraper.
2. **`source-explorer`**: a seed that is a person, a field or a profession goes through `people-discoverer` first; a source found by search without a person is matched with `person-matcher` after `profile --ingest`; `list --catalog` discovers everything a source published.
3. **`person-matcher`**: not limited to traders (profession, affiliation, domains, relevance, external ids).
4. Mining, deduplication, rulebooks and search are unchanged: they already work on persons and citations.

## 5. Next step: scholar databases

`research-explorer` already reads OpenAlex and Semantic Scholar (keyless) and SSRN/NBER pages, and `research.py profile <author>` returns an author's works and topics. The next step adds author-centred access: Google Scholar profiles, SSRN author pages, RePEc/IDEAS, ORCID and citation counts as `external_ids` plus a `kb person works` listing, and a `scholar` platform skill that catalogues an author's papers with `list --catalog` (metadata first, full text only for papers worth reading). Until then the discoverer stores ids it can see and uses `research-explorer` for papers. Open questions: which databases need a session or an API key, rate limits, and whether paper authors without a person row should be created automatically (default: no, only in-scope authors with several relevant works).
