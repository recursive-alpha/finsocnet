# Knowledge Card format (card_version 1)

Normative schema: `finsocnet/core/schemas/card.schema.json` (`docs/spec/02-knowledge-cards.md` §2). This page explains each field for the agent.

| Field | Required | What to write | Example |
|---|---|---|---|
| `card_version` | yes | always `1` | `1` |
| `kind` | yes | `rule` (what to do), `setup` (complete pattern + trigger), `observation` (market tendency), `mechanism` (cause → effect), `definition`, `metric` (a number), `practice` (process/psychology) | `rule` |
| `domain` | yes | `trading_strategy`, `stock_market`, `market_microstructure`, `macro_economics`, `valuation`, `risk_management`, `psychology`, `quant_research`, `derivatives`, `crypto`, `forex`, `fixed_income`, `general_finance` | `trading_strategy` |
| `category` | yes | `setup_and_screening`, `entry_and_execution`, `trade_management`, `risk_and_sizing`, `psychology_and_review`, `market_dynamics`, `concept`, `research_method` | `trade_management` |
| `subject` | yes | 5–120 chars, canonical noun phrase, no names | `partial profit then moving-average trailing exit after breakout` |
| `claim` | yes | one sentence in the grammar for the kind (`claim_grammar.md`) | `IF … THEN EXIT_PARTIAL …` |
| `conditions` | no | atomic conditions, each a short phrase | `["entered on breakout", "3-5 trading days since entry"]` |
| `action` | rule/setup | first action after `THEN`: `LONG`, `SHORT`, `ADD`, `EXIT`, `EXIT_PARTIAL`, `AVOID`, `HOLD`, `SIZE`; other kinds `NONE` | `EXIT_PARTIAL` |
| `horizon` | no | `intraday`, `overnight`, `swing_days`, `swing_weeks`, `position`, `n/a` | `swing_weeks` |
| `instruments` | no | `equities`, `small_caps`, `etfs`, `indices`, `futures`, `options`, `forex`, `crypto`, `bonds`, `commodities`, `any` | `["equities"]` |
| `regime` | no | vocabulary terms for market conditions | `["rising_rates"]` |
| `terms` | yes | 1–15 vocabulary keys; at least one must appear (key, label or alias) in `claim` or `conditions` | `["breakout", "trailing_stop", "ma_10"]` |
| `aliases` | no | the source's own phrases | `["the 10", "sell a third"]` |
| `entities` | no | tickers, indices, funds, events | `["$NVDA", "FOMC"]` |
| `numbers` | no | explicit numbers only, snake_case keys | `{"partial_fraction": "1/4-1/3"}` |
| `evidence_level` | yes | `anecdotal`, `claimed`, `backtested`, `audited` | `claimed` |
| `invalidation` | no | when the idea stops working, if stated | `"fails if the stock closes below the breakout day low"` |
| `notes` | no | ambiguity, caveats, variants | `"MA type not stated."` |
| `citation` | yes | `content_id`, `segment_seq`, `quote` (verbatim), `speaker {person_id or handle, role, confidence}` | see examples |

Speaker roles: `owner`, `guest`, `host`, `co_host`, `author`, `co_author`, `commenter`, `member`, `unknown`.

Validator checks (fix them all before committing): schema, claim grammar per kind, action consistency, every term exists, terms appear in claim/conditions, quote found in the segment (and next two), segment exists, speaker valid, no timestamps in claim/subject/conditions.
