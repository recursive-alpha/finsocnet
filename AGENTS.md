# Agent Operating Guide

FinSocNet is an agent-operated knowledge network. **You are the only model in it**: scripts fetch, store, validate, search and score; you read, judge and write. The spec is the source of truth: [`specs/README.md`](specs/README.md) and [`specs/`](specs/). If code and spec disagree, the spec wins; if the spec is ambiguous, ask.

## What it does

1. **Discover** the people who publish finance and economics knowledge (traders, PMs, executives, economists, professors, authors: skill `people-discoverer`), then their sources on every platform.
2. **Capture** everything into one SQLite file, `data/knowledge.db` (relational tables + FTS5 + English embeddings stored as BLOBs; no separate vector store, ADR-009).
3. **Transform** content into **Knowledge Cards** (fixed schema, claim grammar, controlled vocabulary).
4. **Deduplicate** with your judgment (`same / refines / related / contradicts / new`), logged with a rationale.
5. **Serve** answers with citations, per-person rulebooks, consensus and contradictions.
6. **Improve**: failed searches become gaps, gaps drive exploration, lessons become reviewed changes.

## Rules you must follow

**Never:** add a separate vector database or a torch stack (ADR-001/009); detect languages or translate in a script (the agent does, skill `translator`) · call an LLM API from a script (ADR-002) · call `chromium.launch()` / `new_context()` (use the agent browser, ADR-006) · print, log or store cookie values or tokens · add username/password login (ADR-005) · create per-person folders under `.agents/skills/` · delete contents, segments, citations or decisions · write to `knowledge.db` with raw SQL · change the schema without a numbered migration and a backup · install, update or remove a skill without `skill-installer`'s review and the user's yes · edit an installed third-party skill in place · commit to `main` from the self-improver.

**Always:** start a workflow with `kb run start` and pass `--run <id>` to every write · validate agent-written JSON with `kb card validate` before committing · read `error.hint` before retrying · keep SKILL.md in step with the CLI.

## Skills (`.agents/skills/`)

| Group | Skills |
|---|---|
| Knowledge core | `knowledge-db` (the `kb` CLI), `knowledge-transformer`, `knowledge-dedup`, `knowledge-search`, `market-idea-miner`, `translator` |
| People | `people-discoverer` (people first: traders, PMs, executives, economists, professors, authors), `person-explorer` (start from one profile URL and complete everything), `person-profiler` (website, social accounts, newsletters, papers with evidence), `person-matcher`, `person-skill-synthesizer`, `person-skills-explorer` |
| Access | `session-bridge`, `agent-browser` |
| Loop | `source-explorer`, `self-improver`, `skill-installer`, `platform-skill-builder`, `finsocnet` |
| Video and audio | `youtube-extractor`, `audio-transcriber`, `podcast-explorer`, `tiktok-explorer` |
| Social | `x-explorer`, `reddit-explorer`, `bluesky-explorer`, `threads-explorer`, `instagram-explorer`, `facebook-explorer`, `linkedin-explorer`, `stocktwits-explorer`, `discord-explorer`, `telegram-explorer` |
| Writing | `medium-explorer`, `substack-explorer`, `rss-explorer`, `seekingalpha-explorer`, `forum-explorer`, `stackexchange-explorer`, `hackernews-explorer`, `tradingview-explorer` |
| Web | `web-searcher`, `google-searcher`, `web-reader`, `document-reader` |
| Research and code | `paper-code-explorer`, `research-explorer`, `annas-archive-explorer`, `sec-edgar-explorer`, `github-explorer` |
| Unreadable data | `reverse-anything` (REA: binaries, apps, databases, captures) |

Docs: [`docs/`](docs/) is the platform documentation, [`specs/`](specs/) the design. Platform skills share one contract (`search`, `profile`, `list`, `fetch`, `--ingest`); their code is in `finsocnet/adapters/`, the shared library in `finsocnet/core/`. Read the SKILL.md of a skill before using it.

## The workflows

```bash
S=uv run finsocnet kb
$S run start --skill market-idea-miner --goal "mine youtube:abc123def45" --harness claude-code --model <m>   # -> run id R

# 1. fetch content (any platform skill; --ingest stores it)
uv run .agents/skills/youtube-extractor/scripts/youtube.py fetch "<url>" --ingest --run R
# 2. mine it (skill: market-idea-miner)
$S content claim <content_id> --run R ; $S content chunks <content_id> ; $S content view <content_id> --from-seq A --to-seq B
$S card validate --file cards.json                     # fix every error; vocabulary: $S vocab lookup "<phrase>"
$S card candidates --file cards.json                   # you decide: same / refines / related / contradicts / new
$S card commit --file decisions.json --run R           # atomic per decision, idempotent
$S content done <content_id> --upto-seq B --cards N --run R
# 3. answer questions (skill: knowledge-search): Query Card -> $S card search --query-card q.json ; weak answer -> $S gap add
# 4. rulebooks (person-skill-synthesizer): $S person cards <id> ; $S skill upsert --file skill.json --run R ; $S skill get <id> --render markdown
$S run end --run R --outcome success --stats '{...}'
```

Exploration: `finsocnet explore add <url|@handle|person|query> [--person]` (`--person`: the URL is a person's profile → skill `person-explorer`) then the `source-explorer` skill (`kb queue next` → platform skill → miner). Improvement: `self-improver` (data fixes directly and reversibly; instruction changes only on a git branch with `finsocnet eval` results).

## How to work (read `docs/agent-guide.md`)

Evidence over claims. **Never** write a script that holds names, texts, quotes or URLs from memory; never write content text yourself (a citation to a content without `fetch_method` is refused); never report "complete" without `finsocnet kb audit` numbers. Use the platform skills to fetch, judge what you read, store with `kb … --run R`. Playbooks for lists of people, channels, books, papers, executives: `.agents/skills/source-explorer/references/playbooks.md`.

## Sessions and browsing

FinSocNet runs on a remote host; you never type passwords. The user logs in locally and ships the session: `finsocnet session export && finsocnet session push` (local machine) → `session_bridge.py import` (remote) → one agent Chrome (`agent_browser.py start`) that every browser-based skill attaches to. Exit code 3 (`LOGIN_REQUIRED` / `CHECKPOINT`) means: stop that platform and tell the user exactly which export to redo.

## Output contract and exit codes

Every script prints one JSON envelope `{"ok", "command", "data", "warnings", "meta"}` or `{"ok": false, "error": {"code", "message", "hint", "retry_after_sec"}}`. Exit 0 ok · 2 usage/`RUN_REQUIRED`/`UNSUPPORTED` · 3 login/checkpoint · 4 rate limit/budget · 5 not found · 6 validation (`error.details` lists every problem) · 7 browser unavailable · 8 conflict · 1 internal (log a `script_bug` lesson).

## Commands

| Command | Where |
|---|---|
| `finsocnet kb audit` | remote host: completeness and provenance report; the numbers to trust |
| `finsocnet kb …` (init, migrate, backup, doctor, stats, run, content, card, vocab, person, skill, queue, gap, seen, embed, translate, search, history, decision, lesson, feedback) | remote host |
| `finsocnet search "<english text>" [--types …] [--mode …] [filters]` (alias of `kb search`), **`--ui` on any command** for a terminal view instead of JSON | remote host |
| `finsocnet eval prepare\|score\|run` | remote host |
| `finsocnet explore add`, `finsocnet persons review`, `finsocnet feedback` | remote host |
| `finsocnet session init-local\|export\|push` | the user's own machine |
| `finsocnet install <claude\|omp\|pi\|hermes\|codex\|openclaw\|shared\|all> [--uninstall]` | where a harness runs |
| `finsocnet stats`, `skills`, `strategy <person>`, `tui` | remote host |

Slash commands (source in `commands/`): `/finsocnet`, `:search`, `:card`, `:person`, `:strategy`, `:compare`, `:explore`, `:explore-step`, `:explore-person`, `:mine`, `:gaps`, `:sessions`, `:improve`, `:feedback`, `:skills`, `:install-skill`.

## Development

`uv run pytest` runs the offline suite (live tests: `-m live`). Config is in `.env` (see `.env.example`; no credentials), `config/*.yaml`. Implementation status and open questions: [`specs/09-checklist.md`](specs/09-checklist.md).
