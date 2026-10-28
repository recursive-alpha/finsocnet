# Web UI

A Next.js app in [`web/`](../web/) for people who prefer a browser. It contains **no Python API**: every page calls `finsocnet` through Next route handlers (`execFile`, argument vectors, never a shell string), so it shows exactly what the CLI returns.

## Run

```bash
make web-install && make web-build && make web-start      # http://localhost:3000
# development: make web-dev
# Docker: make docker-build && make docker-up              # http://localhost:3001, ./data mounted
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
