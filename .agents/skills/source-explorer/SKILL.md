---
name: source-explorer
description: Run the FinSocNet exploration loop — take the next items from the explore queue (user seeds, knowledge gaps, people and books mentioned in content, browser history, cross-platform links, search results, source refreshes), dispatch each URL, handle or query to the right platform skill, ingest and mine what is fetched, and enqueue what it discovers. Use for "explore <trader/channel/url>", "find more sources about …", "keep crawling", scheduled /finsocnet:explore-step runs, or to fill open knowledge gaps.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI), the platform skills, and the agent browser for session platforms.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "5"
  spec: docs/spec/06-explore-improve-eval.md
---

# Source Explorer

> **Status: planned — built in Phase 5.**

## One explore step (safe to repeat and to run in parallel)

1. `kb run start --skill source-explorer --goal "explore step" …` → `R`.
2. `uv run finsocnet kb queue next --limit 5` → items (now `in_progress`). The script already skips items whose `not_before` is in the future, platforms with no budget left, and session platforms that are not `logged_in`.
3. For each item:
   a. Choose the skill with `references/dispatch.md` (URL pattern → skill · subcommand).
   b. Run the action (`fetch` with `--ingest --run R`, `list` with `--enqueue --save-cursor --run R`, `profile --ingest`, or `search`).
   c. Handle the result:
      - **fetch** → content stored; run `market-idea-miner` on it now (default) or leave it `new` when the step is "fetch only".
      - **list** → unknown items were enqueued; mark obviously irrelevant ones `skipped` with a reason (never silently drop them).
      - **profile** → `person-matcher` on the profile; if the source is relevant, enqueue `crawl_source` for it.
      - **search** → enqueue the promising results with a priority and one-line reason.
   d. `kb queue update <id> --status done|failed|deferred [--retry-after S] [--error "…"] --run R`.
4. Errors: exit 3 → `session-bridge` procedure; exit 4 → `deferred` with `retry_after_sec`; exit 5 → `failed`; exit 7 → `agent-browser start`, retry once.
5. Gaps touched in this step: re-run the gap's Query Card (`kb card search`). Good answer → `kb gap update <id> --status filled --filled-by <card ids>`.
6. `kb run end --run R --outcome success --stats '{"items": N, "fetched": N, "mined": N, "enqueued": N}'`.

## Seeding the queue

| Source | How |
|---|---|
| user | `finsocnet explore add <url\|handle\|query\|person> [--priority 0.95]` |
| gaps | `kb gap list --status open` → write 1–3 search queries per gap → `kb queue add --target-kind query --origin gap --origin-ref gap:<id>`; `kb gap update <id> --status exploring` |
| history | `kb history pending --limit 200` → triage: creator pages, communities, articles → `kb queue add --origin history`, `kb history mark … --triage queued`; others → `--triage not_relevant` |
| crosslinks | links in known persons' bios/descriptions → `--origin person_crosslink` |
| refresh | `kb source list --status active` older than `refresh_hours` → platform `list --enqueue --save-cursor` |

## Priorities (0..1, set by you with a reason)

user 0.95 · gap asked ≥ 2 times 0.85 · open gap 0.75 · new content of a high-consensus person 0.7 · mentor/influence named by a known person 0.65 · book/paper cited by a known person 0.6 · crosslinked platform 0.55 · history entry 0.5 · generic search result 0.3–0.5 · source refresh 0.4.

## Scheduling

Claude Code: `/loop 30m /finsocnet:explore-step` or a scheduled routine. Other harnesses: their scheduler, or cron running the harness CLI with "Run one source-explorer step".
