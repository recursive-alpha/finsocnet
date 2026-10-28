---
name: knowledge-search
description: Answer trading and finance questions from the FinSocNet knowledge base with cited Knowledge Cards — who said it, how many people agree, evidence level, contradictions, and links with timestamps. Transforms the question into a Query Card, searches cards with SQLite FTS5, reads and ranks results, and logs a knowledge gap when the answer is weak. Use for "what do traders say about…", "how should I…", "find rules for…", "who recommends…", "is there evidence that…", or /finsocnet:search.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P0"
  status: ready
  phase: "1"
  spec: specs/03-pipelines.md
---

# Knowledge Search

Search is hybrid over canonical cards, BM25 plus embeddings of the English Query Card (ADR-001, ADR-009): you turn the question into the same vocabulary the cards use, the script retrieves, and you judge relevance and write the answer.

## Procedure

1. `kb run start --skill knowledge-search --goal "<question>" --harness <h> --model <m>` → `R`.
2. **Not English?** Use `translator` §3 first: restate the question in English. Then write a Query Card (see `knowledge-transformer/references/query_examples.md`) to `data/work/<R>/q.json`. If the question names a person, resolve them first: `kb person candidates --name "<name>"`.
3. `uv run finsocnet kb card search --query-card data/work/<R>/q.json --limit 30 [--mode auto|lexical|semantic|hybrid]`. `auto` (default) fuses BM25 over the canonical form with the cosine ranking of the embedded Query Card when card embeddings exist (`kb embed status`; run `kb embed sync` if cards are pending). The flow is: question → translate → Query Card → embed → hybrid search.
4. Read every result. Drop irrelevant ones. Group cards that answer the same sub-question. For cards with `stats.contradictions > 0`, run `kb card get <id> --links` and read the other side.
5. Fewer than 3 relevant cards → rewrite the Query Card once (broader terms, more aliases, fewer filters) and search again.
6. Need more context for a claim → `kb content view <content_id> --from-seq <seq-2> --to-seq <seq+3>` around the citation.
7. Answer in the format below, in the user's language.
8. Weak result → `kb gap add --query "<question>" --query-card data/work/<R>/q.json --verdict no_answer|weak_answer|conflicting --run R`. Tell the user the gap was logged and will drive exploration.
9. `kb run end --run R --outcome success --stats '{"cards_used": N, "gap": true|false}'`.

## Answer format

For each claim used:
```
• <claim in plain language>
  Who: <names> (consensus: <persons> people, <contents> sources) · Evidence: <evidence_level>
  Source: "<quote>" — <content title>, <link with locator>
  Contradicted by: <one line + card id>   (only if any)
```
Then a 2–5 sentence synthesis. Every factual claim needs a card; if you add general knowledge, label it as such.

Links with locators: YouTube `https://youtu.be/<id>?t=<start_sec>`; Reddit comment permalink; PDF `#page=<n>`; Discord `https://discord.com/channels/<guild>/<channel>/<message_id>`; X `https://x.com/i/status/<tweet_id>`.

## Feedback

If the user says an answer or card is wrong: `kb feedback add --target-type answer|card --target-id <id> --rating -1 --comment "<what is wrong>"`. The self-improver handles it.
