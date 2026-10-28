---
name: knowledge-dedup
description: Decide whether a new Knowledge Card is the same as, refines, relates to, or contradicts existing cards, and commit the decision atomically so the knowledge base keeps exactly one card per idea with all its citations. Use after knowledge-transformer produced validated cards, during market-idea-miner runs, for periodic re-dedup sweeps, or when the user asks to "merge duplicates", "check if we already have this idea", or "find contradictions". The script retrieves candidates lexically; the agent judges.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P0"
  status: planned
  phase: "1"
  spec: docs/spec/03-pipelines.md
---

# Knowledge Dedup

> **Status: planned — built in Phase 1.**

`kb card candidates` finds up to 10 similar existing cards with SQLite FTS5 over the canonical card fields (no embeddings, ADR-001). **You** decide what each candidate is to the new card. `kb card commit` applies your decision in one transaction and stores your rationale.

## When to use

- Step 5c of `market-idea-miner` (every validated chunk of cards).
- `self-improver` re-dedup sweeps.
- User: "do we already have this rule?", "merge duplicate cards", "which ideas contradict each other?".

## Procedure

1. `uv run finsocnet kb card candidates --file chunk_NNN.cards.json --limit 10`
   → for each new card `index`: `candidates[]` with the full card, `stats` (citations, persons, contradictions), top citations and `score_debug`.
2. For each new card, compare it with each candidate and label the candidate:

   | Label | Meaning |
   |---|---|
   | `same` | same claim, compatible conditions, same action/direction, same horizon (or one is `n/a`), overlapping instruments; wording may differ |
   | `refines` | same claim; the new card adds conditions, numbers, a variant or an exception |
   | `related` | same subject or setup family, different claim (e.g. entry vs stop of the same setup) |
   | `contradicts` | same conditions, opposite or incompatible action/outcome |
   | `unrelated` | ignore |

3. Choose the final decision for the new card:
   - any `same` → `"decision": "same"`, `target_card_id` = best same candidate
   - else any `refines` → `"decision": "refines"`, `target_card_id`, plus `updates`
   - else → `new`, or `related` / `contradicts` (the card is inserted) with a `links` entry for **every** related/contradicting candidate
4. Write all decisions for the chunk to `data/work/<run>/<content>/chunk_NNN.decisions.json` (format below).
5. `uv run finsocnet kb card commit --file chunk_NNN.decisions.json --run <R>`.
6. Per item results: `committed`, `already_committed` (safe retry), or `error`. On `CONFLICT` (target was merged/retired since step 1): rerun step 1 for that card only and decide again.

## Decision rules

1. Same topic is never enough for `same`. Check conditions, action, horizon, instruments.
2. Opposite action under the same conditions → `contradicts`, never `same`.
3. Different people saying the same thing → `same`. One card, many citations; that is the consensus count.
4. A special case of a broader card with a different action → `related` with relation `example_of`.
5. Unsure between `same` and `related` → `related`. A missed merge is cheap; a wrong merge loses information.
6. No candidates → `new` with `"candidate_ids": []` and rationale `"no candidates"`.
7. Different numbers for the same rule (10% vs 8%) → `refines` with `notes_append`, never overwrite the number.

## Decision file format

```json
[{
  "index": 0,
  "new_card": { "...the validated card including citation..." },
  "candidate_ids": [41, 77],
  "decision": "refines",
  "target_card_id": 41,
  "updates": {
    "conditions_add": ["slower stocks use ma_20"],
    "numbers_set": {"trail_ma_slow": 20},
    "aliases_add": ["the 20"],
    "terms_add": ["ma_20"],
    "notes_append": "Variant: ma_20 for slower stocks.",
    "evidence_level_upgrade": null,
    "invalidation_set": null
  },
  "links": [{"to_card": 77, "relation": "related", "rationale": "Same setup family; 77 is the stop rule."}],
  "rationale": "Same partial-then-trail rule as 41; adds the ma_20 variant."
}]
```

Allowed `updates` (refines only): `conditions_add`, `numbers_set` (new keys only), `aliases_add`, `terms_add`, `entities_add`, `notes_append`, `evidence_level_upgrade` (upward only), `invalidation_set` (only if empty). `claim`, `subject`, `kind` and `action` never change through dedup.

Link relations: `related`, `contradicts`, `prerequisite`, `example_of`, `refines`.

## References

- `references/decision_examples.md` — 12 worked decisions. Read before the first dedup of a session.
- `docs/spec/03-pipelines.md` §2 (candidate algorithm) and §3 (this procedure).
