# FinSocNet

**FinSocNet is an agent-operated knowledge network for finance and trading.** It finds the people who publish market knowledge (video, podcasts, social networks, chats, newsletters, forums, Q&A sites, code, papers, filings, books), stores everything they publish in one SQLite file, has your AI harness rewrite it into canonical **Knowledge Cards**, merges duplicates with the agent's judgment, and then answers questions with citations and hands out per-person rulebooks.

No vector database, no embeddings, no LLM calls from scripts: the harness agent (Claude Code, Codex, Hermes, Pi, OMP, OpenClaw) does all the reading and judging; scripts only fetch, store, validate, search and score. Skills follow the open [Agent Skills specification](https://agentskills.io). Design and decisions: [`SPEC.md`](SPEC.md), [`docs/spec/`](docs/spec/).

## How it works

```
platform skills ──fetch──► contents + segments ──► agent writes Knowledge Cards ──► validate ──► dedup (agent decides) ──► commit
 (youtube, x, reddit,       (data/knowledge.db,      (claim grammar, controlled       kb card      same / refines / related       atomic,
  substack, discord, …)      SQLite + FTS5)           vocabulary, exact quotes)        validate     / contradicts / new            logged
                                                                                                                                  │
 questions ──► Query Card ──► kb card search (BM25 over canonical form) ──► cited answer ──► weak? ──► gap ──► explore ──► more content
```

- **Knowledge Card:** one atomic statement (`rule`, `setup`, `observation`, `mechanism`, `definition`, `metric`, `practice`) with a fixed claim grammar such as `IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position`, vocabulary terms (`ema_10`, `episodic_pivot`), and citations that point at an exact segment and quote.
- **Person-centric:** knowledge belongs to people, not channels; every citation records who said it and in which role. Rulebooks live in the database (`finsocnet strategy <person>`), not in skill folders.
- **Remote-first sessions:** you log in on your own machine, `finsocnet session export` makes an encrypted bundle of your browser sessions, and the remote host imports it into its one agent Chrome. No passwords or cookies in `.env`.
- **Self-improving:** failed searches become gaps that drive exploration; lessons become reviewed changes on git branches with evaluation results.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/recursive-alpha/finsocnet/main/install.sh | bash        # remote host: CLI + harness registration
curl -fsSL https://raw.githubusercontent.com/recursive-alpha/finsocnet/main/install.sh | bash -s -- --local   # your own machine: session export only
```

or from a clone: `./install.sh`. Requires `uv`, Python ≥ 3.11 and SQLite ≥ 3.38.

## Quick start

```bash
finsocnet kb init                                    # database + vocabulary seed (344 terms)
finsocnet install all                                # slash commands and skill links for every harness found
uv run .agents/skills/session-bridge/scripts/session_bridge.py keygen        # remote: prints the age recipient
finsocnet session init-local --recipient age1… --remote me@host --remote-path /srv/finsocnet   # local
finsocnet session export && finsocnet session push   # local: log in in your browser first
uv run .agents/skills/agent-browser/scripts/agent_browser.py start           # remote
finsocnet explore add @qullamaggie                   # then, in your harness: /finsocnet:explore-step
```

In a harness: `/finsocnet:search should I hold overnight or close same day?` · `/finsocnet:strategy qullamaggie` · `/finsocnet:compare minervini,qullamaggie stops` · `/finsocnet:install-skill <link>`.

## Skills

About 45 skills in [`.agents/skills/`](.agents/skills/): the knowledge core (`knowledge-db`, `knowledge-transformer`, `knowledge-dedup`, `knowledge-search`, `market-idea-miner`), people (`person-matcher`, `person-skill-synthesizer`, `person-skills-explorer`), access (`session-bridge`, `agent-browser`), the improvement loop (`source-explorer`, `self-improver`, `skill-installer`) and one skill per platform family: YouTube, podcasts, X, Reddit, Bluesky, Threads, Instagram, Facebook, LinkedIn, StockTwits, Discord, Telegram, Medium, Substack, RSS, Seeking Alpha, forums, Stack Exchange, Hacker News, TradingView, web search and reading, documents, papers, SEC filings, GitHub, books. Third-party skills are installed only through `skill-installer` (quarantine, scan, review of every file, your confirmation, lock file).

## Status

Everything in the specification is implemented; what has been checked against real sites and what still waits for your accounts is listed in [`docs/spec/09-checklist.md`](docs/spec/09-checklist.md) and in each skill's `references/platform_notes.md`. Run the offline tests with `uv run pytest`.

## Responsible use

Reading Discord, Facebook, LinkedIn or Instagram by automating a user account can violate their terms and get the account banned; use a secondary account, keep the strict budgets, and read the notes in SPEC §9. Downloading copyrighted books may be illegal where you live. Nothing here is investment advice.
