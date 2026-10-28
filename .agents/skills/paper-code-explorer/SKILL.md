---
name: paper-code-explorer
description: Search arXiv (q-fin, stat.ML, cs.LG) and Hugging Face / Papers With Code for quantitative finance and trading papers with open-source code, read abstracts and AI summaries, list trending papers, and download PDFs for document-reader. Use for arxiv.org links, "papers about market microstructure / momentum / RL trading", "is there code for this paper".
license: MIT
compatibility: FinSocNet repository with uv.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Paper & Code Explorer (arXiv)

Paper metadata and abstracts are stored as `metadata_only`; full text comes from `--pdf` → document-reader. Linked GitHub repos are enqueued for github-explorer.

## When to use

- arXiv ids/URLs, quant research topics, paper + code lookups.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/paper-code-explorer/scripts/papers.py
uv run $S search "<query>" [--has-code] [--category q-fin.TR] [--limit 20]
uv run $S fetch <arxiv id|url> [--pdf] [--ingest]
uv run $S trending [--limit 10] [--has-code]
```

| Command | Returns |
|---|---|
| `search "<query>"` | ItemRef[] `arxiv:<id>` |
| `fetch <arxiv id|url>` | metadata + abstract; `--pdf` downloads and ingests full text |
| `trending` | HF daily papers |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill paper-code-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. `search` → choose → `fetch --pdf --ingest --run R` → market-idea-miner.
3. Repos in `links` → `kb queue add --target <repo url> --origin citation`.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `arxiv:<id>` (no version; version in `extra.version`) |
| content_type | `paper` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill paper-code-explorer --kind script_bug …` with the error, then report |


## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
- `references/qfin_categories.md` — arXiv q-fin categories
