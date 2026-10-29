# Agent guide: how to work in FinSocNet

Read this before any exploration, mining or population task, whatever harness you run in. It exists because earlier agent sessions reported "100% complete" while the data was thin or invented. The rules below are checked by `finsocnet kb audit` and by `kb card validate`; **your summary is not evidence, the audit is.**

## 1. The one idea

Scripts fetch, store and measure. **You read, judge and write.** Everything in the database must trace back to something a platform skill fetched (a page, a transcript, a PDF, an API record), and every claim you store must be checkable by a reviewer who only has the database.

## 2. What you must never do (each one happened)

| Never | Why | Instead |
|---|---|---|
| Write a `populate_*.py` (or any script) that holds names, "texts", quotes, URLs or cards you typed from memory | The text is yours, not the source's; quotes "verify" against your own text; reviewers cannot tell | Use the platform skill to fetch, then read what it stored |
| Open `data/knowledge.db` in a script (python/sqlite3), and above all `INSERT`/`UPDATE`/`DELETE` | Bypasses validation, runs, history, provenance | Read: `kb query --sql "SELECT …"`, `kb schema`, `kb person coverage ID`, the `list`/`get` commands. Write or remove: the typed `kb … --run R` commands only |
| Create a content with text you wrote (`fetch_method` empty) | `kb card validate` refuses citations to it; the audit lists it | Fetch it: `<skill> fetch <url> --ingest --run R`. If nothing can fetch it, store a `metadata_only` content and say so |
| Invent or guess a URL, handle, id, avatar or "official homepage" | A wrong link is worse than none | Open the page with a skill (`web.py fetch`, `search`, `profile`); store the evidence of what you saw |
| Write "verified", "official", "100%", "complete" without a number from `kb audit` | Unchecked claims hide gaps | Paste the audit numbers and list what is missing |
| Make cards from a title, an abstract, a book's metadata or a Wikipedia summary as if it were the work | A card must come from text of the work | Fetch the full text; abstract-only cards carry a lower `evidence_level` and say so in `notes` |
| Skip hard parts silently (DDoS check, login, bot check, paywall) | The user cannot act on silence | Report exit code 3/4/7 with the hint, and what is queued instead |
| Mark a person "complete" because every column is non-empty | Placeholder text fills columns | A field counts only if you can name the page that proved it |

## 3. Definition of done (measurable)

Run `uv run finsocnet kb audit --limit 30` before and after your task and include both in your report.

**A person is complete** when: `canonical_name`, `profession`, `affiliation`, `domains`, `homepage`, `relevance`, `bio` come from pages you opened; a primary avatar was fetched (`kb person avatar fetch`); at least 3 links with `evidence` that says what you saw (official site, one social account, one more place; or "not found: searched X, Y" in the run stats); every content place linked as a source with an `owner` appearance; `list --catalog` run on each content place; the best content fetched and mined into cards; a rulebook once there are 5+ cards.

**A source is explored** when its inventory is listed (`list --catalog`, all pages or `cap_reached` reported), the top items by popularity and by teaching value are fetched and mined, and the rest is queued (`kb queue add`), not forgotten.

**A book** is explored when a real edition was downloaded (`annas.py download`) and read with `document-reader` into chunks, and every chunk was mined or skipped with a reason. Metadata alone creates no card. A blocked download is reported (CHECKPOINT), not worked around.

**A paper** is explored when the full text (PDF/HTML) was fetched with `papers.py`/`research.py`/`document.py`, not only the abstract.

**A video or podcast** is explored when a transcript exists (captions, or `audio-transcriber`). No transcript: leave it `metadata_only`, record why (`caption_error`), queue it.

**A list task** ("Nobel laureates", "100 central bankers", "channels of traders") means: one `person` per row only after the gate (`relevance` sentence + verifiable fact), then the per-person loop above, **person by person**, newest to oldest if asked. 20 people done properly beat 100 stubs. Report progress as `done / total` from the audit, not from memory.

## 4. Depth and diversity

- Per person: at least 2 platforms and 2 content types where they exist (video, article, paper, podcast, book, talk), and at least 5 fetched contents mined before you move on to the next person, unless the person has less.
- Across the database: spread over professions (`kb person list --profession`), languages (translate with `translator`, never in a script), and regions. After each batch, look at `kb audit`: if one profession or platform dominates, aim the next batch elsewhere.
- Prefer primary sources: their own words (lectures, letters, speeches, filings, their site) over summaries about them.

## 5. The working loop

1. `kb run start --skill <skill> --goal "<one line>" --harness <h> --model <m>` → `R`; every write passes `--run R`; end with `kb run end --run R --outcome success|partial|failed --stats '{...}'` (real numbers).
2. Read the SKILL.md of every skill before you use it; the names and flags in this guide are the contract, `--help` is the truth.
3. Work in small batches (one person, one source, one book). After each batch: `kb card validate` → `kb card candidates` (dedup judgment: same / refines / related / contradicts / new) → `kb card commit` → `kb content done`.
4. Mind the platform limits: exit 3 = login/checkpoint (stop that platform, name the export), 4 = budget/rate (defer, `retry_after_sec`), 7 = browser (`agent_browser.py start` once), 6 = validation (read `error.details`, fix every item). Do not retry the same failing command more than twice.
5. Temporary files go to the scratchpad/temp directory you were given, never into the repo or `data/`.
6. Finish with a report: what changed (before/after audit numbers), what is blocked and why, what is queued next, doubts. No celebration, no tables of things you did not verify.

## 6. Delegating (omp, other harnesses)

Give each helper: the goal, the list of ids it owns (no overlap), the budget, the skills to read first, this guide, the report path. Ask it to be verbose (what and why before each step). Then **review**: run `kb audit`, open a sample of cards against `kb content view`, open a sample of links, read the event log for forbidden shortcuts (scripts, SQL, guessed URLs). Fix or retire what is wrong (`kb card retire`, `kb person link add` with `match_status: rejected|needs_review`) and say so in your report.

## 6b. Every database operation is a CLI command

| Need | Command |
|---|---|
| Any read the list/get commands do not cover | `kb query --sql "SELECT …" [--limit N]` (SELECT only, enforced by SQLite), `kb schema [--table T]` |
| What do we hold about this person / what is missing | `kb person coverage ID` (profile fields, links by kind, content by type listed/fetched/mined, cards, `gaps` = your to-do) |
| Who is missing something | `kb person list --missing avatar|bio|homepage|links|… --no-cards --no-sources --class X --search T` |
| The static classifications | `kb taxonomy [--entity people\|cards\|content\|sources\|skills\|vocab]` (fixed lists with counts; `kb person classes` for people). Never invent a class: use a listed value or `other` |
| Medium, not platform | Content and sources are classified by **medium** (`video`, `audio`, `article`, `social`, `paper`, `book`, `code`, `document`, `other`), derived from `content_type` (`video short stream episode article page post paper book repo file`). Platforms are free text and will grow: never put a platform in a list, and set `content_type` from the real thing (a podcast episode is `episode`, a newsletter post `article`, a tweet `post`) |
| Contents by provenance | `kb content list --provenance fetched|missing|metadata_only --type article|book|paper|video|… --person ID --search T` |
| Sources nobody owns | `kb source list --no-person` (also `--medium book`, `--kind channel`) |
| Update | `kb person upsert`, `kb person link add`, `kb person alias add`, `kb person appearance add`, `kb source upsert`, `kb card update`, `kb card retire`, `kb queue update` |
| Remove | `kb person link remove`, `kb person alias remove`, `kb person appearance remove`, `kb person remove` (refused when cited: `kb person merge`), `kb queue remove`; cards, contents, citations and decisions are never deleted (retire / `fail` / `merge`) |

If a command you need does not exist, say so in the report (a `script_bug`/`other` lesson: `kb lesson add`); do not write a script around the database.

## 7. Quick reference

```bash
S="uv run finsocnet kb"
$S audit --limit 30                              # completeness + provenance (trust this)
$S person candidates --name "…"                  # before creating anyone
$S person upsert --file p.json --run R           # profile fields
$S person link add --person ID --file l.json --run R
$S person avatar fetch --person ID --run R
$S source upsert --file s.json --run R           # {"id": …, "person_id": …}
<skill> list <target> --catalog --run R          # whole inventory, metadata only
<skill> fetch <url> --ingest --run R             # real text; sets fetch_method
$S content claim ID --run R; $S content chunks ID; $S content view ID --from-seq A --to-seq B
$S card validate --file cards.json; $S card candidates --file cards.json; $S card commit --file decisions.json --run R
$S content done ID --upto-seq B --cards N --run R
$S queue add --target … --origin person_crosslink --origin-ref person:ID --action fetch --reason "…" --run R
$S embed sync
```

See also: [`AGENTS.md`](../AGENTS.md) (rules), [`specs/16-people-first-discovery.md`](../specs/16-people-first-discovery.md), skills `person-explorer`, `people-discoverer`, `person-profiler`, `market-idea-miner`, `source-explorer` (with its `references/playbooks.md`).
