---
name: finsocnet
description: Entry point to FinSocNet, the financial social intelligence system — database stats, cited answers from trading knowledge, trader rulebooks and comparisons, exploration of new creators and sources across YouTube, podcasts, X, Reddit, Discord, Telegram, Substack, Medium, forums, Stack Exchange, TradingView, Facebook, SEC filings, papers and books, session status, feedback, and self-improvement. Use for /finsocnet commands, when the user asks what FinSocNet knows about a trading topic or trader, or how to use the system; it routes to the specialised skills.
license: MIT
compatibility: Requires the FinSocNet repository (uv) on the host where the harness runs; local machines only need `finsocnet session` commands.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "8"
  spec: docs/spec/07-harness-integration.md
---

# FinSocNet

## Route the request

| User wants | Use |
|---|---|
| numbers: how much do we know | `/finsocnet` → `uv run finsocnet kb stats` |
| an answer about trading/finance | `knowledge-search` |
| a trader's strategy | `person-skills-explorer` (`uv run finsocnet strategy <name>`) |
| compare traders | `person-skills-explorer` compare procedure |
| a specific card | `uv run finsocnet kb card get <id> --citations --links` |
| who is this person | `person-matcher` |
| add / explore a creator, URL, book or topic | `finsocnet explore add <target>` then `source-explorer` |
| mine a stored item | `market-idea-miner` |
| login problems on a platform | `session-bridge` |
| browser problems | `agent-browser` |
| improve the system, clean duplicates | `self-improver` |
| install / update / remove a skill from a link | `skill-installer` |
| report a wrong answer/card | `uv run finsocnet feedback <type> <id> -1 "<comment>"` |

## Slash commands

| Command | Behaviour |
|---|---|
| `/finsocnet` | stats summary: persons, sources, contents by status, cards, citations, top consensus cards, open gaps, queue, session health |
| `/finsocnet:search <question>` | knowledge-search |
| `/finsocnet:card <id>` | card with citations (links with timestamps) and links |
| `/finsocnet:person <id or name>` | profile, aliases, appearances, stats |
| `/finsocnet:strategy <person> [category] [--rebuild]` | rulebook; `--rebuild` runs person-skill-synthesizer first |
| `/finsocnet:compare <a,b> <topic>` | side-by-side rules |
| `/finsocnet:explore <target>` | enqueue + one explore step for it |
| `/finsocnet:explore-step` | one source-explorer step (for loops/schedules) |
| `/finsocnet:mine <content_id>` | market-idea-miner |
| `/finsocnet:gaps` | open knowledge gaps |
| `/finsocnet:sessions` | session status per platform |
| `/finsocnet:improve` | one self-improver run |
| `/finsocnet:feedback <type> <id> <+1\|-1> [comment]` | record feedback |
| `/finsocnet:skills` | core vs installed skills, versions, outdated |
| `/finsocnet:install-skill <link>` | skill-installer: check, review, confirm, install |

## CLI

| Command | Where |
|---|---|
| `finsocnet kb …`, `finsocnet eval …` | remote host |
| `finsocnet explore add`, `finsocnet persons review`, `finsocnet feedback` | remote host |
| `finsocnet session init-local\|export\|push` | user's local machine |
| `finsocnet install <claude\|omp\|pi\|hermes\|codex\|openclaw\|all>` | where the harness runs |
| `finsocnet tui` | remote host |

## Principles to respect in every answer

- Every claim comes from a card with a citation; say when you add general knowledge.
- Show consensus (how many people) and contradictions, not only one view.
- Persons marked `private_source` (closed groups) are not exported to other harnesses.
