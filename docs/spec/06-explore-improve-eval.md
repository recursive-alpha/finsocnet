# 06 — Exploration, Self-Improvement and Evaluation

These three skills close the loop: search finds gaps, exploration fills them, evaluation measures quality, and the self-improver turns lessons into better data and better instructions.

---

## 1. `source-explorer`

### 1.1 Responsibilities

- Own the exploration frontier (`explore_queue`).
- Turn gaps, mentions, history and crosslinks into queue items with a priority and a reason.
- Pick the next items, dispatch each to the right platform skill, and hand fetched content to `market-idea-miner`.
- Keep sources fresh (`source_refresh`).

### 1.2 Commands used

`kb queue add|next|update|list`, `kb gap list|update`, `kb history pending|mark`, `kb source list|cursor`, `kb content list --status new`, platform `search/profile/list/fetch`.

### 1.3 Dispatch rules (`.agents/skills/source-explorer/references/dispatch.md`)

| URL / target pattern | Skill · subcommand |
|---|---|
| `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | youtube-extractor · fetch |
| `youtube.com/@…`, `/channel/UC…`, `/c/…` | youtube-extractor · profile, then list |
| `x.com/<h>/status/<id>`, `twitter.com/…/status/…` | x-explorer · fetch |
| `x.com/<h>` | x-explorer · profile, list |
| `reddit.com/r/<s>/comments/<id>` | reddit-explorer · fetch |
| `reddit.com/r/<s>`, `reddit.com/user/<u>` | reddit-explorer · profile, list |
| `medium.com/…` with 12-hex suffix | medium-explorer · fetch |
| `*.substack.com/p/…` or custom domain with `/p/` and Substack markers | substack-explorer · fetch |
| `discord.com/channels/…`, `discord.gg/…` | discord-explorer |
| `t.me/<c>`, `t.me/s/<c>` | telegram-explorer |
| `*.stackexchange.com/questions/…`, `stackoverflow.com/questions/…` | stackexchange-explorer · fetch |
| host in `config/forums.yaml` | forum-explorer |
| `tradingview.com/chart/…` (ideas), `/script/…` | tradingview-explorer · fetch |
| `facebook.com/groups/…`, `fb.com/…` | facebook-explorer |
| `sec.gov/…` | sec-edgar-explorer |
| `arxiv.org/abs|pdf/…` | paper-code-explorer · fetch |
| `ssrn.com/abstract=…`, `doi.org/…`, `openalex.org/…` | research-explorer · fetch |
| `github.com/<o>/<r>` | github-explorer |
| `bsky.app/profile/…` | bluesky-explorer |
| podcast feed URL / `podcasts.apple.com/…` | podcast-explorer |
| `stocktwits.com/…`, `tiktok.com/…`, `instagram.com/…`, `threads.net/…`, `linkedin.com/…`, `seekingalpha.com/…`, `news.ycombinator.com/item?id=…` | P3 skills |
| URL ending `.pdf`, `.epub`, `.docx` | document-reader · fetch |
| any other URL | web-reader · discover, then fetch |
| `target_kind = query` | web-searcher / google-searcher (agent chooses) → enqueue results |
| `target_kind = person` | profile on every known platform of the person; web search for other platforms |
| `target_kind = book` | annas-archive-explorer search → agent picks edition → download |

### 1.4 Explore step (agent procedure)

```
1. kb run start --skill source-explorer --goal "explore step"
2. kb queue next --limit 5
3. For each item:
   a. choose the skill with the dispatch rules (or the item's platform)
   b. run it (profile/list/fetch/search as the item's action says), with --ingest for fetch
   c. results:
        fetch      → content stored → run market-idea-miner on it (03 §1) now, or leave status=new for a miner run
        list       → enqueue unknown items (agent filters obviously irrelevant ones, but records them as 'skipped'
                     rather than dropping them, so the decision is visible)
        profile    → kb source upsert; person-matcher; enqueue crawl of the source if relevant
        search     → enqueue results the agent judges promising (priority by relevance)
   d. kb queue update <id> --status done|failed|deferred [--retry-after S]
4. Error handling: exit 3 → re-export protocol (04 §5); exit 4 → deferred with retry_after; exit 5 → failed; exit 7 → start browser and retry once
5. kb run end
```

### 1.5 Priority guidance (agent-assigned, 0..1)

| Situation | Priority |
|---|---|
| user request (`origin=user`) | 0.95 |
| open gap asked ≥ 2 times | 0.85 |
| open gap | 0.75 |
| new content from a person with high consensus (≥ 10 cards cited by others too) | 0.7 |
| person newly mentioned by a known person as a mentor/influence | 0.65 |
| book or paper cited by a known person | 0.6 |
| crosslinked platform of a known person | 0.55 |
| history entry pointing to a creator/source page | 0.5 |
| generic search result | 0.3–0.5 |
| source refresh (new uploads since cursor) | 0.4 |

### 1.6 Seeds

- **User:** `finsocnet explore add <url|handle|query|person> [--priority]` → `origin=user`.
- **Gaps:** for each open gap the agent writes 1–3 search queries (web/Google/platform search), marks the gap `exploring`, and links queue items with `origin_ref = gap:<id>`. After each exploration batch, the agent re-runs the gap's Query Card; if it now finds good cards → `kb gap update --status filled --filled-by …`.
- **History:** `kb history pending --limit 200` → the agent triages in bulk (creator pages, trading communities, articles → `queued` with a queue item; others → `not_relevant`). Nothing is deleted.
- **Mentions** from the miner (03 §1.1 step 6).
- **Crosslinks:** profile bios and description links of known persons.
- **Source refresh:** a scheduled run lists every `active` source whose `last_crawled_at` is older than its refresh interval (`config/platforms.yaml: refresh_hours`, default 24 h for social, 168 h for blogs/forums) with `--enqueue`.

### 1.7 Scheduling

Harness-specific; examples:
- Claude Code: `/loop 30m /finsocnet:explore-step` or a scheduled routine.
- Cron on the remote host invoking the harness CLI in non-interactive mode with the prompt "Run one source-explorer step".
The skill must be safe to run repeatedly and concurrently (queue `next` marks items `in_progress`; content `claim` prevents double mining).

---

## 2. `self-improver`

### 2.1 Inputs (signals)

| Signal | Query |
|---|---|
| failed or partial runs | `kb run list --since 7d` (outcome ≠ success) |
| open lessons | `kb lesson list --status open` |
| user feedback | `kb feedback list --status open` |
| weak/no-answer gaps | `kb gap list --status open` |
| dedup disagreements | re-dedup sweep (§2.3) → `kb decision list --reviewed overturned` |
| validation error patterns | runs' `errors_json` grouped by code |
| vocabulary health | near-duplicate terms (same label after normalization; alias owned by two terms), unused terms (> 90 days, 0 cards), heavily used aliases missing from vocabulary (alias strings frequent in cards' `aliases_json` but absent from `vocabulary.aliases_json`) |
| eval results | `finsocnet eval run --all` (§3) |

### 2.2 Actions

| Kind | Allowed changes | How |
|---|---|---|
| `data_fix` | merge/split/retire/update cards, fix citations' attribution, merge persons | `kb card merge|retire|update`, `kb citation attribute`, `kb person merge`; each with `--reason` referencing the lesson/feedback id; reversible through `card_history` |
| `vocabulary` | add aliases, add terms, set `broader`, merge duplicate terms | `kb vocab add|update|merge` |
| `few_shot` | add/replace examples in `references/examples.md`, `decision_examples.md`, `query_examples.md` | git branch + eval report (§2.4) |
| `instruction` | edit SKILL.md procedures | git branch + eval report |
| `script_bug` / `platform_change` | fix adapters (selectors, endpoints), validators | git branch + tests + eval report |

### 2.3 Re-dedup sweep

1. Sample N = 30 recent `dedup_decisions` (stratified by decision type).
2. For each, rebuild the input (new card + candidate cards as they were — from `new_card_json` and `card_history` snapshots) and decide again **without looking at the stored decision**.
3. Compare. Agreement → `kb decision review <id> --verdict agreed`. Disagreement → think again with both rationales; if the new decision is better → `overturned` + `data_fix` (e.g. merge or split) + a lesson; if the old one stands → `agreed`.
4. Agreement rate is reported in the run stats; < 85% → lesson of kind `few_shot` for `knowledge-dedup`.

### 2.4 Proposal workflow (instruction/few-shot/script changes)

```
1. git switch -c self-improve/<YYYYMMDD>-<topic>
2. finsocnet eval run --all --out data/work/<run>/eval_before.json        (on the current instructions)
3. make the change (one topic per branch)
4. finsocnet eval run --all --out data/work/<run>/eval_after.json
5. accept only if the target set improves and no other set drops by more than 2 points
6. write docs/improvements/<YYYYMMDD>-<topic>.md: lesson ids, change summary, before/after table
7. commit; kb lesson update <ids> --status proposed --ref <branch>
8. tell the user the branch name and the before/after table; never merge yourself
```
Never edit eval golden cases in the same branch as the instructions they test.

### 2.5 Run cadence

- After every 20 mining runs or daily, whichever comes first (scheduled like the explorer).
- On demand: `/finsocnet:improve`.

---

## 3. Evaluation (`evals/`, `finsocnet eval`)

### 3.1 Layout

```
evals/
  transform/<case_id>/input.json         # {content_id?, chunk_view: "…", cast: […], platform}
  transform/<case_id>/expected.json      # expected cards (partial match rules below)
  dedup/<case_id>.json                   # {new_card, candidates: [cards], expected_decision, expected_target?}
  search/<case_id>.json                  # {question, expected_card_refs: [...], must_not: [...]} over evals/search/fixture_db.sql
  attribution/<case_id>.json             # {chunk_view, cast, expected: {seq: person_id}}
  README.md                              # how to add cases
```
Minimum sizes before Phase 5 is done: transform 30, dedup 40, search 30, attribution 15. Cases are hand-checked by the user (golden).

`evals/search/fixture_db.sql` creates a small DB (≈ 300 cards with citations and vocabulary) so search evals are independent of the live DB. Card references in search cases use stable `fixture_key`s stored in the fixture cards' `notes`.

### 3.2 Running

```
finsocnet eval prepare <set> --out data/work/<run>/eval_inputs/      # writes one input file per case
# the harness agent produces outputs following the CURRENT skill instructions:
#   transform → <case>.cards.json, dedup → <case>.decision.json, search → <case>.query_card.json (+ its chosen card ids),
#   attribution → <case>.attribution.json
finsocnet eval score <set> --outputs data/work/<run>/eval_outputs/ [--out report.json]
finsocnet eval run --all        # convenience: prints the prepare → produce → score steps for the agent to follow
```
`eval` scripts never call an LLM (ADR-002); the agent produces outputs, scripts score them.

### 3.3 Scoring (deterministic)

| Set | Metric | Definition |
|---|---|---|
| transform | card recall / precision | expected card matched when `kind`, `category`, `action` equal and ≥ 60% of expected `terms` present and quote overlaps the expected segment; unmatched produced cards count against precision |
| transform | validity | % of produced cards passing `kb card validate` (target 100%) |
| transform | no-card accuracy | cases expecting `[]` that produced `[]` |
| dedup | accuracy | decision equals expected (and target equals when given) |
| dedup | wrong-merge rate | expected `new/related/contradicts` but produced `same/refines` (most important; target < 3%) |
| search | recall@10, MRR | over expected card refs using `kb card search` with the produced Query Card, plus the agent's final selection |
| attribution | accuracy | per segment with an expected speaker |

Reports: `{set, n, metrics, failures: [{case, reason}]}`. `kb lesson add` is created automatically by the agent for each failure cluster.

### 3.4 Targets (v2 acceptance)

| Metric | Target |
|---|---|
| transform validity | 100% |
| transform recall | ≥ 0.80 |
| transform precision | ≥ 0.75 |
| dedup accuracy | ≥ 0.85 |
| dedup wrong-merge rate | ≤ 0.03 |
| search recall@10 | ≥ 0.80 (ADR-001 revisit threshold) |
| attribution accuracy | ≥ 0.85 |
