---
name: research-explorer
description: Search academic and practitioner finance research beyond arXiv — OpenAlex and Semantic Scholar (keyless APIs), SSRN and NBER working papers — read abstracts and authors, find open-access PDFs and ingest them with document-reader as FinSocNet content. Use for SSRN/NBER/DOI links, "is there research on …", academic evidence for a trading claim, author lookups.
license: MIT
compatibility: FinSocNet repository with httpx; agent-browser for SSRN; OPENALEX_MAILTO optional.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Research Explorer (SSRN, NBER, OpenAlex, Semantic Scholar)

> **Status: planned — built in Phase 6.** Nothing below runs yet; it is the contract the implementation must follow.

Complements paper-code-explorer (arXiv + code). Papers that test a claim give `backtested` evidence.

## When to use

- DOIs, SSRN/NBER links, evidence for a claim, finance researchers.

## Before you start

- Agent browser for SSRN.

## Commands

```bash
S=.agents/skills/research-explorer/scripts/research.py
uv run $S search "<query>" [--source openalex|s2|ssrn] [--year-from Y] [--limit 25]
uv run $S profile <author id|name> [--ingest]
uv run $S fetch <doi|ssrn url|openalex id> [--pdf] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | papers |
| `profile <author id|name>` | author works and topics |
| `fetch <doi|ssrn url|openalex id>` | metadata + abstract; `--pdf` ingests open-access full text |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill research-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Evidence for a gap or claim: `search` → choose → `fetch --pdf --ingest --run R` → market-idea-miner.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `paper:doi:<doi>`, `paper:openalex:<W…>`, `paper:ssrn:<abstract_id>`; arXiv papers keep `arxiv:<id>` |
| content_type | `paper` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill research-explorer --kind script_bug …` with the error, then report |

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
