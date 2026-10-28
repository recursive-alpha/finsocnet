---
name: github-explorer
description: Explore GitHub repositories on any topic (trading strategies, backtests and quant research included) — search by optional topic and language, read READMEs, list a repository's files, read selected source files as code segments — and store them as FinSocNet content so strategy logic becomes Knowledge Cards. Use for github.com links, "code for this strategy", repos linked from papers or creators.
license: MIT
compatibility: FinSocNet repository with httpx; GITHUB_TOKEN optional (rate limit).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "6"
  spec: specs/05-platform-skills.md
---

# GitHub Explorer

You choose which files to read: `tree` lists them, `fetch <repo>:<path>` reads one. Read strategy/signal/backtest files, skip boilerplate.

## When to use

- GitHub repo URLs, code behind a paper or creator.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/github-explorer/scripts/github.py
uv run $S search "<query>" [--topic algorithmic-trading] [--language python] [--limit 30]
uv run $S profile <user> [--ingest]
uv run $S tree <owner/repo> [--branch B]
uv run $S fetch <owner/repo> [--ingest]
uv run $S fetch <owner/repo>:<path> [--ingest]
```

| Command | Returns |
|---|---|
| `search "<query>"` | repositories by stars |
| `profile <user>` | user/org |
| `tree <owner/repo>` | file list with sizes |
| `fetch <owner/repo>` | README paragraphs |
| `fetch <owner/repo>:<path>` | file as ≤ 60-line code segments |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill github-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Repo: `fetch <repo> --ingest` → `tree` → pick strategy files → `fetch <repo>:<path> --ingest --run R` → market-idea-miner (`--max-chars 6000`).
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `github:<owner>/<repo>`, `github:<owner>/<repo>:<path>@<sha7>` |
| content_type | `repo`, `file` |
| segments | README paragraphs; code `kind=code {path, line_start, line_end}` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill github-explorer --kind script_bug …` with the error, then report |

## Notes

- Reproducible backtest results in the repo → `backtested`, otherwise `claimed`.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
