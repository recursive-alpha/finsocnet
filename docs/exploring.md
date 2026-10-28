# Exploring: discovery, visited items, new sites

FinSocNet finds people, communities, channels and threads on **any topic**. Finance is the miner's interest (it writes cards where there is finance knowledge), not a filter on what explorers may find, store or follow. Everything fetched is stored, searchable by text and, once translated and embedded, by meaning ([Search](search.md)).

## People first

Exploration starts from **who** publishes, not from what an algorithm shows. A seed that is a name, a field or a profession ("famous portfolio managers", "professors of asset pricing", "Jane Professor") goes through [`people-discoverer`](../.agents/skills/people-discoverer/SKILL.md): it finds the people in scope (traders, PMs, executives, economists, professors, authors, regulators), creates them with profession, affiliation and relevance, links their sources everywhere and queues them. A source found by search is attached to its owner with `person-matcher`. See [People](persons.md).

## The explore queue

```bash
finsocnet explore add "pairs trading"                         # a query (any topic, any language)
finsocnet explore add https://quant.stackexchange.com/questions/tagged/risk-management
finsocnet explore add @qullamaggie
finsocnet explore add https://news.ycombinator.com/item?id=44180862 --priority 0.8 --reason "quant discussion"
finsocnet kb queue list
```

`explore add` classifies the target with `core/dispatch.py` (URL pattern → platform skill and action; your own sites from `config/sites/` first). One **explore step** (skill `source-explorer`; `/finsocnet:explore-step`): take the next queue items, run the platform script (`search`, `list`, `profile`, `fetch --ingest`), mine what was fetched, enqueue what it discovered, update the item (`done` / `failed` / `deferred`), end the run. Safe to repeat and to run in parallel; schedule with `/loop 30m /finsocnet:explore-step`.

Where items come from: your seeds, **knowledge gaps** (a question the base could not answer becomes search queries), people and books mentioned in mined content, browsing history triage, cross-platform links, search results, source refreshes. Priorities and the loop are in [`specs/06-explore-improve-eval.md`](../specs/06-explore-improve-eval.md).

A gap closes like this (a real run on this database: pairs trading → 9 cards from 3 Stack Exchange threads):

```
kb card search → weak → kb gap add → queue item (origin gap) → search + fetch + mine → kb card search again → kb gap update --status filled --filled-by <card ids>
```

## Discovering communities on any topic

The `source-explorer` skill carries a recipe per platform; for a topic `T`:

| Where | Command |
|---|---|
| Reddit | `reddit.py search "T" --type sr` → `reddit.py list r/<name> --sort top --t month` |
| YouTube | `youtube.py search "T" --type channel` → `list --tab all` |
| Podcasts | `podcast.py search "T"` |
| Stack Exchange (any of ~180 sites) | `stackexchange.py search "T" --site <slug>` |
| Forums (any engine) | `web_search.py search "T forum"` → `forum.py detect <url>` → `forum.py list <board>` |
| Newsletters, blogs | `substack.py search`, `medium.py search`, `rss.py discover <site>` |
| Telegram, Discord, Facebook groups | `web_search.py search "T site:t.me"` (and invite/group queries), then the platform skill |
| Code, papers | `github.py search "T"` (no topic filter unless `--topic`), `research.py search`, `papers.py search` |
| anything else | `web_search.py` / `google.py` → `web.py fetch` |

Pick communities by activity and distinct authors, enqueue them (`kb queue add … --origin search_result --action crawl_source`), and mark dead ends so they are not offered again.

## Visited items

Every platform script records the items it shows you (when the call has a run) in `seen_items`, keyed by the canonical item id. So a search or a list can tell you what you already looked at, even if you never stored it.

```bash
uv run .agents/skills/reddit-explorer/scripts/reddit.py list r/Daytrading --limit 25 --new-only --run $R
```

Each item has `visited` (`null`, `seen`, `queued`, `fetched`, `skipped`, `failed`), `seen_count` and `known` (true for stored, fetched or skipped items). `--new-only` hides known items (`hidden_known` tells how many). `list --enqueue` queues only unseen items. `list --catalog` stores every unseen listed item as a metadata-only content (title, url, kind, duration, views), which discovers a whole channel or archive (YouTube: long videos, shorts and streams with `--tab all`) in one call. Decisions you make stick:

```bash
finsocnet kb seen mark --key reddit:1xg9xq1 --status skipped --note "off topic" --run $R
finsocnet kb seen check youtube:dQw4w9WgXcQ reddit:1xg9xq1
finsocnet kb seen list --status skipped --platform reddit
finsocnet kb seen stats
```

A later sighting never undoes a decision. `--no-track` disables recording for one call. Details: [`specs/11-explore-visited-open-topics.md`](../specs/11-explore-visited-open-topics.md).

## New sites (platform-skill-builder)

"Add xyz.org": ask the agent, or follow the skill [`platform-skill-builder`](../.agents/skills/platform-skill-builder/SKILL.md).

```bash
S=.agents/skills/platform-skill-builder/scripts/site.py
uv run $S probe https://xyz.org                 # robots.txt, feeds, APIs, forum engine, bot walls, login form, candidate selectors, strategy
# the agent asks you what to collect and about any login or terms concern, then writes config/sites/xyz.yaml
uv run $S check xyz --query pairs --source news  # live test: items found, titles/authors/dates, body length, problems
uv run $S scaffold xyz                           # skill folder + platform/budget config; `finsocnet explore add <xyz url>` now routes to it
```

The probe's `strategy` is `existing` (a skill already covers it), `api`, `feed`, `http`, `browser` or **`blocked`** (robots.txt disallows generic crawlers: no scraper is built; you decide). A recipe (`config/sites/<name>.yaml`) declares lists, search, profile and fetch with CSS selectors, JSON paths or a feed, plus an id regex, a rate budget and dispatch rules; the shared adapter gives it the standard contract, visited tracking, budgets and `--ingest`. Format and examples: [`recipe.md`](../.agents/skills/platform-skill-builder/references/recipe.md). Design: [`specs/14-platform-skill-builder.md`](../specs/14-platform-skill-builder.md).

## Respectful by default

Per-platform budgets (`config/budgets.yaml`: per minute / hour / day and human-like delays) are enforced inside the shared HTTP and browser layers. A checkpoint or login wall (exit 3) stops that platform until you refresh the session. Reading Discord, Facebook, LinkedIn or Instagram with an automated user account can violate their terms: use a secondary account and keep the budgets ([Sessions](sessions.md#risks)).
