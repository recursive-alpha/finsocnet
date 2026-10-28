# 03 — Agent Pipelines: Mining, Dedup, Search, Persons

Each section is the normative procedure for one skill. SKILL.md files copy these procedures (shortened) and link here.

Common rules for every pipeline:
- Start: `kb run start --skill <skill> --goal "<goal>" --harness <h> --model <m>` → `run_id`. Pass `--run <run_id>` to every write.
- Work files go to `data/work/<run_id>/`.
- End: `kb run end --run <id> --outcome success|partial|failed --stats '{…}'`.
- Anything surprising (validator rejects something that looks right, a platform changed, a repeated mistake) → `kb lesson add`.

---

## 1. Mining One Content Item (`market-idea-miner`)

### 1.1 Procedure

```
1. kb content claim <id>                        → fails with CONFLICT if another run holds it
2. kb content get <id> --meta-only              → title, platform, source, author, duration, process_status
3. Person context (§5): identify owner/host/guests BEFORE transforming
     kb person candidates --name … --handle … --platform …  → decide → kb person upsert / appearance add
4. kb content chunks <id> --max-chars 12000 --overlap 2
5. for each chunk:
     a. kb content view <id> --from-seq A --to-seq B
     b. transform (knowledge-transformer, 02 §5.2) → chunk_NNN.cards.json → kb card validate (fix until valid)
     c. dedup (§3) → chunk_NNN.decisions.json → kb card commit
     d. kb content done <id> --upto-seq B --cards <total so far>   (checkpoint; safe to resume)
6. Mentions: collect people, books, papers, tools, channels, URLs mentioned in the content that look useful
     → kb queue add --origin mention --origin-ref <id> --reason "<one line>" --priority <0..1>
7. If any person gained ≥ 5 new cards in this run → note it for person-skill-synthesizer (§7)
```

On any script error, follow the exit-code table (00 §3.3). If the content cannot be processed (unreadable, wrong language detection, empty transcript): `kb content fail <id> --error "<reason>"`.

### 1.2 Chunk view format (`kb content view`)

```
CONTENT youtube:abc123def45 | video | "Selling into strength — my exact rules" | 2026-09-02
SOURCE  youtube:channel:UCxxxx (Example Swing Trader) | owner person: example-swing-trader
PEOPLE  example-swing-trader (owner)
SEGMENTS 40-61 of 0-212
[#40 | 12:15-12:40 | speaker ?] …
[#41 | 12:40-13:05 | speaker ?] so what I do is, once it's up like 3, 4 days after the breakout I sell a third …
[#42 | 13:05-13:31 | speaker ?] …
```
- Transcript locator shown as `mm:ss-mm:ss` (or `h:mm:ss`); comments as `comment <id> | <author> | score N`; pages as `page N`; code as `code <path>:<l1>-<l2>`.
- `speaker` shows `segment.person_id` if attributed, else `speaker_hint`, else `?`.
- Overlap segments from the previous chunk are prefixed with `(context)` and must not produce new cards.

### 1.3 Chunk sizing

| Content | `--max-chars` | Why |
|---|---|---|
| transcripts, threads, chats | 12000 | enough context for speaker attribution |
| books / long PDFs | 8000 | dense text, more cards per char |
| code (Pine, Python) | 6000 | read fully |

---

## 2. Candidate Retrieval Algorithm (`finsocnet.core.cards.candidates`, `fts.py`)

Deterministic, lexical, no embeddings (ADR-001). Used by both `kb card candidates` (dedup) and `kb card search` (search).

### 2.1 Input normalization

- `T` = card/query `terms` ∪ `broader` of each term (one level) ∪ `broader_terms` (query only).
- `A` = `aliases` (+ for queries: phrases in `question` matched to vocabulary aliases via `vocabulary_fts`, mapped back to term keys and added to `T`).
- `S` = significant words of `subject`: tokens after removing English stopwords and grammar keywords (`IF THEN AND OR WHEN TENDS TO CAUSES BECAUSE IS HAS IMPROVES HURTS WITHIN UNTIL`), length ≥ 3.
- `C` = significant words of `claim` (same filter), at most 15, keeping the order of first appearance.
- `E` = `entities`.

### 2.2 Sub-queries

Each token is quoted for FTS5 (`"token"`, with internal `"` doubled). Empty sub-queries are skipped.

| id | FTS5 MATCH expression | Purpose |
|---|---|---|
| q_terms | `terms : ("t1" OR "t2" …)` over `T` | vocabulary overlap |
| q_subject | `subject : ("s1" OR "s2" …)` | same topic wording |
| q_claim | `{claim conditions} : ("c1" OR "c2" …)` | statement wording |
| q_alias | `{aliases quotes} : ("a 1 phrase" OR …)` (phrases) | user/source wording |
| q_entities | `entities : ("e1" OR …)` | same ticker/event |
| q_agent_i | each `fts_queries[i]` from a Query Card, run as given; on FTS syntax error → skip, add warning | agent-crafted |

Each sub-query: `SELECT rowid, bm25(knowledge_cards_fts, 3.0, 2.0, 1.0, 4.0, 1.5, 1.0, 0.5) AS s FROM knowledge_cards_fts WHERE knowledge_cards_fts MATCH ? ORDER BY s LIMIT 50` (column weights in schema order: subject, claim, conditions, terms, aliases, entities, quotes).

### 2.3 Fusion and filtering

1. Reciprocal Rank Fusion: `score(card) = Σ_q 1 / (60 + rank_q(card))` over sub-queries where the card appears (rank starts at 1).
2. Join `knowledge_cards` and keep `status = 'active'`.
3. Apply filters (search only): `kind`, `domain`, `category`, `horizon`, `instruments` (any overlap), `person_id` (card has a citation by that person), `evidence_level_min` (ordered anecdotal < claimed < backtested < audited), `min_persons` (from `card_stats`).
4. Dedup only: exclude cards created in the same run from the same content and segment (they were split from the same quote on purpose) — they are still returned under `siblings` for reference.
5. Return the top `limit` with: full card, `card_stats`, up to 2 citations (highest attribution confidence), and `score_debug` (`{q_terms: rank, q_subject: rank, …}`).

The algorithm must be stable: same DB + same input → same output order (ties broken by card id ascending).

---

## 3. Deduplication (`knowledge-dedup`)

### 3.1 Procedure (agent, per chunk)

```
1. kb card candidates --file chunk_NNN.cards.json --limit 10
2. For each new card i, read it next to its candidates. For each candidate decide one of:
      same        same claim, same conditions, same action/direction  (wording may differ)
      refines     same claim; the new card adds conditions, numbers, variants or exceptions
      related     same subject or setup family, different claim
      contradicts same conditions, opposite or incompatible action/outcome
      unrelated   ignore
3. Final decision for card i:
      any 'same'        → decision same,   target = the best 'same' candidate
      else any 'refines'→ decision refines, target = the best 'refines' candidate, with 'updates'
      else              → decision new | related | contradicts (insert), with links to every
                          related / contradicts candidate
4. Write chunk_NNN.decisions.json (array, schema §3.3) → kb card commit --file … --run R
5. On CONFLICT (target merged/retired meanwhile): re-run candidates for that card and decide again.
```

### 3.2 Decision rules

1. `same` requires: compatible `conditions`, same `action` (or both `NONE`), same `horizon` (or one is `n/a`), overlapping `instruments`. Same topic is never enough.
2. Opposite direction or incompatible outcome under the same conditions is `contradicts`, never `same`.
3. Different people stating the same claim → `same`. One card, many citations; `card_stats.persons` is the consensus.
4. When a candidate is broader and the new card is a special case with a different action → `related` with relation `example_of` or `refines` link, not a merge.
5. When unsure between `same` and `related` → choose `related`. A missed merge is cheap (the re-dedup sweep can merge later); a wrong merge loses information.
6. If there are no candidates: decision `new`, `candidate_ids: []`, rationale `"no candidates"`.

### 3.3 Decision JSON (`decision.schema.json`)

```json
{
  "new_card": { "...full card as in 02 §2.1, including citation..." },
  "candidate_ids": [41, 77],
  "decision": "refines",
  "target_card_id": 41,
  "updates": {
    "conditions_add": ["slower stocks use ma_20"],
    "numbers_set": {"trail_ma_slow": 20},
    "aliases_add": ["the 20"],
    "terms_add": ["ma_20"],
    "notes_append": "Variant: ma_20 for slower stocks (youtube:abc123def45).",
    "evidence_level_upgrade": null,
    "invalidation_set": null
  },
  "links": [
    {"to_card": 77, "relation": "related", "rationale": "Same setup family; 77 is the initial stop rule."}
  ],
  "rationale": "Same partial-then-trail rule as 41; new card adds the ma_20 variant for slower stocks."
}
```

### 3.4 Allowed `updates` (refines)

| Field | Effect | Constraint |
|---|---|---|
| `conditions_add` | append to `conditions_json` | ≤ 12 total |
| `numbers_set` | set keys in `numbers_json` | must not overwrite an existing key with a different value; conflicting numbers → put in `notes_append` instead |
| `aliases_add`, `terms_add`, `entities_add` | union | terms must exist in vocabulary |
| `notes_append` | append to `notes` with a newline | ≤ 500 chars total |
| `evidence_level_upgrade` | raise `evidence_level` | only upward |
| `invalidation_set` | set when currently null | |

`claim`, `subject`, `kind`, `action` are never changed by `refines`. If they need to change, the self-improver uses `kb card update` with a reason.

### 3.5 Few-shot decisions (`knowledge-dedup/references/decision_examples.md`, ≥ 10)

Required cases: same claim from two people (→ same); same rule with an added variant (→ refines); same setup, different exit (→ related); same conditions, opposite action (→ contradicts); general vs special case (→ related, `example_of`); same subject, different timeframe (→ related); paraphrase with different numbers (→ refines with `notes_append`, not `numbers_set`); no candidates (→ new); a candidate that is `merged` (→ CONFLICT handling); topic-only overlap (→ new).

---

## 4. Search (`knowledge-search`)

### 4.1 Procedure

```
1. Transform the question into a Query Card (02 §7) → data/work/<run>/q.json
2. kb card search --query-card q.json --limit 30
3. Read results. Drop irrelevant ones. Group by claim. Note contradictions (card_stats.contradictions > 0 →
   kb card get <id> --links to read the other side).
4. If fewer than 3 relevant cards: try once more with a rewritten Query Card (broader terms, more aliases).
5. If the user needs more context, kb content search "<phrase>" --content <content_id> and kb content view around the cited segment.
6. Answer (format §4.2).
7. If the answer is weak: kb gap add --query "<question>" --query-card q.json --verdict no_answer|weak_answer|conflicting
```

### 4.2 Answer format

For each claim used:
```
• <claim in plain English>
  Who: <person names> (consensus: N people, M sources) · Evidence: <evidence_level>
  Source: "<quote>" — <content title>, <url with timestamp, e.g. https://youtu.be/<id>?t=760>
  Contradicted by: <card ids / one-line summary> (if any)
```
Then a short synthesis. Never state a claim without a card behind it; if using general knowledge, say so.

URL with locator: YouTube `?t=<start_sec>`; Reddit comment permalink; page `#page=N` for PDFs; Discord message link `https://discord.com/channels/<guild>/<channel>/<message_id>`.

---

## 5. Person Matching (`person-matcher`)

### 5.1 `kb person candidates` scoring (script)

| Signal | Score |
|---|---|
| `alias_key` exact match on same platform | 1.0 |
| `alias_key` exact match on any platform (`platform = ''`) | 0.9 |
| source owner (`sources.person_id`) for the content's source | 0.9 |
| `persons_fts` match on name (bm25 rank 1) | 0.6 |
| `persons_fts` match on name (rank 2–5) | 0.4 |
| `--context` text mentions the canonical name | +0.1 |

Returns the top 5 with `reasons`.

### 5.2 Agent decision

1. Collect evidence: title ("ft.", "with", "interview", "×"), description, channel owner, self-introduction in the first segments ("I'm …", "my name is …"), host introductions ("today my guest is …"), byline, profile bio links.
2. Score ≥ 0.9 with consistent evidence → confirm. 0.6–0.9 → confirm only with a second independent signal. Otherwise → new person or `needs_review`.
3. A new person is created only if they state knowledge (would receive at least one citation) or own a source being crawled.
4. Write `person.json` (schema below) → `kb person upsert`; add aliases for every handle seen; `kb person appearance add` with `role`, `match_confidence`, `evidence`.
5. Confidence < 0.7 → `match_status = 'needs_review'`. The user reviews with `finsocnet persons review`.

### 5.3 `person.schema.json`

```json
{
  "id": "example-guest", "canonical_name": "Example Guest", "moniker": "ExampleG",
  "bio": "Prop trader since 2012; runs a small-cap desk.", "avatar_url": null,
  "trading_style": "Small-cap momentum, defense-first risk", "primary_markets": "US equities",
  "verified_records": null, "visibility": "public",
  "aliases": [{"alias": "@exampleg", "platform": "x"}, {"alias": "Example Guest", "platform": ""}]
}
```
`visibility = 'private_source'` for people whose only appearances are in closed groups/servers (Discord, private Facebook groups, Telegram private chats).

---

## 6. Speaker Attribution

Whisper and YouTube captions do not label speakers. The agent attributes segments while transforming.

1. Determine the cast from metadata (§5): owner, host, guests.
2. Solo content (one cast member) → everything is that person, confidence 0.95.
3. Interviews: questions and introductions → host; long first-person answers about their own trading → guest; use names in speech ("Thanks, Tim"), turn-taking, and topic continuity. Confidence 0.6–0.9.
4. Write attribution on the citation (`speaker`). Optionally record segment-level attribution for the whole chunk with `kb citation attribute` (later: `kb segment attribute` when diarization exists).
5. When `speaker_hint` (diarization) exists, map each `SPEAKER_n` to a person once per content and reuse it.
6. Confidence < 0.7 → appearance `needs_review`; the card is still committed.

Optional later script: `audio-transcriber --diarize` (whisperX/pyannote) fills `speaker_hint`. Not required for v2.

---

## 7. Person Rulebooks (`person-skill-synthesizer`)

### 7.1 Procedure

```
1. kb person cards <person_id>            → active cards with citations by this person, grouped by category
2. For each category with ≥ 1 card: write a person_skill JSON (§7.2)
     - content_markdown: rules in the person's logic order (screen → entry → manage → exit → risk → review)
     - every rule lists its card ids; no timestamps; no rule without a card
     - mention contradictions inside the person's own cards explicitly
3. Write an 'overview' row: style, markets, horizon, core edge in 5-10 lines, links to the other categories
4. Write a 'checklists' row derived from the rules (pre-market, entry, in-trade, review)
5. kb skill upsert --file … --run R (validator: card ids exist, are active, and cite this person; no timestamps)
```

### 7.2 `person_skill.schema.json` (example)

```json
{
  "person_id": "example-swing-trader",
  "skill_name": "example-swing-trader-core",
  "category": "trade_management",
  "title": "Trade management: partials and moving-average trails",
  "summary": "Sells 1/4-1/3 into strength after 3-5 days, trails the rest with the 10-day (20-day for slower names).",
  "content_markdown": "## Rules\n1. After 3-5 days in a breakout position, sell 1/4-1/3. (cards 41)\n2. Trail the remainder; exit on the first daily close below the 10-day MA; use the 20-day for slower stocks. (cards 41, 58)\n",
  "rules": [
    {"rule": "After 3-5 days, sell 1/4-1/3 of a breakout position.", "card_ids": [41]},
    {"rule": "Exit the remainder on the first daily close below the 10-day MA (20-day for slower stocks).", "card_ids": [41, 58]}
  ]
}
```

### 7.3 When to rebuild

- After a mining run that gave a person ≥ 5 new citations.
- After any merge/retire/update touching the person's cards (self-improver lists affected persons).
- On request: `/finsocnet:strategy <person> --rebuild`.

### 7.4 Exploring rulebooks (`person-skills-explorer`)

| Command | Behaviour |
|---|---|
| `kb skill get <person> --render markdown` | full rulebook (overview first) |
| `kb skill get <person> --category trade_management` | one section |
| `kb person list` | persons with `person_stats` |
| compare (agent procedure) | `kb skill get` for each person on the same category; agent writes a side-by-side table and cites card ids |
