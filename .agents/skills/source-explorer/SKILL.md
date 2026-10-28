---
name: source-explorer
description: Run the FinSocNet exploration loop — take the next items from the explore queue (user seeds, knowledge gaps, people and books mentioned in content, browser history, cross-platform links, search results, source refreshes), dispatch each URL, handle or query to the right platform skill, ingest and mine what is fetched, and enqueue what it discovers. Use for "explore <trader/channel/url>", "find more sources about …", "keep crawling", scheduled /finsocnet:explore-step runs, or to fill open knowledge gaps.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI), the platform skills, and the agent browser for session platforms.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "5"
  spec: specs/06-explore-improve-eval.md
---

# Source Explorer

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
   c2. **Visited items.** Platform scripts record every item they show you in `seen_items` (when a run id is given): `search`/`list` print `visited` (`null|seen|queued|fetched|skipped|failed`) and `seen_count` per item and `known` is true for stored, fetched or skipped items. Add `--new-only` to hide those. When you judge an item irrelevant, say so once so it never comes back: `kb seen mark --key <item id> --status skipped --note "<why>" --run R`. `kb seen check <key>…`, `kb seen list --status skipped`, `kb seen stats` answer "did we look at this already?".
   d. `kb queue update <id> --status done|failed|deferred [--retry-after S] [--error "…"] --run R`.
4. Errors: exit 3 → `session-bridge` procedure; exit 4 → `deferred` with `retry_after_sec`; exit 5 → `failed`; exit 7 → `agent-browser start`, retry once.
5. Gaps touched in this step: re-run the gap's Query Card (`kb card search`). Good answer → `kb gap update <id> --status filled --filled-by <card ids>`.
6. `kb run end --run R --outcome success --stats '{"items": N, "fetched": N, "mined": N, "enqueued": N}'`.

## A person's profile URL

A queue item with `origin_ref=person-explore` (added by `finsocnet explore add <profile url> --person`), or a user message such as "explore this person: <url>", is not a single fetch: hand it to the skill `person-explorer`, which resolves the profile, creates or matches the person, profiles them, lists everything they published, mines the most important content and reports. Mark the queue item `done` when it reports.

## People first

Content is explored because of who publishes it. When a seed is (or reveals) a person, a field or a profession ("famous portfolio managers", "professors of asset pricing", "<name>"), run `people-discoverer` before the platform skills: it finds the people in scope (traders, PMs, investors, executives, economists, professors, authors, journalists, regulators), creates them with `profession`/`affiliation`/`relevance`, links their channels, accounts, sites and papers as sources, and queues them with `origin=person_crosslink` (`origin_ref=person:<id>`). A channel, account or blog found by search that has no person yet gets one through `person-matcher` after its `profile --ingest` when the owner is identifiable and in scope; never leave a crawled source without trying to attach it to a person. `list --catalog` discovers everything a source published; fetch and mine only what the person is known for first.

## Seeding the queue

| Source | How |
|---|---|
| user | `finsocnet explore add <url\|handle\|query\|person> [--priority 0.95]` |
| gaps | `kb gap list --status open` → write 1–3 search queries per gap → `kb queue add --target-kind query --origin gap --origin-ref gap:<id>`; `kb gap update <id> --status exploring` |
| history | `kb history pending --limit 200` → triage: creator pages, communities, articles → `kb queue add --origin history`, `kb history mark … --triage queued`; others → `--triage not_relevant` |
| person profile | `finsocnet explore add <profile url> --person` → `person-explorer` |
| people | `people-discoverer` for a field, profession or name → `--origin person_crosslink --origin-ref person:<id>` |
| crosslinks | links in known persons' bios/descriptions → `--origin person_crosslink` |
| refresh | `kb source list --status active` older than `refresh_hours` → platform `list --enqueue --save-cursor` |

## Discovering communities, channels and threads on any topic

There is **no topic limit** in exploration: a seed can be a hobby, a language, a country, a profession, a niche. Finance is the default interest of the card miner, not a filter on what the explorers may find, store or follow (everything fetched is stored, "nothing ignored"; `market-idea-miner` writes cards only where there is finance knowledge, and every segment stays searchable by text and, once translated, by meaning).

For a topic `T` (free text, any language) run the discovery recipe, enqueue what looks alive, and let normal explore steps do the rest:

| Where | Command (every one is `--run R`, `--new-only` hides what you already saw) |
|---|---|
| Reddit communities | `reddit.py search "T" --type sr` → `reddit.py list r/<name> --sort top --t month` |
| YouTube channels | `youtube.py search "T" --type channel`, then `list --tab all` |
| Podcasts | `podcast.py search "T"` |
| Stack Exchange (any of its ~180 sites) | `stackexchange.py search "T" --site <slug>`; the site list is at stackexchange.com/sites |
| Forums (any engine) | `web_search.py search "T forum"` → `forum.py detect <url>` → `forum.py list <board>` |
| Newsletters / blogs | `substack.py search "T"`, `medium.py search "T"`, `rss.py discover <site>` |
| Telegram / Discord / Facebook groups | `web_search.py search "T site:t.me"`, `"T discord invite"`, `"T site:facebook.com/groups"`; then the platform skill (sessions where needed) |
| Code and papers | `github.py search "T"` (no topic filter unless you pass `--topic`), `research.py search "T"`, `papers.py search "T"` |
| Anything else | `web_search.py search "T"` / `google.py search` → `web.py fetch` |

Steps: (1) pick the communities with the most activity and the most distinct authors, not the biggest; (2) `kb queue add --target <url|handle> --origin search_result --action crawl_source --reason "<why>" --priority 0.4..0.6`; (3) for a thread or channel that proves empty or off-purpose, `kb seen mark --key <id> --status skipped --note "<why>"` so the next discovery pass does not return to it; (4) when a topic needs people (experts, authors), run `person-matcher` on the authors who appear in several communities.

## Priorities (0..1, set by you with a reason)

user 0.95 · gap asked ≥ 2 times 0.85 · open gap 0.75 · new content of a high-consensus person 0.7 · mentor/influence named by a known person 0.65 · book/paper cited by a known person 0.6 · crosslinked platform 0.55 · history entry 0.5 · generic search result 0.3–0.5 · source refresh 0.4.

## Scheduling

Claude Code: `/loop 30m /finsocnet:explore-step` or a scheduled routine. Other harnesses: their scheduler, or cron running the harness CLI with "Run one source-explorer step".
