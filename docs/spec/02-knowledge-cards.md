# 02 — Knowledge Cards, Vocabulary and the Transformer

A Knowledge Card is the only form in which FinSocNet stores knowledge (ADR-003). The `knowledge-transformer` skill teaches the harness agent to write cards. Scripts only validate and store them.

---

## 1. What a Card Is

One card = **one atomic, reusable statement of financial knowledge**, rewritten into a fixed form with the same meaning as the source.

| `kind` | Use for | Example (meaning) |
|---|---|---|
| `rule` | what to do under conditions (entries, exits, stops, sizing) | sell a third after 3–5 days, trail the rest with the 10-day MA |
| `setup` | a complete pattern with trigger, used to find trades | episodic pivot: gap > 10% on earnings with volume, buy the opening range high |
| `observation` | how markets/instruments tend to behave | small caps that gap up on low float tend to fade after 10:30 |
| `mechanism` | cause → effect with a reason | rising real yields compress growth-stock multiples because distant cash flows are discounted most |
| `definition` | what a term means in this person's usage | "ADR%" = average daily range as % of price over 20 days |
| `metric` | a number about a strategy, market or person | the setup wins 25–30% with average winner 5–10R |
| `practice` | process, psychology, review habits and their effect | reviewing every trade on video weekly improves execution |

Not cards: greetings, sponsor reads, life stories without a lesson, pure predictions about one ticker on one day ("NVDA goes to 200 tomorrow"), jokes. The content is still stored; the chunk yields `[]`.

---

## 2. Card JSON (input to `kb card validate/commit`)

### 2.1 Schema (`finsocnet/core/schemas/card.schema.json`, normative)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "card.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["card_version", "kind", "domain", "category", "subject", "claim", "terms", "evidence_level", "citation"],
  "properties": {
    "card_version": {"const": 1},
    "kind": {"enum": ["rule","setup","observation","mechanism","definition","metric","practice"]},
    "domain": {"enum": ["trading_strategy","stock_market","market_microstructure","macro_economics","valuation",
                         "risk_management","psychology","quant_research","derivatives","crypto","forex",
                         "fixed_income","general_finance"]},
    "category": {"enum": ["setup_and_screening","entry_and_execution","trade_management","risk_and_sizing",
                           "psychology_and_review","market_dynamics","concept","research_method"]},
    "subject": {"type": "string", "minLength": 5, "maxLength": 120},
    "claim": {"type": "string", "minLength": 10, "maxLength": 600},
    "conditions": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 12},
    "action": {"enum": ["LONG","SHORT","ADD","EXIT","EXIT_PARTIAL","AVOID","HOLD","SIZE","NONE"]},
    "horizon": {"enum": ["intraday","overnight","swing_days","swing_weeks","position","n/a"]},
    "instruments": {"type": "array", "items": {"enum": ["equities","small_caps","etfs","indices","futures","options",
                    "forex","crypto","bonds","commodities","any"]}, "uniqueItems": true},
    "regime": {"type": "array", "items": {"type": "string", "pattern": "^[a-z0-9]+(_[a-z0-9]+)*$"}, "uniqueItems": true},
    "terms": {"type": "array", "minItems": 1, "maxItems": 15, "uniqueItems": true,
              "items": {"type": "string", "pattern": "^[a-z0-9]+(_[a-z0-9]+)*$"}},
    "aliases": {"type": "array", "items": {"type": "string", "maxLength": 80}, "maxItems": 20},
    "entities": {"type": "array", "items": {"type": "string", "maxLength": 40}, "maxItems": 20},
    "numbers": {"type": "object", "additionalProperties": {"type": ["number", "string"]},
                "propertyNames": {"pattern": "^[a-z0-9]+(_[a-z0-9]+)*$"}},
    "evidence_level": {"enum": ["anecdotal","claimed","backtested","audited"]},
    "invalidation": {"type": ["string", "null"], "maxLength": 300},
    "notes": {"type": ["string", "null"], "maxLength": 500},
    "citation": {
      "type": "object", "additionalProperties": false,
      "required": ["content_id", "segment_seq", "quote", "speaker"],
      "properties": {
        "content_id": {"type": "string"},
        "segment_seq": {"type": "integer", "minimum": 0},
        "quote": {"type": "string", "minLength": 8, "maxLength": 1200},
        "speaker": {
          "type": "object", "additionalProperties": false, "required": ["role", "confidence"],
          "properties": {
            "person_id": {"type": ["string", "null"]},
            "handle": {"type": ["string", "null"]},
            "role": {"enum": ["owner","guest","host","co_host","author","co_author","commenter","member","unknown"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      }
    }
  }
}
```

### 2.2 Validation beyond the schema (`validate_card`)

Every failure is reported with a JSON pointer and a suggestion. All checks run; errors are not short-circuited.

| Check | Error code | Rule |
|---|---|---|
| Claim grammar | `GRAMMAR_ERROR` | §3 regex for the card's `kind` must match |
| Action consistency | `GRAMMAR_ERROR` | for `rule`/`setup`: the first action keyword after `THEN` equals `action`; other kinds: `action` is `NONE` or absent |
| Vocabulary | `VOCAB_UNKNOWN` | every `terms[]` and `regime[]` value exists in `vocabulary` with `status='active'`; suggestion = best `kb vocab lookup` match or the `merged_into` term |
| Terms appear in claim or conditions | `VALIDATION_ERROR` | at least one term key, its label, or one of its aliases appears in `claim` or `conditions` (prevents tag stuffing) |
| Quote | `QUOTE_NOT_FOUND` | `quote_in(quote, text(seq) + text(seq+1) + text(seq+2))` |
| Segment exists | `VALIDATION_ERROR` | `(content_id, segment_seq)` exists |
| Speaker | `VALIDATION_ERROR` | `person_id` exists if given; if `role` is `commenter`/`member` and `person_id` is null, `handle` is required |
| Timestamps | `VALIDATION_ERROR` | `claim`, `subject`, `conditions` must not contain `\[?\d{1,2}:\d{2}(:\d{2})?\]?` |
| Numbers in claim | warning | numbers in `claim` should also be in `numbers` |
| Language | warning | `claim`/`subject`/`conditions` should be English (ASCII letter ratio > 0.8) |

---

## 3. Claim Grammar

Uppercase keywords are fixed tokens. `<…>` is free text using vocabulary labels or keys. Regexes are applied with `re.DOTALL`.

| kind | Template | Regex |
|---|---|---|
| `rule`, `setup` | `IF <conditions> THEN <ACTION> <object> [AND|THEN <ACTION> <object>]… [WITHIN|UNTIL <horizon or exit>]` | `^IF .+? THEN (EXIT_PARTIAL|LONG|SHORT|ADD|EXIT|AVOID|HOLD|SIZE)\b.+` |
| `observation` | `<subject> TENDS TO <outcome> WHEN <condition>` | `^.+ TENDS TO .+ WHEN .+` |
| `mechanism` | `<cause> CAUSES <effect> BECAUSE <reason>` | `^.+ CAUSES .+ BECAUSE .+` |
| `definition` | `<term> IS <definition>` | `^[a-z0-9_]+ IS .+` (term key first) |
| `metric` | `<subject> HAS <metric> = <value> [ON <sample>]` | `^.+ HAS [a-z0-9_]+ = .+` |
| `practice` | `<practice> IMPROVES|HURTS <outcome> [FOR <who>]` | `^.+ (IMPROVES|HURTS) .+` |

Writing rules:
- Use `AND` / `OR` in conditions; use vocabulary keys for indicators and patterns (`ma_10`, `ema_20`, `opening_range`), plain words elsewhere.
- Numbers keep the source's precision; ranges stay ranges (`3-5 days`, `1/4-1/3`).
- No person names, no "he says", no timestamps in `claim`.

---

## 4. Vocabulary

The vocabulary is what makes lexical search work without embeddings (ADR-001). Treat it as a product.

### 4.1 Term key rules

| Rule | Good | Bad |
|---|---|---|
| snake_case, lowercase ASCII, singular | `bull_flag` | `BullFlags`, `bull-flag` |
| indicator + period | `ema_10`, `sma_200`, `rsi_14`, `atr_14` | `10ema`, `ema10` |
| unspecified MA type | `ma_10` (broader of `ema_10`, `sma_10`) | guessing EMA |
| timeframes | `tf_1m`, `tf_5m`, `tf_15m`, `tf_1h`, `tf_daily`, `tf_weekly` | `5min` |
| metrics | `adr_pct`, `rvol`, `float_shares`, `short_interest`, `win_rate`, `r_multiple`, `expectancy`, `max_drawdown`, `sharpe_ratio` | `ADR%` |
| no tickers, no person names | (tickers go to `entities`) | `nvda_breakout`, `minervini_setup` |
| methodology names are allowed as `setup` facet when widely used | `vcp`, `episodic_pivot`, `smc_order_block` | |
| `broader` links every specific term to its family | `ema_10 → ema → moving_average` | |

### 4.2 Seed file

`.agents/skills/knowledge-transformer/references/vocabulary_seed.json` (array of `{term,label,facet,aliases,broader,definition}`), loaded by `kb vocab add` in Phase 1. Minimum content, written by the implementing agent:

- **≥ 250 terms** covering every facet in 01 §2.4.
- Must include at least: moving averages (`moving_average, ma_N, ema_N, sma_N` for N ∈ {8,9,10,20,21,50,100,150,200}), `vwap, anchored_vwap, rsi_14, macd, atr_14, adr_pct, rvol, volume_dry_up, relative_strength, rs_line`; patterns `breakout, breakdown, bull_flag, bear_flag, base, flat_base, cup_with_handle, vcp, double_bottom, head_and_shoulders, ascending_triangle, wedge, gap_up, gap_down, gap_fill, episodic_pivot, parabolic_short, opening_range, opening_range_breakout, first_red_day, failed_breakout, pullback, reclaim, inside_bar, higher_low`; SMC/ICT `liquidity_sweep, order_block, fair_value_gap, break_of_structure, change_of_character, premium_discount`; levels `support, resistance, inflection_level, prior_day_high, prior_day_low, premarket_high, round_number`; execution `market_order, limit_order, stop_order, stop_loss, trailing_stop, partial_profit, scaling_in, scaling_out, scratch_trade, tape_reading, level_2`; risk `position_sizing, risk_per_trade, r_multiple, max_drawdown, daily_loss_limit, account_risk, kelly_criterion`; timeframes; market/macro `market_regime, trend, uptrend, downtrend, range_bound, high_volatility, vix, breadth, sector_rotation, interest_rate, real_yield, yield_curve, inflation, earnings, guidance, catalyst, fomc, cpi`; instruments/markets `small_caps, large_caps, float_shares, short_interest, premarket, after_hours, market_open, market_close, overnight_hold, intraday_exit, holding_period`; psychology/process `overtrading, revenge_trading, fomo, discipline, trade_journal, trade_review, daily_plan, playbook, process_goal, tilt`; quant `backtest, walk_forward, overfitting, survivorship_bias, look_ahead_bias, transaction_costs, slippage, sharpe_ratio, sortino_ratio, expectancy, win_rate`; valuation `pe_ratio, ev_ebitda, discount_rate, duration, multiple_compression, free_cash_flow, growth_stocks, value_stocks`; styles and regimes `day_trading, swing_trading, position_trading, trade_management, losing_streak, gap_risk, rising_rates, falling_rates, risk_on, risk_off`.
- Every term used in the examples of §6 and §7 must exist in the seed, so the examples validate.
- Each term has 1–6 aliases in English (and Vietnamese aliases where common, e.g. `stop_loss` → "cắt lỗ").

### 4.3 Adding terms during transformation

1. For every concept in the text, run `kb vocab lookup "<surface phrase>"`.
2. `exact_term` / `exact_alias` / `label` match → use that term.
3. `fts` matches only → read them; use one if it means the same; otherwise go to 4.
4. Propose a new term in a `vocab_new.json` file (`facet`, `label`, `aliases`, `broader` required; `broader` must be an existing term unless the facet root is new) and run `kb vocab add --file vocab_new.json --run R` **before** validating the cards that use it.
5. Never create a term that differs from an existing one only by spelling, plural, or period formatting.

---

## 5. The `knowledge-transformer` Skill

### 5.1 Files

```
.agents/skills/knowledge-transformer/
  SKILL.md                       # procedure below + pointers
  references/
    card_format.md               # §2 and §3 in prose for the agent
    claim_grammar.md             # templates + 3 good / 3 bad claims per kind
    examples.md                  # ≥ 16 few-shot examples (§6), every kind, every platform family, ≥ 3 "no card" cases
    query_examples.md            # ≥ 8 Query Card examples (§7)
    vocabulary_seed.json         # §4.2
```

`metadata.version` in SKILL.md frontmatter is the transformer version (`kt-1.0`). Bump the minor version for few-shot or instruction changes, the major version for card schema changes. The version is written to `knowledge_cards.transformer_version` and `contents.processed_with`.

### 5.2 Procedure (agent)

Input: a chunk view from `kb content view <id> --from-seq A --to-seq B` (format in 03 §1.2).

1. Read the whole chunk once. Identify every statement that is reusable knowledge (§1).
2. Merge statements in this chunk that say the same thing (the speaker repeats themselves) into one card; cite the clearest occurrence.
3. Split compound statements into separate cards (one entry rule, one stop rule).
4. For each card: choose `kind`, write `subject`, write `claim` in grammar, fill `conditions`, `action`, `horizon`, `instruments`, `regime`.
5. Map concepts to vocabulary (§4.3). Put surface phrases from the text into `aliases` — this is what lets a user's own words find the card later.
6. Put explicit numbers in `numbers`. Do not compute or infer numbers.
7. Set `evidence_level` by the source's support (§8 rule 6).
8. Copy the quote **exactly** from the segment text (the validator ignores case/punctuation, not words). Prefer 1–3 sentences that contain the core claim. Set `segment_seq` to the segment where the quote starts.
9. Set `speaker`: for transcripts decide who is speaking (03 §6); for comments use the segment author.
10. Write the cards array to `data/work/<run_id>/<content-safe-id>/chunk_<NNN>.cards.json`; run `kb card validate`; fix every error; repeat until valid.
11. If the chunk has no knowledge, write `[]` and a `chunk_<NNN>.skip.json` with `{"skip_reason": "promotion|chit_chat|story_without_lesson|single_ticker_prediction|off_topic|unreadable"}`.

### 5.3 Quality rules

1. Same meaning, new form. Never add a condition, number or conclusion the source did not state. Never drop one it did state.
2. One idea per card.
3. If the source is ambiguous, say so in `notes` and use the broader term.
4. If the speaker contradicts themselves, make two cards; the dedup step will link them as `contradicts`.
5. A host's question is not knowledge. A guest's answer is.
6. Evidence level is about what the source offers: personal experience → `anecdotal`; stated as fact without data → `claimed`; cites a test/statistics with method → `backtested`; independently verified record → `audited`.
7. Cards are in English. Quotes stay in the original language.

---

## 6. Few-Shot Examples (minimum set for `references/examples.md`)

People below are fictional. Real examples in the file must also use fictional people or exact quotes from contents in the DB.

**E1 — YouTube transcript → `rule`**

Chunk view:
```
[#41 | 12:40-13:05 | speaker ?] so what I do is, once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe,
[#42 | 13:05-13:31 | speaker ?] and then the rest I just trail with the 10-day, and if it closes below the 10 I'm out. On slower names I use the 20.
```
Content: `youtube:abc123def45`, channel owner `example-swing-trader`, solo video.

```json
[{
  "card_version": 1, "kind": "rule", "domain": "trading_strategy", "category": "trade_management",
  "subject": "partial profit then moving-average trailing exit after breakout",
  "claim": "IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position THEN EXIT remainder UNTIL first tf_daily close below ma_10 (ma_20 for slower stocks)",
  "conditions": ["position entered on breakout", "3-5 trading days since entry"],
  "action": "EXIT_PARTIAL", "horizon": "swing_weeks", "instruments": ["equities"], "regime": [],
  "terms": ["breakout", "partial_profit", "trailing_stop", "ma_10", "ma_20", "tf_daily"],
  "aliases": ["10-day", "the 10", "the 20", "sell a third", "trail with the 10-day"],
  "entities": [],
  "numbers": {"partial_fraction": "1/4-1/3", "partial_after_days": "3-5", "trail_ma_fast": 10, "trail_ma_slow": 20},
  "evidence_level": "claimed", "invalidation": null,
  "notes": "Moving-average type (EMA/SMA) not stated.",
  "citation": {
    "content_id": "youtube:abc123def45", "segment_seq": 41,
    "quote": "once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe, and then the rest I just trail with the 10-day",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}
  }
}]
```

**E2 — Reddit comment → `practice` (anecdotal)**

```
[#7 | comment t1_k7 | u/example_dt] Honestly the thing that fixed my P&L was just not trading the first 15 minutes. I was giving back everything in the open chop. Went from red to green in 2 months.
```
```json
[{
  "card_version": 1, "kind": "practice", "domain": "trading_strategy", "category": "entry_and_execution",
  "subject": "avoid entries in the first 15 minutes after the open",
  "claim": "AVOIDING entries in the first 15 minutes after market_open IMPROVES day trading P&L FOR traders losing money in opening volatility",
  "conditions": ["intraday trading", "first 15 minutes of the regular session"],
  "action": "NONE", "horizon": "intraday", "instruments": ["equities"], "regime": [],
  "terms": ["market_open", "opening_range", "overtrading", "day_trading"],
  "aliases": ["first 15 minutes", "open chop"], "entities": [],
  "numbers": {"avoid_minutes_after_open": 15, "reported_turnaround_months": 2},
  "evidence_level": "anecdotal",
  "citation": {"content_id": "reddit:1abc234", "segment_seq": 7,
    "quote": "the thing that fixed my P&L was just not trading the first 15 minutes",
    "speaker": {"person_id": null, "handle": "u/example_dt", "role": "commenter", "confidence": 1.0}}
}]
```

**E3 — Book page → `mechanism`**

```
[#212 | page 212] When real yields rise, the present value of cash flows far in the future falls the most, which is why long-duration growth stocks de-rate first.
```
```json
[{
  "card_version": 1, "kind": "mechanism", "domain": "valuation", "category": "market_dynamics",
  "subject": "rising real yields and growth-stock valuation multiples",
  "claim": "rising real_yield CAUSES multiple_compression in long-duration growth_stocks BECAUSE distant cash flows are discounted the most",
  "conditions": ["real yields rising"], "action": "NONE", "horizon": "position",
  "instruments": ["equities"], "regime": ["rising_rates"],
  "terms": ["real_yield", "discount_rate", "duration", "growth_stocks", "multiple_compression"],
  "aliases": ["de-rate", "long-duration"], "entities": [], "numbers": {},
  "evidence_level": "claimed",
  "citation": {"content_id": "book:0123456789abcdef0123456789abcdef", "segment_seq": 212,
    "quote": "When real yields rise, the present value of cash flows far in the future falls the most",
    "speaker": {"person_id": "example-author", "handle": null, "role": "author", "confidence": 1.0}}
}]
```

**E4 — Podcast, host and guest → only the guest's statement is a card**

```
[#88 | 41:10-41:32 | speaker ?] So when you say you size down after losses, how much are we talking?
[#89 | 41:32-42:05 | speaker ?] After three red days in a row I cut size in half, and I only go back to full size after two green days. It stopped my drawdowns from snowballing.
```
Episode title: "Defense first — with Example Guest". Host: `example-host`.
```json
[{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "halve position size after a losing streak",
  "claim": "IF 3 consecutive losing days THEN SIZE down to 50% of normal UNTIL 2 consecutive winning days",
  "conditions": ["3 consecutive losing days"],
  "action": "SIZE", "horizon": "n/a", "instruments": ["any"], "regime": [],
  "terms": ["position_sizing", "losing_streak", "max_drawdown"],
  "aliases": ["three red days", "cut size in half", "full size"], "entities": [],
  "numbers": {"losing_days_trigger": 3, "size_fraction": 0.5, "winning_days_to_restore": 2},
  "evidence_level": "anecdotal",
  "citation": {"content_id": "podcast:9f8e7d6c5b4a:1a2b3c4d", "segment_seq": 89,
    "quote": "After three red days in a row I cut size in half, and I only go back to full size after two green days",
    "speaker": {"person_id": "example-guest", "handle": null, "role": "guest", "confidence": 0.9}}
}]
```
Segment #88 is the host's question → no card.

**E5 — Stack Exchange answer → `metric` (backtested)** — quote includes a sample and method; `evidence_level: "backtested"`; `numbers` holds `sharpe_ratio`, `sample_years`.

**E6 — Pine Script (TradingView) → `setup`** — segment kind `code`; the claim is written from the script's entry/exit logic; quote is the code line(s) containing the condition; `evidence_level: "claimed"`.

**E7 — Discord message thread → two cards, one contradicting the other** — two members disagree on holding through earnings; produce two cards; dedup will link `contradicts`.

**E8 — Vietnamese forum post (F319) → card in English, quote in Vietnamese**, `aliases` include the Vietnamese surface phrases ("cắt lỗ 7%").

**E9 — 13F filing note → `metric`** with `entities` = fund and ticker; `evidence_level: "audited"`.

**E10 — Compound sentence → split** into an entry `setup` card and a stop `rule` card.

**E11 — Ambiguous MA** → broader term + `notes` (already in E1; include a second variant with "the 21").

**E12 — Definition** → `definition` card for a person-specific term ("I call it a 'launch pad' when…").

**E13–E15 — No card:** sponsor read; "NVDA to 200 tomorrow" (single-ticker prediction); greeting and channel news.

**E16 — Already-quoted repetition:** the speaker says the same rule at #12 and #57 of the same chunk → one card citing #12.

The implementing agent writes E5–E16 in full in the same format as E1–E4.

---

## 7. Query Cards

### 7.1 Schema (`query_card.schema.json`)

```json
{
  "type": "object", "additionalProperties": false,
  "required": ["intent", "subject", "terms"],
  "properties": {
    "intent": {"enum": ["find_rules","find_setups","explain_concept","compare_people","find_evidence","find_contradictions","find_person_view"]},
    "question": {"type": "string"},
    "subject": {"type": "string"},
    "claim_pattern": {"type": "string"},
    "terms": {"type": "array", "items": {"type": "string", "pattern": "^[a-z0-9]+(_[a-z0-9]+)*$"}, "minItems": 1},
    "broader_terms": {"type": "array", "items": {"type": "string"}},
    "aliases": {"type": "array", "items": {"type": "string"}},
    "entities": {"type": "array", "items": {"type": "string"}},
    "filters": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "kind": {"type": "array"}, "domain": {"type": "array"}, "category": {"type": "array"},
        "horizon": {"type": "array"}, "instruments": {"type": "array"}, "person_id": {"type": "array"},
        "evidence_level_min": {"enum": ["anecdotal","claimed","backtested","audited"]},
        "min_persons": {"type": "integer"}
      }
    },
    "fts_queries": {"type": "array", "items": {"type": "string"}, "maxItems": 6}
  }
}
```

### 7.2 Procedure

1. Restate the question's subject in canonical words.
2. Map every concept to vocabulary terms with `kb vocab lookup` (same as §4.3, but never add terms for queries).
3. Add `broader_terms` (parents) when the question is general.
4. Add `aliases`: how traders would phrase it, including the user's own words.
5. Add filters only when the question clearly implies them (a person's name → `person_id`; "day trading" → `horizon: intraday`).
6. Optionally add up to 6 raw FTS5 queries (column filters allowed: `terms:`, `subject:`, `claim:`, `aliases:`, `quotes:`).

### 7.3 Example

Question: *"should I hold overnight or close same day?"*

```json
{
  "intent": "find_rules",
  "question": "should I hold overnight or close same day?",
  "subject": "holding positions overnight versus closing intraday",
  "claim_pattern": "IF <position condition> THEN HOLD overnight | EXIT same day",
  "terms": ["overnight_hold", "intraday_exit", "holding_period", "gap_risk"],
  "broader_terms": ["trade_management"],
  "aliases": ["hold overnight", "close same day", "carry the position", "swing vs day trade", "sleep with the position"],
  "filters": {"category": ["trade_management"]},
  "fts_queries": [
    "terms:(overnight_hold OR intraday_exit OR holding_period)",
    "\"hold overnight\" OR \"close same day\" OR \"carry the position\""
  ]
}
```
