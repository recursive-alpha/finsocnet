---
name: sec-edgar-explorer
description: Read SEC EDGAR filings — company and fund filings index by CIK, full-text search, 10-K/10-Q/8-K text, 13F-HR holdings of fund managers, N-CSR fund letters — and store them as FinSocNet content, so fund managers' holdings become audited evidence and shareholder letters become knowledge. Use for sec.gov links, CIKs, "what does <fund> hold", "<manager>'s 13F", fund letters.
license: MIT
compatibility: FinSocNet repository with httpx; SEC_USER_AGENT must be set (name + email), ≤ 10 requests/second.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# SEC EDGAR Explorer

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Official SEC APIs. Numbers from filings are `audited` evidence.

## When to use

- Fund managers, companies, filings, 13F holdings.

## Before you start

- `SEC_USER_AGENT` in .env.

## Commands

```bash
S=.agents/skills/sec-edgar-explorer/scripts/sec.py
uv run $S search "<query>" [--forms 10-K,13F-HR,N-CSR] [--limit 50]
uv run $S profile <cik|ticker|name> [--ingest]
uv run $S list <cik> [--forms 13F-HR] [--limit 40] [--enqueue]
uv run $S fetch <accession no|filing url> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | full-text search hits |
| `profile <cik|ticker|name>` | entity name, tickers, filings index |
| `list <cik>` | filings newest first |
| `fetch <accession no|filing url>` | filing text; 13F holdings table |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill sec-edgar-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Fund manager person: `profile <fund cik> --ingest` → link the source to the person → `list --forms 13F-HR --limit 8 --enqueue` → fetch → market-idea-miner (holdings become metric cards; update `persons.verified_records`).
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `sec:<accession_no>` |
| source id | `sec:cik:<cik10>` |
| content_type | `filing` |
| segments | paragraphs `{section?, para}`; 13F: one generated quotable paragraph per top-20 holding |
| extra | `form`, `period`, `holdings` (full table) |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill sec-edgar-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
