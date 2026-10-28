---
name: market-idea-miner
description: Mine one stored content item (video, podcast episode, thread, chat window, article, book, paper, filing, code) end to end — identify the people, transform each chunk into Knowledge Cards, attribute speakers, deduplicate against the knowledge base, commit, and enqueue mentioned people, books and links for exploration. Use after a platform skill fetched content, when the user says "mine this video/thread/book", "extract the rules from …", or /finsocnet:mine <content_id>.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI) and the knowledge-transformer, knowledge-dedup and person-matcher skills.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P0"
  status: ready
  phase: "1"
  spec: docs/spec/03-pipelines.md
---

# Market Idea Miner

Orchestrates other skills for one content item. It has no script of its own; every step is a `kb` command or another skill's procedure.

## Procedure

1. `kb run start --skill market-idea-miner --goal "mine <content_id>" --harness <h> --model <m>` → `R`.
2. `kb content claim <content_id> --run R` — on `CONFLICT` another run is mining it: stop.
3. `kb content get <content_id> --meta-only` — title, platform, source, author, duration, status. Status `metadata_only` → the text is not fetched yet: fetch it with the platform skill first, or stop.
4. **People first** (`person-matcher`): find owner/host/guests/author from title, description, source owner and the first segments. Confirm or create persons and appearances. You need the cast before attributing quotes.
5. `kb content chunks <content_id>` (default 12000 chars; books 8000; code 6000 via `--max-chars`). Chunks start after `processed_upto_seq`, so a resumed or extended content continues where it stopped.
6. For each chunk `NNN`:
   a. `kb content view <content_id> --from-seq A --to-seq B`
   b. `knowledge-transformer` → `data/work/R/<content-safe>/chunk_NNN.cards.json` → `kb card validate` until valid (or `[]` + skip file).
   c. `knowledge-dedup` → `chunk_NNN.decisions.json` → `kb card commit --run R`.
   d. `kb content done <content_id> --upto-seq B --cards <running total> --transformer kt-1.0 --run R` (checkpoint).
7. **Mentions**: collect people, books, papers, tools, channels and URLs worth exploring. For each: `kb queue add --target … --target-kind url|handle|person|book|paper|query --origin mention --origin-ref <content_id> --reason "<one line>" --priority <0..1> --run R`.
8. If any person gained ≥ 5 citations in this run, list them for `person-skill-synthesizer` (run it now if the user asked for rulebooks).
9. `kb run end --run R --outcome success --stats '{"chunks": N, "cards_new": N, "cards_merged": N, "skipped_chunks": N}'`.

## Errors

| Situation | Action |
|---|---|
| validator keeps rejecting a correct-looking card | commit the rest, `kb lesson add --skill knowledge-transformer --kind instruction --observation …` |
| content unreadable / wrong language / empty transcript | `kb content fail <id> --error "<reason>" --run R` |
| interrupted | rerun the same procedure; `claim` + `processed_upto_seq` + idempotent commits make it safe |

## Chunk sizes

| Content | `--max-chars` |
|---|---|
| transcripts, threads, chats | 12000 |
| books, long PDFs | 8000 |
| code (Pine, Python) | 6000 |
