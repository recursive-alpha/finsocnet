# Few-shot examples (kt-1.0)

People, channels and content ids are fictional. Copy the style exactly: grammar keywords, vocabulary keys, verbatim quotes, speaker roles. Every term used here exists in `vocabulary_seed.json` except `launch_pad`, which E12 shows being added.

---

## E1 — YouTube transcript, solo video → `rule`

Chunk:
```
CONTENT youtube:abc123def45 | video | "Selling into strength — my exact rules"
PEOPLE  example-swing-trader (owner)
[#41 | 12:40-13:05 | speaker ?] so what I do is, once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe,
[#42 | 13:05-13:31 | speaker ?] and then the rest I just trail with the 10-day, and if it closes below the 10 I'm out. On slower names I use the 20.
```
Output:
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
Why: solo video → owner speaks, confidence 0.95. "10-day" without EMA/SMA → `ma_10` + note.

---

## E2 — Reddit comment → `practice` (anecdotal)

Chunk:
```
[#7 | comment t1_k7 | u/example_dt | score 87] Honestly the thing that fixed my P&L was just not trading the first 15 minutes. I was giving back everything in the open chop. Went from red to green in 2 months.
```
Output:
```json
[{
  "card_version": 1, "kind": "practice", "domain": "trading_strategy", "category": "entry_and_execution",
  "subject": "avoid entries in the first 15 minutes after the open",
  "claim": "AVOIDING entries in the first 15 minutes after market_open IMPROVES day_trading P&L FOR traders losing money in opening volatility",
  "conditions": ["intraday trading", "first 15 minutes of the regular session"],
  "action": "NONE", "horizon": "intraday", "instruments": ["equities"], "regime": [],
  "terms": ["market_open", "opening_range", "overtrading", "day_trading"],
  "aliases": ["first 15 minutes", "open chop"], "entities": [],
  "numbers": {"avoid_minutes_after_open": 15, "reported_turnaround_months": 2},
  "evidence_level": "anecdotal", "invalidation": null, "notes": null,
  "citation": {"content_id": "reddit:1abc234", "segment_seq": 7,
    "quote": "the thing that fixed my P&L was just not trading the first 15 minutes",
    "speaker": {"person_id": null, "handle": "u/example_dt", "role": "commenter", "confidence": 1.0}}
}]
```
Why: personal result, no data → `anecdotal`. Commenter without a person → `handle`.

---

## E3 — Book page → `mechanism`

Chunk:
```
[#212 | page 212] When real yields rise, the present value of cash flows far in the future falls the most, which is why long-duration growth stocks de-rate first.
```
Output:
```json
[{
  "card_version": 1, "kind": "mechanism", "domain": "valuation", "category": "market_dynamics",
  "subject": "rising real yields and growth-stock valuation multiples",
  "claim": "rising real_yield CAUSES multiple_compression in long-duration growth_stocks BECAUSE distant cash flows are discounted the most",
  "conditions": ["real yields rising"], "action": "NONE", "horizon": "position",
  "instruments": ["equities"], "regime": ["rising_rates"],
  "terms": ["real_yield", "discount_rate", "duration", "growth_stocks", "multiple_compression"],
  "aliases": ["de-rate", "long-duration"], "entities": [], "numbers": {},
  "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "book:0123456789abcdef0123456789abcdef", "segment_seq": 212,
    "quote": "When real yields rise, the present value of cash flows far in the future falls the most",
    "speaker": {"person_id": "example-author", "handle": null, "role": "author", "confidence": 1.0}}
}]
```

---

## E4 — Podcast interview → only the guest's answer is a card

Chunk:
```
CONTENT podcast:9f8e7d6c5b4a:1a2b3c4d5e6f | episode | "Defense first — with Example Guest"
PEOPLE  example-host (host), example-guest (guest)
[#88 | 41:10-41:32 | speaker ?] So when you say you size down after losses, how much are we talking?
[#89 | 41:32-42:05 | speaker ?] After three red days in a row I cut size in half, and I only go back to full size after two green days. It stopped my drawdowns from snowballing.
```
Output:
```json
[{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "halve position size after a losing streak",
  "claim": "IF 3 consecutive losing days THEN SIZE down to 50% of normal UNTIL 2 consecutive winning days",
  "conditions": ["3 consecutive losing days (losing_streak)"],
  "action": "SIZE", "horizon": "n/a", "instruments": ["any"], "regime": [],
  "terms": ["position_sizing", "losing_streak", "max_drawdown"],
  "aliases": ["three red days", "cut size in half", "full size", "size down"], "entities": [],
  "numbers": {"losing_days_trigger": 3, "size_fraction": 0.5, "winning_days_to_restore": 2},
  "evidence_level": "anecdotal", "invalidation": null, "notes": null,
  "citation": {"content_id": "podcast:9f8e7d6c5b4a:1a2b3c4d5e6f", "segment_seq": 89,
    "quote": "After three red days in a row I cut size in half, and I only go back to full size after two green days",
    "speaker": {"person_id": "example-guest", "handle": null, "role": "guest", "confidence": 0.9}}
}]
```
Why: #88 is the host's question → no card. #89 answers in first person about own trading → guest.

---

## E5 — Stack Exchange answer → `metric` (backtested)

Chunk:
```
CONTENT stackexchange:quant:71234 | question | "Does time-series momentum still work in futures?"
[#3 | answer 71240 | example_quant | score 54 | accepted] In our replication, a 12-month time-series momentum signal across 58 liquid futures, volatility-scaled to 10% per asset, had a Sharpe of about 0.9 from 1985 to 2015 before costs.
```
Output:
```json
[{
  "card_version": 1, "kind": "metric", "domain": "quant_research", "category": "research_method",
  "subject": "Sharpe ratio of volatility-scaled time-series momentum in futures",
  "claim": "time_series_momentum with 12-month lookback_period and volatility_targeting HAS sharpe_ratio = 0.9 ON 58 liquid futures 1985-2015 backtest before costs",
  "conditions": ["12-month lookback", "volatility scaled to 10% per asset", "before transaction costs"],
  "action": "NONE", "horizon": "position", "instruments": ["futures"], "regime": [],
  "terms": ["time_series_momentum", "lookback_period", "volatility_targeting", "sharpe_ratio", "backtest", "transaction_costs"],
  "aliases": ["12-month time-series momentum", "volatility-scaled"], "entities": [],
  "numbers": {"sharpe_ratio": 0.9, "lookback_months": 12, "universe_size": 58, "vol_target_pct": 10, "sample_start": 1985, "sample_end": 2015},
  "evidence_level": "backtested", "invalidation": null,
  "notes": "Before costs; replication by the answerer.",
  "citation": {"content_id": "stackexchange:quant:71234", "segment_seq": 3,
    "quote": "a 12-month time-series momentum signal across 58 liquid futures, volatility-scaled to 10% per asset, had a Sharpe of about 0.9 from 1985 to 2015 before costs",
    "speaker": {"person_id": null, "handle": "example_quant", "role": "commenter", "confidence": 1.0}}
}]
```
Why: method and sample stated → `backtested`.

---

## E6 — Pine Script (TradingView) → `setup`

Chunk:
```
CONTENT tradingview:script:xyz789 | script | "Volume Breakout Strategy"
[#2 | code strategy.pine:12-15 | example_pine_author] longCond = ta.crossover(close, ta.highest(high, 20)[1]) and volume > ta.sma(volume, 50) * 1.5
if longCond
    strategy.entry("L", strategy.long)
```
Output:
```json
[{
  "card_version": 1, "kind": "setup", "domain": "trading_strategy", "category": "entry_and_execution",
  "subject": "20-bar high breakout with volume surge",
  "claim": "IF close crosses above the prior 20-bar high AND volume > 1.5x the 50-bar average_volume THEN LONG at the signal bar close",
  "conditions": ["close crosses above highest high of the previous 20 bars", "volume above 1.5 times its 50-bar average"],
  "action": "LONG", "horizon": "n/a", "instruments": ["any"], "regime": [],
  "terms": ["breakout", "average_volume", "volume_surge"],
  "aliases": ["ta.highest(high, 20)", "volume > ta.sma(volume, 50) * 1.5"], "entities": [],
  "numbers": {"breakout_lookback_bars": 20, "volume_multiple": 1.5, "volume_average_bars": 50},
  "evidence_level": "claimed", "invalidation": null,
  "notes": "From script code; timeframe is whatever chart it runs on.",
  "citation": {"content_id": "tradingview:script:xyz789", "segment_seq": 2,
    "quote": "longCond = ta.crossover(close, ta.highest(high, 20)[1]) and volume > ta.sma(volume, 50) * 1.5",
    "speaker": {"person_id": null, "handle": "example_pine_author", "role": "author", "confidence": 1.0}}
}]
```

---

## E7 — Discord, two members disagree → two cards (dedup will link `contradicts`)

Chunk:
```
[#14 | message 1101 | trader_a] I never hold through earnings, the gap risk isn't worth it, I'm flat before the report.
[#15 | message 1102 | trader_b] Disagree, if it's a leader in a base I hold a half position through earnings, that's where the big gaps come from.
```
Output:
```json
[{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "trade_management",
  "subject": "exit before earnings reports",
  "claim": "IF open position AND earnings report before the next session THEN EXIT full position before the report",
  "conditions": ["holding a position", "earnings report scheduled before the next session"],
  "action": "EXIT", "horizon": "overnight", "instruments": ["equities"], "regime": [],
  "terms": ["earnings", "gap_risk", "overnight_hold"],
  "aliases": ["hold through earnings", "flat before the report"], "entities": [], "numbers": {},
  "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "discord:1100000000000000001:2026-10-20", "segment_seq": 14,
    "quote": "I never hold through earnings, the gap risk isn't worth it, I'm flat before the report",
    "speaker": {"person_id": null, "handle": "trader_a", "role": "member", "confidence": 1.0}}
},
{
  "card_version": 1, "kind": "rule", "domain": "trading_strategy", "category": "trade_management",
  "subject": "hold a half position in leaders through earnings",
  "claim": "IF position is a market_leader in a base AND earnings report before the next session THEN HOLD half position through the report",
  "conditions": ["stock is a market leader", "stock is in a base", "earnings report scheduled before the next session"],
  "action": "HOLD", "horizon": "overnight", "instruments": ["equities"], "regime": [],
  "terms": ["earnings", "market_leader", "base", "overnight_hold", "position_sizing"],
  "aliases": ["hold through earnings", "half position", "big gaps"], "entities": [],
  "numbers": {"position_fraction": 0.5}, "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "discord:1100000000000000001:2026-10-20", "segment_seq": 15,
    "quote": "if it's a leader in a base I hold a half position through earnings",
    "speaker": {"person_id": null, "handle": "trader_b", "role": "member", "confidence": 1.0}}
}]
```

---

## E8 — Vietnamese forum post (F319) → two cards in English, quotes in Vietnamese

Chunk:
```
[#5 | post 885512 | page 1 | nhadautu_vd] Nguyên tắc của mình: mua sai thì cắt lỗ 7% không bàn cãi, không bao giờ bình quân giá xuống.
```
Output:
```json
[{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "fixed 7 percent stop loss",
  "claim": "IF position loss reaches 7% from entry THEN EXIT full position",
  "conditions": ["unrealized loss of 7% from entry price"],
  "action": "EXIT", "horizon": "n/a", "instruments": ["equities"], "regime": [],
  "terms": ["stop_loss"],
  "aliases": ["cắt lỗ 7%", "mua sai thì cắt lỗ"], "entities": [],
  "numbers": {"stop_loss_pct": 7}, "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "forum:f319.com:885500", "segment_seq": 5,
    "quote": "mua sai thì cắt lỗ 7% không bàn cãi",
    "speaker": {"person_id": null, "handle": "nhadautu_vd", "role": "member", "confidence": 1.0}}
},
{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "never average down on a losing position",
  "claim": "IF position is losing THEN AVOID adding to the position (averaging_down)",
  "conditions": ["position below entry price"],
  "action": "AVOID", "horizon": "n/a", "instruments": ["equities"], "regime": [],
  "terms": ["averaging_down"],
  "aliases": ["bình quân giá xuống"], "entities": [],
  "numbers": {}, "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "forum:f319.com:885500", "segment_seq": 5,
    "quote": "không bao giờ bình quân giá xuống",
    "speaker": {"person_id": null, "handle": "nhadautu_vd", "role": "member", "confidence": 1.0}}
}]
```

---

## E9 — 13F filing → `metric` (audited)

Chunk:
```
CONTENT sec:0001234567-26-000123 | filing | "13F-HR Example Capital LP 2026-Q2"
PEOPLE  example-fund-manager (author)
[#4 | section holdings | para 4] As of 2026-06-30, Example Capital LP held 1,250,000 shares of NVDA valued at $212.5M, 8.4% of reported 13F assets.
```
Output:
```json
[{
  "card_version": 1, "kind": "metric", "domain": "stock_market", "category": "concept",
  "subject": "Example Capital NVDA position weight in 13F holdings",
  "claim": "Example Capital LP 13F portfolio HAS position_weight = 8.4% ON form_13f holdings of $NVDA as of 2026-06-30",
  "conditions": ["reported 13F long holdings only"],
  "action": "NONE", "horizon": "position", "instruments": ["equities"], "regime": [],
  "terms": ["position_weight", "form_13f"],
  "aliases": ["13F assets"], "entities": ["$NVDA", "Example Capital LP"],
  "numbers": {"position_weight_pct": 8.4, "shares": 1250000, "value_usd": 212500000},
  "evidence_level": "audited", "invalidation": null,
  "notes": "13F shows long US equity positions only; no shorts or options detail.",
  "citation": {"content_id": "sec:0001234567-26-000123", "segment_seq": 4,
    "quote": "Example Capital LP held 1,250,000 shares of NVDA valued at $212.5M, 8.4% of reported 13F assets",
    "speaker": {"person_id": "example-fund-manager", "handle": null, "role": "author", "confidence": 0.9}}
}]
```

---

## E10 — Compound sentence → split into setup + stop rule

Chunk:
```
[#30 | 22:10-22:40 | speaker ?] I buy the first pullback to the 21 EMA after a breakout, and my stop goes just under the low of the pullback day.
```
Output:
```json
[{
  "card_version": 1, "kind": "setup", "domain": "trading_strategy", "category": "entry_and_execution",
  "subject": "first pullback to the 21 EMA after a breakout",
  "claim": "IF stock broke out AND first pullback reaches ema_21 THEN LONG on the pullback",
  "conditions": ["prior breakout", "first pullback since the breakout", "price touches the 21-period EMA"],
  "action": "LONG", "horizon": "swing_days", "instruments": ["equities"], "regime": [],
  "terms": ["breakout", "pullback", "ema_21"],
  "aliases": ["first pullback", "the 21 EMA"], "entities": [], "numbers": {"ema_period": 21},
  "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "youtube:pull21exmpl", "segment_seq": 30,
    "quote": "I buy the first pullback to the 21 EMA after a breakout",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}}
},
{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "stop below the pullback day low",
  "claim": "IF long entry on a pullback AND price trades below the pullback day low THEN EXIT full position (stop_loss)",
  "conditions": ["long entry taken on a pullback", "price trades below the low of the pullback day"],
  "action": "EXIT", "horizon": "swing_days", "instruments": ["equities"], "regime": [],
  "terms": ["stop_loss", "pullback"],
  "aliases": ["just under the low of the pullback day"], "entities": [], "numbers": {},
  "evidence_level": "claimed", "invalidation": null, "notes": "Stop placement rule for the pullback setup.",
  "citation": {"content_id": "youtube:pull21exmpl", "segment_seq": 30,
    "quote": "my stop goes just under the low of the pullback day",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}}
}]
```

---

## E11 — Ambiguous moving average ("the 21")

Chunk:
```
[#55 | 31:02-31:20 | speaker ?] as long as it holds the 21 on the daily I just sit there, I don't touch it.
```
Output:
```json
[{
  "card_version": 1, "kind": "rule", "domain": "trading_strategy", "category": "trade_management",
  "subject": "hold while price stays above the 21-day moving average",
  "claim": "IF open position AND tf_daily close stays above ma_21 THEN HOLD position",
  "conditions": ["daily closes above the 21-period moving average"],
  "action": "HOLD", "horizon": "swing_weeks", "instruments": ["equities"], "regime": [],
  "terms": ["ma_21", "tf_daily", "trailing_stop"],
  "aliases": ["holds the 21", "the 21 on the daily"], "entities": [], "numbers": {"ma_period": 21},
  "evidence_level": "claimed", "invalidation": null,
  "notes": "MA type not stated (often EMA for 21, but not said here).",
  "citation": {"content_id": "youtube:abc123def45", "segment_seq": 55,
    "quote": "as long as it holds the 21 on the daily I just sit there",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}}
}]
```

---

## E12 — Person-specific term → add vocabulary, then `definition`

Chunk:
```
[#18 | 09:12-09:40 | speaker ?] I call it a launch pad when it goes sideways real tight for a few days right on top of the 10 after a big move.
```
1. `kb vocab lookup "launch pad"` → no exact/alias/label match; FTS returns `flat_base`, `consolidation` (not the same meaning).
2. `vocab_new.json`:
```json
[{"term": "launch_pad", "label": "launch pad", "facet": "pattern",
  "aliases": ["launch pad", "launchpad"], "broader": "consolidation",
  "definition": "Tight sideways consolidation of a few days on top of a rising 10-period moving average after a large move."}]
```
3. `kb vocab add --file vocab_new.json --run R`, then the card:
```json
[{
  "card_version": 1, "kind": "definition", "domain": "trading_strategy", "category": "concept",
  "subject": "launch pad consolidation",
  "claim": "launch_pad IS a tight sideways consolidation of a few days sitting on top of ma_10 after a large move",
  "conditions": ["prior large move", "tight sideways range for a few days", "price on top of the 10-period moving average"],
  "action": "NONE", "horizon": "n/a", "instruments": ["equities"], "regime": [],
  "terms": ["launch_pad", "consolidation", "ma_10"],
  "aliases": ["launch pad", "sideways real tight"], "entities": [], "numbers": {},
  "evidence_level": "claimed", "invalidation": null, "notes": "Speaker's own term.",
  "citation": {"content_id": "youtube:abc123def45", "segment_seq": 18,
    "quote": "I call it a launch pad when it goes sideways real tight for a few days right on top of the 10 after a big move",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}}
}]
```

---

## E13 — Sponsor read → no card

```
[#3 | 00:45-01:20 | speaker ?] This video is sponsored by ExampleBroker, open an account with my link and get two free stocks.
```
Output: `[]` and `chunk_000.skip.json`: `{"skip_reason": "promotion"}`.

## E14 — Single-ticker prediction → no card

```
[#61 | 44:10-44:20 | speaker ?] NVDA is going to 200 tomorrow, mark my words.
```
Output: `[]` and `{"skip_reason": "single_ticker_prediction"}`. (A reason or condition would make it an `observation`; this has none.)

## E15 — Greeting and channel news → no card

```
[#0 | 00:00-00:30 | speaker ?] Hey guys welcome back, quick update, the merch store is live and we hit 100k subs!
```
Output: `[]` and `{"skip_reason": "chit_chat"}`.

---

## E16 — The same rule said twice in one chunk → one card

```
[#12 | 05:10-05:40 | speaker ?] I risk a quarter percent of the account per trade, that's it.
...
[#57 | 38:00-38:20 | speaker ?] like I said, a quarter percent per trade, never more.
```
Output: one card citing `#12` (the clearer statement):
```json
[{
  "card_version": 1, "kind": "rule", "domain": "risk_management", "category": "risk_and_sizing",
  "subject": "risk a quarter percent of the account per trade",
  "claim": "IF taking any trade THEN SIZE position so risk_per_trade is 0.25% of account",
  "conditions": ["every trade"],
  "action": "SIZE", "horizon": "n/a", "instruments": ["any"], "regime": [],
  "terms": ["risk_per_trade", "position_sizing", "account_risk"],
  "aliases": ["a quarter percent", "quarter percent per trade"], "entities": [],
  "numbers": {"risk_per_trade_pct": 0.25}, "evidence_level": "claimed", "invalidation": null, "notes": null,
  "citation": {"content_id": "youtube:abc123def45", "segment_seq": 12,
    "quote": "I risk a quarter percent of the account per trade, that's it",
    "speaker": {"person_id": "example-swing-trader", "handle": null, "role": "owner", "confidence": 0.95}}
}]
```
