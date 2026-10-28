# Concepts

## The loop

```
discover ──► capture ──► transform ──► deduplicate ──► serve ──► improve
 people and   everything   the agent     the agent       cited      failed searches
 sources on   into one     writes        decides         answers,   become gaps,
 any topic    SQLite file  Knowledge     same / refines  rulebooks, gaps drive
                           Cards         / related /     search     exploration,
                                         contradicts                lessons become
                                         / new                      reviewed changes
```

## Who does what

| Scripts (`finsocnet`, skill scripts) | The agent (your harness) |
|---|---|
| fetch pages, APIs, transcripts; store; validate JSON; run BM25 and vector search; score evaluations; enforce budgets and run ids | read content, identify people, write cards, decide duplicates, detect languages, translate, judge relevance, write answers and rulebooks, decide what to explore next |

Scripts print one JSON envelope and never call a model API (ADR-002). The only models scripts run are local and narrow: Whisper for speech-to-text and the embedding encoder for search.

## Data

| Thing | Table(s) | Notes |
|---|---|---|
| **Content** | `contents`, `content_segments`, `sources` | one stored item (video, thread, article, page, file); segments are numbered pieces with a locator (timestamp, comment id, page) so every quote can link back. `language` is the agent's verdict |
| **Knowledge Card** | `knowledge_cards`, `card_citations`, `card_links`, `card_history`, `dedup_decisions` | one atomic statement in a fixed claim grammar, with vocabulary terms and citations (exact quote, segment, who said it, in which role). English by contract; quotes keep their language |
| **Vocabulary** | `vocabulary` | the controlled terms (`ema_10`, `episodic_pivot`, …) that make lexical search work; grows through `kb vocab add` |
| **Person** | `persons`, `person_aliases`, `person_appearances`, `person_images`, `person_skills` | knowledge belongs to people, not channels; a rulebook is a person's cards rewritten by category |
| **Run / lesson / gap / queue** | `agent_runs`, `lessons`, `knowledge_gaps`, `explore_queue`, `seen_items` | the audit trail and the improvement loop |
| **Vectors** | `embeddings`, `segment_translations` | English text embedded per model; translations written by the agent |

A **claim** looks like `IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position`; kinds: `rule`, `setup`, `observation`, `mechanism`, `definition`, `metric`, `practice`. See [`specs/02-knowledge-cards.md`](../specs/02-knowledge-cards.md).

## Guarantees

- Every write needs a run id; every card has at least one citation whose quote is found in its segment (or is flagged `quote_verified = 0`).
- A card commit (card + citations + links + index + decision) is one transaction and idempotent.
- Contents, segments, citations and decisions are never deleted; cards are merged or retired with a snapshot in `card_history` and can be undone (`kb card undo`).
- Sessions and cookie values are never printed, logged or stored in the database ([Sessions](sessions.md)).

## Languages

Cards are English. A Vietnamese forum post yields English cards quoting the Vietnamese text. For search, non-English segments are embedded through an English translation that the agent writes; search questions in any language are first restated in English by the agent ([Search](search.md#languages)).
