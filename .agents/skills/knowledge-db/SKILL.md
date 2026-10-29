---
name: knowledge-db
description: The FinSocNet database CLI (`finsocnet kb`) over the single SQLite file data/knowledge.db — runs, contents and segments, Knowledge Cards, citations, vocabulary, persons, person rulebooks, explore queue, gaps, lessons, feedback, backups, migrations and stats. Use whenever another FinSocNet skill needs to read or write data, to check database health or statistics, to back up or migrate the database, or to start and end an agent run. SQLite only, no vector store.
license: MIT
compatibility: Requires the FinSocNet repository with uv, Python ≥ 3.11 and SQLite ≥ 3.38 (FTS5 + JSON1).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P0"
  status: ready
  phase: "0"
  spec: specs/01-database.md
---

# Knowledge DB (`finsocnet kb`)

One SQLite file, `data/knowledge.db`, holds everything: relational tables plus FTS5 full-text indices. Embeddings of English text live in the `embeddings` table (no Chroma, no second store, ADR-009). Semantic judgment (same / refines / related) is still yours, never a similarity threshold.

## When to use

- Any FinSocNet workflow: start/end a run, store content, validate/commit cards, look up vocabulary, manage persons, queue exploration.
- "How big is the knowledge base?", "show stats", "back up the database", "migrate the database", "is the DB healthy?".

## Rules

1. Every workflow starts with `kb run start` and ends with `kb run end`. Every write command needs `--run <run_id>` (or `FINSOCNET_RUN_ID`).
2. Never write to `knowledge.db` with raw SQL or `sqlite3`, and never write a populate script that holds names, texts, quotes or URLs from memory. Read-only `sqlite3` queries for debugging are fine. Report completeness from `kb audit`, not from your own summary (`docs/agent-guide.md`).
3. Never delete contents, segments, citations or decisions. Use statuses (`retire`, `fail`, `merged`).
4. Every command prints one JSON envelope: `{"ok", "command", "data", "warnings", "meta"}` or `{"ok": false, "error": {"code", "message", "hint"}}`. Read `error.hint` before retrying.
5. Before any migration, a backup is made automatically; still confirm with the user before migrating the real database.

## Commands

All commands: `uv run finsocnet kb <group> <command> …` (same as `uv run .agents/skills/knowledge-db/scripts/kb.py …`). W = write, needs `--run`.

| Group | Commands |
|---|---|
| admin | `init`, `migrate [--dry-run]`, `backup [--to PATH]`, `doctor`, `stats`, `query --sql "SELECT …"` (read-only SQL for anything the other commands do not show), `schema [--table T]`, `audit [--limit N]` (completeness and provenance: cards without a fetched source, thin links, people without cards, per-person backlog, todo list; **the numbers to report**), `prune [--dry-run]` |
| run | `run start --skill S --goal G --harness H --model M [--parent R]` → `{run_id}`; `run end --run R --outcome success\|partial\|failed\|aborted [--stats JSON]`; `run list` |
| lesson / feedback | `lesson add --skill S --kind K --observation T [--evidence] [--proposal]` W; `lesson list\|update`; `feedback add\|list\|handle` |
| source | `source upsert --file F` W; `source get\|list [--no-person] [--search T]`; `source cursor ID --set C` W |
| content | `content add --file F` W; `get ID`; `view ID [--from-seq A --to-seq B]`; `chunks ID [--max-chars 12000] [--overlap 2]`; `list [--status] [--platform] [--type T] [--provenance fetched\|missing\|metadata_only] [--search T]`; `claim ID` W; `done ID --upto-seq N --cards N` W; `fail ID --error T` W; `link-duplicate ID --of OTHER` W; `search "<text>" [--content ID] [--person P]` |
| vocab | `vocab lookup "<phrase>"`; `vocab add --file F` W; `vocab update\|merge` W; `vocab list\|export` |
| person avatar | `person avatar add --person P (--url U \| --file F) [--kind avatar\|banner\|photo\|logo] [--platform X] [--primary]` W; `person avatar fetch --person P` W (downloads known avatar URLs); `person avatar list --person P` |
| seen | `seen check KEY…`; `seen mark --key K --status seen\|queued\|fetched\|skipped\|failed [--note N]` W; `seen list [--platform --status --source]`; `seen stats` (items the explorers looked at) |
| embed | `embed status`; `embed sync [--kinds card,person,skill,segment] [--limit N]`; `embed query --text T [--kinds card]` (English text; nearest rows) |
| translate | `translate detect-pending`; `translate set-language --file F` W; `translate pending [--content C]`; `translate put --file F` W; `translate get C [--seq N]` (the agent detects and translates, see skill `translator`) |
| card | `card validate --file F`; `card candidates --file F [--limit 10]`; `card commit --file F` W; `card search --query-card F \| --text Q [--mode auto\|lexical\|semantic\|hybrid]`; `card get ID [--citations --links --history]`; `card list`; `card update\|merge\|retire\|undo` W; `card link\|unlink --from A --to B [--relation related] --reason R` W (add or remove one link after the fact; snapshots card A first); `citation attribute ID --person P --role R --confidence C` W |
| decision | `decision list [--reviewed none]`; `decision review ID --verdict agreed\|overturned` W |
| person link | `person link add --file F [--person P]` W (links with evidence/confidence; platform+handle also becomes an alias); `person link list --person P [--all]`; `person link remove --person P --url U` W |
| person | `person candidates\|upsert\|get\|cards\|merge`; `person list [--class C] [--search T] [--no-cards] [--no-sources] [--missing avatar\|bio\|homepage\|links\|…] [--sort cards\|name\|sources\|recent]`; `person classes` (the static classification, `other` is the catch-all); `person coverage ID` (what we hold and the `gaps` to fill); `person alias add\|remove`; `person appearance add\|list\|remove` ; `person remove ID --reason R` (refused when cited: merge) — writes W |
| skill | `skill upsert\|get\|list` (person fields: profession, affiliation, domains, homepage, relevance, external_ids) |
| queue / gap / history | `queue add\|next\|update\|list\|remove`; `gap add\|list\|update`; `history pending\|mark` |

Full reference with outputs: `specs/01-database.md` §6.

## Procedures

**Health check**
1. `kb doctor` — expect `integrity: ok` and every FTS table `ok`.
2. If an FTS table is not ok: `kb doctor --repair-fts` (rebuilds from source tables), then `kb doctor` again.
3. Report `kb stats` to the user in a short table.

**Migration**
1. `kb migrate --dry-run` and show the pending list to the user.
2. After approval: `kb migrate`. A backup path is printed; tell the user where it is.
3. `kb doctor`.

## Error codes

| Exit | Code | Do |
|---|---|---|
| 2 | `RUN_REQUIRED`, `USAGE` | add `--run` / fix arguments |
| 6 | `VALIDATION_ERROR`, `VOCAB_UNKNOWN`, `QUOTE_NOT_FOUND`, `GRAMMAR_ERROR` | fix the JSON using `error.details[].suggestion` |
| 8 | `CONFLICT` | refetch (e.g. rerun candidates) and decide again |
| 1 | `INTERNAL` | `kb lesson add --kind script_bug` with the error, continue with the next item |

## Why SQLite only

See `specs/README.md` ADR-001 and ADR-009: one transaction for card + citations + links + index + decision, no second store to drift, the vocabulary-based card format makes lexical search work, and the agent makes the semantic decisions. Do not add Chroma, faiss, a vector extension or torch.
