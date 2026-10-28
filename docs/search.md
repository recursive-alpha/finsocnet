# Search

Three ways to look things up, from precise to broad.

| Want | Use |
|---|---|
| a cited answer to a question | skill `knowledge-search` (the agent) → `kb card search` |
| the best matches across everything stored, ranked, with filters | `finsocnet search` / `kb search` / the [web UI](web-ui.md#search) |
| one exact thing by id | `kb card get`, `kb content view`, `kb person get` |

## How matching works

Two indexes in the same SQLite file:

- **Keywords:** SQLite FTS5 (BM25) over the canonical text of cards (subject, claim, conditions, terms, aliases, entities, quotes), segments, persons and rulebooks. Cards are written in a controlled vocabulary, so `10 EMA`, `ema_10` and `ten-day average` land on the same term.
- **Meaning:** every card, person, rulebook section and English segment has an embedding (float32 BLOB in `embeddings`). A query is embedded the same way and compared by cosine similarity. This finds paraphrases that share no words ("how many shares so one bad trade cannot hurt" → *risk at most 1.25% of equity*).

Results of both are fused with Reciprocal Rank Fusion (the vector ranking counts double). With no embeddings, search is exactly the keyword search; it never fails for lack of them.

**Model:** `snowflake/snowflake-arctic-embed-m` through fastembed (ONNX, CPU, 0.43 GB, Apache-2.0), picked from the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard) as the best English retrieval model that runs well on CPU in under 0.5 GB (mean nDCG@10 55.8 over 14 retrieval tasks vs 54.1 for bge-base, 53.8 for nomic v1.5). Change it in `config/embedding.yaml`; vectors are kept per model.

On the 30-case evaluation set, recall@10: keyword 0.956 → semantic 0.967 → **hybrid 0.978**.

## Make things searchable

```bash
finsocnet kb embed status            # what is embedded, what is pending, other models present
finsocnet kb embed sync              # incremental: only new or edited rows (cards, persons, rulebooks)
finsocnet kb embed sync --kinds segment    # content text (English only, see Languages)
```

The `market-idea-miner` procedure runs `embed sync` after committing cards. The first sync downloads the model (once, into `data/models/`).

## Unified search

```bash
finsocnet search "how to size a position after a losing streak" --ui
finsocnet search "options theta" --types cards,skills --kind rule --evidence-min claimed
finsocnet search "breakout failure" --types contents --platform youtube --platform reddit --since 2026-01-01
finsocnet search "defense first" --types persons
finsocnet search "stop placement" --person tom-dante --mode semantic --limit 20
```

| Flag | Meaning |
|---|---|
| `--types cards,contents,persons,skills` | which kinds of data to search (default: all four); content hits are text passages grouped by content |
| `--mode auto\|hybrid\|semantic\|lexical` | `auto` = hybrid when vectors exist |
| `--kind --category --domain --horizon --evidence-min --instrument --min-persons` | card filters |
| `--platform --content-type --since --language --status` | content filters |
| `--person` (repeatable) | cards, content and rulebooks by trader |
| `--category` | for rulebooks: section (setup, entry, risk…) |
| `--limit N` | merged result size (default 30) |

The result has `results[]` (`type`, `id`, `title`, `snippet`, `relevance`, `ranks{lex,vec}`, `meta`), `facets` (hits per type) and `warnings` (a filter that does not apply to the chosen types is reported and ignored). Types are merged by *relevance*: each hit's score relative to the best hit of its type, times a small prior (cards 1.0, rulebooks 0.92, traders 0.88, content 0.8), so the best of every type interleave.

## Answering a question (agent flow)

`question → translate to English → Query Card → embed → search → read the cards → cited answer`

1. If the question is not English the agent restates it in English ([translator](../.agents/skills/translator/SKILL.md) §3).
2. It writes a **Query Card** (subject, vocabulary terms, aliases).
3. `kb card search --query-card q.json` runs BM25 and the embedded Query Card together.
4. The agent reads each hit, drops irrelevant ones, follows contradictions, and answers with quote, person, source and a timestamped link; a weak answer becomes a **gap** (`kb gap add`) that drives exploration.

## Languages

All embedded text is English. Cards already are. For other content:

1. The agent decides the language of every content, per **source** where possible: `kb translate detect-pending --by-source`, then `kb translate set-language --file languages.json --run R`. (No detector is built in; the agent reads samples.) Until a content has a language it is not embedded.
2. For non-English contents the agent translates segments and stores them: `kb translate pending`, `kb translate put --file translations.json --run R`.
3. `kb embed sync --kinds segment` embeds the English text. Original text and quotes are never replaced.

Queries typed into the web UI or `finsocnet search` are matched as typed: write them in English (or let the agent translate).

Details: [`specs/10-semantic-search.md`](../specs/10-semantic-search.md).
