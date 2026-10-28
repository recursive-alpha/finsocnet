---
name: stackexchange-explorer
description: Search and read Stack Exchange Q&A — Quantitative Finance (quant), Personal Finance & Money (money), Stack Overflow (backtesting, pandas, trading APIs), Economics, Cross Validated (stats) and Data Science — questions, all answers with votes and accepted flags, code blocks and comments, plus user profiles, via the official Stack Exchange API. Use for stackoverflow.com or *.stackexchange.com links, quant questions, "how do quants handle …".
license: MIT
compatibility: FinSocNet repository with httpx; STACKEXCHANGE_KEY optional (raises quota from 300 to 10,000 requests/day).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "6"
  spec: docs/spec/05-platform-skills.md
---

# Stack Exchange Explorer (incl. Stack Overflow)

Official API, no browser. Honour `backoff` and stop when `quota_remaining` < 10.

## When to use

- Q&A on quant methods, backtesting, risk, personal finance, code.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/stackexchange-explorer/scripts/stackexchange.py
uv run $S search "<query>" [--site quant|money|stackoverflow|economics|stats|datascience] [--tagged t1;t2] [--accepted] [--limit 50]
uv run $S profile <user_id> --site S [--ingest]
uv run $S list <tag|user_id> --site S [--limit 100] [--enqueue]
uv run $S fetch <question url|id> --site S [--comments] [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | questions by votes |
| `profile <user_id> --site S` | user + top answer tags |
| `list <tag|user_id> --site S` | questions by tag or a user's answers |
| `fetch <question url|id> --site S` | question + all answers |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill stackexchange-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Topic: `search --site quant` → fetch the top questions `--ingest --run R` → market-idea-miner.
3. High-reputation answerer with many relevant answers → `profile` → person-matcher.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `stackexchange:<site>:<question_id>` |
| source id | `stackexchange:site:<site>`, `stackexchange:user:<site>:<id>`, `stackexchange:tag:<site>:<tag>` |
| content_type | `question` |
| segments | question `{post_id}`; answers `kind=answer {post_id, score, accepted}`; code blocks `kind=code {post_id, block}`; HTML → markdown |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill stackexchange-explorer --kind script_bug …` with the error, then report |

## Notes

- Answers with method + data → `backtested` evidence.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
