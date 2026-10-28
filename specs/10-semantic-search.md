# 10 — Semantic search, translation and unified search

Normative for ADR-009. Code: `finsocnet/core/embed.py`, `translate.py`, `search.py`, `cards.py` (`retrieve`, `search_cards`). Skills: `translator`, `knowledge-search`. Migration `004` (`embeddings`, `segment_translations`).

## 1. Principles

1. **Everything searchable is English.** Cards are English by contract (02). Segments and persons are embedded through English text only: a content in English as is, anything else through its translation. A content whose language is unknown is not embedded.
2. **The agent detects and translates.** No language-detection library, no heuristic, no translation API in scripts (ADR-002, ADR-009). The `translator` skill reads samples and writes verdicts; `kb translate …` stores them.
3. **Vectors live in SQLite.** One table, float32 BLOBs, brute-force cosine with numpy. No second database, no extension, no torch.
4. **Hybrid by default, lexical when there is nothing to fuse.** Search never fails because embeddings are missing; it degrades to the BM25 search of 03 §2 and says so.
5. **A similarity score never decides a duplicate.** Candidate retrieval for dedup uses the same fusion; the decision remains the agent's (ADR-004).

## 2. Model

`config/embedding.yaml`; environment overrides `FINSOCNET_EMBED_PROVIDER` (`fastembed` | `hashing`) and `FINSOCNET_EMBED_MODEL`.

| Key | Default | Meaning |
|---|---|---|
| `provider` | `fastembed` | ONNX encoder on CPU; `hashing` = offline feature hashing (tests, no download) |
| `model` | `snowflake/snowflake-arctic-embed-m` | 768 dims, 0.43 GB, Apache-2.0 |
| `query_prefix` | `Represent this sentence for searching relevant passages: ` | applied to queries only |
| `max_chars` | 2000 | text cut before encoding |
| `cache_dir` | `data/models` | model files |

**Why this model** (MTEB leaderboard, https://huggingface.co/spaces/mteb/leaderboard; scores are the models' published `model-index` results, mean nDCG@10 over 14 of the 15 English retrieval tasks): arctic-embed-m 55.8 · mxbai-embed-large-v1 55.3 · bge-base-en-v1.5 54.1 · nomic-embed-text-v1.5 53.8 · arctic-embed-s 52.9 · bge-small-en-v1.5 52.5. Among models that run through ONNX on CPU in under 0.5 GB it is the best; `Qwen/Qwen3-Embedding-0.6B` ranks higher on the leaderboard but needs 1.1–2.4 GB and is an opt-in. English-only is acceptable because of principle 1.

Vectors are stored **per model** (`embeddings.model`): changing the model leaves old vectors in place and re-embeds lazily (`kb embed sync`; `kb embed status` lists `other_models`).

## 3. Language and translation

Tables: `contents.language` (BCP-47, `mixed`, `und`), `segment_translations(content_id, seq, source_lang, text_en)`.

| Command | Purpose |
|---|---|
| `kb translate detect-pending [--by-source] [--limit N]` | contents (or sources) without a language, each with a text sample |
| `kb translate set-language --file F --run R` | `[{content_id\|source_id, language}]`; a source verdict covers its contents that have none and never overwrites |
| `kb translate pending [--content C]` | segments of non-English contents without English text |
| `kb translate put --file F --run R` | `[{content_id, seq, source_lang, text_en}]`; `source_lang: en` without `text_en` marks an English segment inside a `mixed` content |
| `kb translate get C [--seq N]` | read stored translations |

Original text in `content_segments` is **never** replaced; quotes in cards keep the source language (02).

## 4. Embedded kinds and their text

| Kind | `ref` | Text |
|---|---|---|
| `card` | card id | subject. claim. Conditions: …. Also said as: aliases. Topics: terms in words |
| `segment` | `content_id#seq` | the translation, or the segment text when `contents.language` is English |
| `person` | person id | name, moniker, trading style, primary markets (agent-written English fields; the free-text bio is not embedded) |
| `skill` | `person_skills.id` | title, summary, first 1500 chars of the rulebook section |

`text_hash` (sha1 of the text) makes `kb embed sync` incremental: unchanged rows are skipped, edited cards (aliases, claim) are re-embedded.

## 5. Search

**Query flow:** question → (translator: English statement) → Query Card → embedded as `subject. Also said as: aliases. Topics: terms` → `kb card search`. Free `--text` is the caller's English text.

**`kb card search [--mode auto|lexical|semantic|hybrid]`:** BM25 sub-queries (03 §2) and the cosine ranking of the query are fused with RRF (`k = 60`); the vector ranking has weight 2. `auto` = hybrid when card vectors exist for the current model, else lexical. `semantic` and `hybrid` without vectors fall back to lexical with a warning naming `kb embed sync`.

**`kb search "<english text>" [--types cards,contents,persons,skills] [--mode …] [filters] [--limit N]`** (alias `finsocnet search`): every selected type is searched lexically (FTS5 on `knowledge_cards_fts`, `segments_fts`, `persons_fts`, `person_skills_fts`) and semantically, fused per type, filtered, then merged: `relevance = prior(type) × score / best score of the type` with priors cards 1.0 · skills 0.92 · persons 0.88 · contents 0.8, so the best hits of every type interleave. Output: `results[]` with `type, id, title, snippet, relevance, score, ranks{lex,vec}, meta`, plus `facets` (hits per type), `mode`, `filters`, `warnings`. Filters apply to the types they make sense for and others report "ignored":

| Filter | Types |
|---|---|
| `--kind --category --domain --horizon --evidence-min --instrument --min-persons` | cards |
| `--platform --content-type --since --language --status` | contents |
| `--person` | cards, contents, skills |
| `--category` | skills (rulebook section) |

## 6. Evaluation

`finsocnet eval score search --outputs DIR --search-mode lexical|semantic|hybrid` embeds the fixture cards with the configured model and scores the chosen mode. On the 30-case set: recall@10 lexical 0.956, semantic 0.967, hybrid 0.978 (MRR 1.0 for all).

## 7. Acceptance

- `kb embed sync` is idempotent; editing a card's alias marks exactly that card pending.
- With `FINSOCNET_EMBED_PROVIDER=hashing` the whole suite runs offline.
- A non-English content is not embedded until `set-language` ran, and its segments only after `translate put`.
- `kb search` returns hits of every selected type, respects filters, and never errors when embeddings are missing.
- Dedup candidate retrieval is unchanged when no vectors exist.
