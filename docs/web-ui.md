# Web UI

A Next.js app in [`web/`](../web/) for people who prefer a browser. It contains **no Python API**: every page calls `finsocnet` through Next route handlers (`execFile`, argument vectors, never a shell string), so it shows exactly what the CLI returns.

## Run

```bash
make web-install && make web-build && make web-start      # http://localhost:3000
# development: make web-dev
# Docker: make docker-build && make docker-up              # web on http://localhost:3001; CLI: docker compose exec worker uv run finsocnet ...
```

It runs from the repository root (it finds `pyproject.toml`) and uses `data/knowledge.db`. `uv` must be on `PATH` for the server process.

## Pages

| Page | What |
|---|---|
| **Search** (`/search`) | everything in one box, see below |
| Dashboard | counts, health (`kb doctor`), contents by status, recent runs |
| Cards | filter and read Knowledge Cards, citations, links, history |
| Traders | persons with avatars; rulebooks, cards, profile and appearances in a modal |
| Content, Sources | stored items with a viewer for segments; sources and their crawl state |
| Skills | the catalogue and each SKILL.md |
| Vocabulary | the controlled terms |
| Operations | runs, dedup decisions, gaps, the explore queue |
| Terminal | run `finsocnet` commands and see the JSON |

## Search

One query over **cards, content text, traders and rulebooks**, ranked in one list.

- **Mode:** Auto (hybrid when vectors exist), Hybrid, Semantic (meaning only: finds paraphrases that share no words), Keyword (FTS5 only). A status line shows whether the semantic index is ready, the model and the number of vectors.
- **Data types:** toggle cards / content / traders / rulebooks; each chip shows how many hits that type produced. Search all, then read the merged ranking.
- **Filters** (by the types selected): cards — kind, category, evidence at least, horizon, minimum persons; content — platform, published since, language; rulebooks — section; any — trader ids.
- Each hit shows a relevance bar, `meaning #n` / `keyword #n` badges (where it ranked in each index), a highlighted snippet and metadata; click to open the card, the content viewer or the trader.
- The URL holds the query, mode and types, so searches can be shared.

The first semantic query after a restart loads the model (a few seconds); later ones take 1–2 s. Queries are matched as typed: use English ([Search → Languages](search.md#languages)). Run `finsocnet kb embed sync` after new content so it shows up by meaning.

## API routes (all call the CLI)

`GET /api/search?q=…&mode=…&types=…&kind=…&category=…&evidence_min=…&horizon=…&min_persons=…&person=…&platform=…&content_type=…&since=…&language=…&limit=…` · `GET /api/embed` · `GET /api/media/<path>` (only images under `data/media/`) · plus the page data routes (`/api/cards`, `/api/persons`, `/api/content`, `/api/stats`, …). Bad `mode`, `types` or an empty `q` return 400.

Design and acceptance: [`specs/15-cli-ui-and-web.md`](../specs/15-cli-ui-and-web.md). The UI needs the Node version of your Next.js install; `web/AGENTS.md` notes that this Next.js differs from older versions, so read `web/node_modules/next/dist/docs/` before changing it.

## Speed: the warm runner

The web UI does not spawn `uv run finsocnet …` per request. The container starts `finsocnet serve` (127.0.0.1:8787, `kb`/`search`/`strategy` only) which keeps Python, the database code and the embedding model loaded, so a call costs tens of milliseconds instead of 1+ s, and the first semantic search no longer reloads the model. Read results are also cached while `data/knowledge.db` and its WAL are unchanged (an agent's write shows on the next request). If the runner is down the UI falls back to spawning the CLI. Run it yourself with `uv run finsocnet serve`; set `FINSOCNET_SERVE=0` to disable it in the container.

## What the pages show

- **Cards** show who said it (pictures and names) and a link to the source; the card detail lists every citation with the person, the verified quote and a link that opens the place (YouTube at the second, PDF at the page).
- **People** (formerly "Traders") lists everyone in scope with profession, affiliation, card and source counts; the profile has Overview (bio, facts, links grouped by kind with evidence on hover, identifiers), Cards, Sources (listed / fetched / mined per source) and Rulebook. Markdown renders like GitHub (tables, task lists, code).
- Every request shows a progress bar under the header; lists show skeletons while they load.
