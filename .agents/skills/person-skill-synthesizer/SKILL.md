---
name: person-skill-synthesizer
description: Build or rebuild a person's trading rulebook (overview, setup and screening, entry and execution, trade management, risk and sizing, psychology and review, checklists) from the Knowledge Cards cited to that person, and store it in the person_skills table — never as a skill folder on disk. Use after mining gave a person new cards, after merges touching their cards, or when the user asks to "build/update the strategy of <trader>", "write <trader>'s rulebook", or /finsocnet:strategy <person> --rebuild.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "2"
  spec: docs/spec/03-pipelines.md
---

# Person Skill Synthesizer

## Procedure

1. `kb run start --skill person-skill-synthesizer --goal "rulebook <person_id>" …` → `R`.
2. `uv run finsocnet kb person get <person_id>` (style, markets) and `kb person cards <person_id>` → active cards with this person's citations, grouped by category, with `stats` and contradiction links.
3. For each category that has cards, write one row (`skill_name` = `<person_id>-core` unless the person teaches clearly named methods, e.g. `example-vcp`):
   - `title`, `summary` (1–2 sentences).
   - `content_markdown`: numbered rules in the person's own order (screen → entry → manage → exit → risk → review). After each rule, list its card ids in parentheses: `(cards 41, 58)`.
   - `rules`: `[{"rule": "...", "card_ids": [41]}]` — one entry per numbered rule.
   - Mention explicitly when two of the person's own cards contradict each other, and when the person changed their view over time (use citation dates).
4. Write an `overview` row: style, markets, horizon, core edge in 5–10 lines, and what each category covers.
5. Write a `checklists` row derived only from the rules: pre-market, entry validation, in-trade, end-of-day review.
6. Save all rows to `data/work/R/skills_<person_id>.json` and run `kb skill upsert --file … --run R`. The validator rejects rows whose card ids are not active or do not cite this person, and any timestamp like `[12:40]`.
7. `kb run end --run R --outcome success --stats '{"categories": N, "rules": N}'`.

## Rules

1. No rule without a card behind it. If something is missing, it is a gap — `kb gap add` — not something to fill from general knowledge.
2. Use plain language for rules; keep the person's own numbers and terms (e.g. "ADR ≥ 4%").
3. No timestamps in rulebooks; the cards keep the citations and locators.
4. `private_source` persons get rulebooks too, but they are excluded from harness exports.

## Row example

```json
{"person_id": "example-swing-trader", "skill_name": "example-swing-trader-core", "category": "trade_management",
 "title": "Trade management: partials and moving-average trails",
 "summary": "Sells 1/4-1/3 into strength after 3-5 days and trails the rest with the 10-day (20-day for slower names).",
 "content_markdown": "## Rules\n1. After 3-5 days in a breakout position, sell 1/4-1/3. (cards 41)\n2. Exit the rest on the first daily close below the 10-day MA; use the 20-day on slower stocks. (cards 41, 58)\n",
 "rules": [{"rule": "After 3-5 days, sell 1/4-1/3 of a breakout position.", "card_ids": [41]},
           {"rule": "Exit the remainder on the first daily close below the 10-day MA (20-day for slower stocks).", "card_ids": [41, 58]}]}
```
