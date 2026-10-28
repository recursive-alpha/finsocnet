# 15 — Terminal view (`--ui`) and the web UI

The system has **no HTTP API in Python**. The CLI is the interface: JSON by default, a human view with `--ui`; the Next.js app (`web/`) calls the CLI.

## 1. `--ui` (terminal view)

- Global flag, accepted by every command of `finsocnet` and by every platform script (`output.take_ui` strips it from `argv`; `output.begin()` strips it from `sys.argv`). `FINSOCNET_UI=1` turns it on for a session.
- Without it every command prints exactly one JSON envelope (00 §3). With it the same `data` is drawn by `finsocnet/core/ui.py` (rich): a ranked table for `kb search`, tables for `card search`, `list`, `items`, panels for `card get` and `person get`, key/value blocks for stats, a generic table/tree for anything else; warnings in yellow; failures in a red panel with the hint. **Exit codes are unchanged.**
- `finsocnet search "<english text>" --ui` is the shortcut for `kb search`.

## 2. Web UI (`web/`, Next.js app router)

| Route | Calls | Notes |
|---|---|---|
| `/search` | `GET /api/search` → `finsocnet kb search …` | one box, mode toggle (Auto / Hybrid / Semantic / Keyword), data-type chips (cards, content, traders, rulebooks) with live facet counts, filter panel per type (kind, category, evidence, horizon, min persons · platform, since, language · rulebook section · trader ids), ranked list with relevance bar and `meaning #n` / `keyword #n` badges, modals for cards, content and traders; shareable URL (`?q=&mode=&types=`) |
| `/api/embed` | `kb embed status` | semantic index status shown on the search page |
| `/api/media/<path>` | none (files) | serves only `data/media/**` images; path traversal and non-image extensions return 404 |
| existing pages | `kb …` | traders show avatars; the person modal too |

Rules: route handlers pass **argument vectors** to `execFile` (never a shell string), validate `mode`, `types`, `limit` (≤ 200), and cap the semantic search at 90 s (the first query loads the model). The first search after a restart is slower (model load); later ones take ~1–2 s.

## 3. Acceptance

`tests/unit/test_ui.py` (flag stripping, JSON default is one object, rendering, failure exit code, platform items). Web: `tsc --noEmit` and `eslint` clean for the new files, `next build` succeeds, `/api/search` rejects bad `types`/`mode`/empty `q`, `/api/media` rejects traversal, the search page renders ranked hits from the real database (screenshots checked).
