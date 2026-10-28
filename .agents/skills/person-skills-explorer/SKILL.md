---
name: person-skills-explorer
description: Read, list and compare traders' rulebooks stored in the FinSocNet database — a person's full strategy, one category (setup, entry, trade management, risk, psychology, checklists), or a side-by-side comparison of several traders on a topic, each rule linked to its source cards. Use for "show me <trader>'s strategy", "how does <trader> manage trades", "compare <A> and <B> on stops", "which traders do we have", or /finsocnet:strategy and /finsocnet:compare.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "2"
  spec: specs/03-pipelines.md
---

# Person Skills Explorer

## Commands

| Need | Command |
|---|---|
| list persons with card counts | `uv run finsocnet kb person list` |
| find a person by name/handle | `uv run finsocnet kb person candidates --name "<name>"` |
| full rulebook | `uv run finsocnet kb skill get <person_id> --render markdown` |
| one category | `uv run finsocnet kb skill get <person_id> --category trade_management --render markdown` |
| the cards behind a rule | `uv run finsocnet kb card get <id> --citations` |

Categories: `overview`, `setup_and_screening`, `entry_and_execution`, `trade_management`, `risk_and_sizing`, `psychology_and_review`, `checklists`.

## Procedure: show a strategy

1. Resolve the person (`kb person candidates`). If several match, ask the user which one.
2. `kb skill get <id> --render markdown`. If it returns nothing but the person has cards, offer to run `person-skill-synthesizer`.
3. Show the overview first, then the requested categories. Keep card ids so the user can ask "why?" → `kb card get <id> --citations` and show quotes with links.

## Procedure: compare people on a topic

1. Resolve every person.
2. Pick the category for the topic (stops → `risk_and_sizing`, exits → `trade_management`, …) and `kb skill get` it for each person.
3. Also run `knowledge-search` with a Query Card filtered to those `person_id`s, to catch cards not yet in a rulebook.
4. Output a table: rows = aspects (trigger, stop placement, sizing, exit …), columns = persons, cells = the rule in a few words + card ids. Then 3–5 sentences on where they agree, where they differ, and contradictions.
