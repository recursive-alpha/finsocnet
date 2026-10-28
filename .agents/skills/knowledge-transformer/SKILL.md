---
name: knowledge-transformer
description: Rewrite financial and trading knowledge from any text (video transcripts, podcasts, posts, comments, chat messages, articles, books, papers, filings, Pine Script or code) into canonical Knowledge Cards with the same meaning, a fixed claim grammar and a controlled vocabulary; and rewrite user questions into Query Cards for search. Use when mining content, when another skill asks for cards or a Query Card, or when the user asks to "extract rules", "turn this into knowledge", or "normalize this idea".
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI). No scripts of its own; the harness agent does the transformation.
metadata:
  author: finsocnet
  version: "kt-1.0"
  priority: "P0"
  status: planned
  phase: "1"
  spec: docs/spec/02-knowledge-cards.md
---

# Knowledge Transformer

> **Status: planned — instructions are final; the `kb card validate` and `kb vocab` commands it relies on are built in Phases 0–1.**

You turn text into **Knowledge Cards**: one atomic piece of financial knowledge per card, rewritten into a fixed form with the **same meaning** as the source. You also turn questions into **Query Cards** with the same vocabulary, which is what makes search work without embeddings.

The transformer version is `kt-1.0` (frontmatter `version`). Pass it to `kb content done --transformer kt-1.0`.

## When to use

- `market-idea-miner` gives you a chunk to transform.
- `knowledge-search` needs a Query Card.
- The user pastes text and asks for the rules/ideas in it (transform, validate, and show the cards; commit only if asked).

## Read first

- `references/card_format.md` — fields and what goes where.
- `references/claim_grammar.md` — the claim templates per kind, with good and bad claims.
- `references/examples.md` — few-shot examples. Follow their style exactly.
- `references/query_examples.md` — Query Card examples.
- `references/vocabulary_seed.json` — the starting vocabulary (already loaded into the DB; use `kb vocab lookup`, not this file, at run time).

## Procedure: text → cards

Input: a chunk view from `kb content view <content_id> --from-seq A --to-seq B`. Segments look like `[#41 | 12:40-13:05 | speaker ?] text`.

1. Read the whole chunk once. Mark every statement that is reusable knowledge: a rule, a setup, an observation, a mechanism, a definition, a metric, or a practice. Segments marked `(context)` are from the previous chunk: read them, do not make cards from them.
2. Merge repeats of the same statement inside the chunk into one card; cite the clearest occurrence.
3. Split compound statements: one idea per card.
4. For each card fill `kind`, `domain`, `category`, `subject`, `claim` (grammar!), `conditions`, `action`, `horizon`, `instruments`, `regime`.
5. Vocabulary: for each concept run `uv run finsocnet kb vocab lookup "<phrase>"`. Use the returned term. If nothing fits, write the new term to `vocab_new.json` (term, label, facet, aliases, broader, definition) and run `kb vocab add --file vocab_new.json --run <R>` **before** validating cards. Never invent a near-duplicate (`ema10` when `ema_10` exists).
6. `aliases`: the source's own phrases for the concepts ("the 10", "sell a third"). They let users' words find the card later.
7. `numbers`: only explicit numbers; ranges stay ranges.
8. `evidence_level`: personal experience → `anecdotal`; stated as fact → `claimed`; cites a test with method → `backtested`; independently verified → `audited`.
9. `citation`: `content_id`, `segment_seq` where the quote starts, `quote` copied **word for word** from the segment (case and punctuation may differ, words may not), `speaker` (`person_id` or `handle`, `role`, `confidence`). For interviews: questions are the host's and are not knowledge; answers are the guest's.
10. Write the array to `data/work/<run_id>/<content-id-safe>/chunk_<NNN>.cards.json`.
11. `uv run finsocnet kb card validate --file <that file>`. Fix every reported error (each has a JSON pointer and a suggestion). Repeat until valid.
12. If the chunk has no knowledge, write `[]` and `chunk_<NNN>.skip.json` with `{"skip_reason": "promotion|chit_chat|story_without_lesson|single_ticker_prediction|off_topic|unreadable"}`.

## Procedure: question → Query Card

1. Restate the subject in canonical words.
2. Map concepts to terms with `kb vocab lookup` (never add terms for queries).
3. Add `broader_terms` for general questions, `aliases` for how traders say it (include the user's words), `filters` only when clearly implied (a person's name → `person_id`).
4. Optionally add up to 6 FTS5 queries in `fts_queries` (columns: `subject`, `claim`, `conditions`, `terms`, `aliases`, `entities`, `quotes`).
5. Save as `data/work/<run_id>/q.json`.

## Quality rules (never break these)

1. Same meaning, new form: never add a condition, number or conclusion the source did not state; never drop one it did.
2. Ambiguity stays visible: broader term + `notes` (e.g. "MA type not stated" → `ma_10`, not `ema_10`).
3. A speaker who contradicts themselves gets two cards; dedup will link them.
4. Cards are in English; quotes stay in the source language (Vietnamese quotes stay Vietnamese, with Vietnamese phrases in `aliases`).
5. No timestamps, person names or "he says" inside `claim`, `subject` or `conditions`.
6. Single-ticker predictions ("NVDA to 200 tomorrow") are not cards.
