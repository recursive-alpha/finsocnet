# Query Card examples (kt-1.0)

Schema: `finsocnet/core/schemas/query_card.schema.json` (`specs/02-knowledge-cards.md` §7). Map concepts with `kb vocab lookup`; never add vocabulary for a query. Add filters only when the question clearly implies them.

## Q1 — general trade management
"should I hold overnight or close same day?"
```json
{"intent": "find_rules", "question": "should I hold overnight or close same day?",
 "subject": "holding positions overnight versus closing intraday",
 "claim_pattern": "IF <position condition> THEN HOLD overnight | EXIT same day",
 "terms": ["overnight_hold", "intraday_exit", "holding_period", "gap_risk"],
 "broader_terms": ["trade_management"],
 "aliases": ["hold overnight", "close same day", "carry the position", "swing vs day trade", "sleep with the position"],
 "filters": {"category": ["trade_management"]},
 "fts_queries": ["terms:(overnight_hold OR intraday_exit OR holding_period)", "\"hold overnight\" OR \"close same day\" OR \"carry the position\""]}
```

## Q2 — sizing after losses
"how do good traders size down after a losing streak?"
```json
{"intent": "find_rules", "question": "how do good traders size down after a losing streak?",
 "subject": "reducing position size after consecutive losses",
 "claim_pattern": "IF <losing streak> THEN SIZE down …",
 "terms": ["position_sizing", "losing_streak", "risk_per_trade", "max_drawdown"],
 "broader_terms": ["risk_management"],
 "aliases": ["size down", "cut size", "red days in a row", "drawdown", "smaller size after losses"],
 "filters": {"category": ["risk_and_sizing"]}}
```

## Q3 — concept explanation
"what is a VCP?"
```json
{"intent": "explain_concept", "question": "what is a VCP?",
 "subject": "volatility contraction pattern",
 "terms": ["vcp", "base", "volume_dry_up", "consolidation"],
 "aliases": ["VCP", "volatility contraction pattern", "contractions", "tightening"],
 "filters": {"kind": ["definition", "setup", "observation"]}}
```

## Q4 — one person's view
"what does Qullamaggie say about episodic pivots?"
```json
{"intent": "find_person_view", "question": "what does Qullamaggie say about episodic pivots?",
 "subject": "episodic pivot setup rules",
 "terms": ["episodic_pivot", "gap_up", "earnings", "opening_range"],
 "aliases": ["EP", "episodic pivot", "gap up on news"],
 "filters": {"person_id": ["kristjan-qullamaggie"]}}
```
Find the `person_id` with `kb person candidates --name "Qullamaggie"` first.

## Q5 — stop placement
"where should the stop go on a breakout?"
```json
{"intent": "find_rules", "question": "where should the stop go on a breakout?",
 "subject": "stop loss placement for breakout entries",
 "claim_pattern": "IF LONG breakout … THEN EXIT … below …",
 "terms": ["stop_loss", "breakout", "low_of_day", "failed_breakout"],
 "broader_terms": ["risk_management"],
 "aliases": ["stop under the low of day", "where to put the stop", "LOD stop", "breakout fails"],
 "filters": {"category": ["risk_and_sizing", "trade_management"]}}
```

## Q6 — research evidence
"does momentum work in crypto? any backtests?"
```json
{"intent": "find_evidence", "question": "does momentum work in crypto? any backtests?",
 "subject": "momentum strategies in cryptocurrencies",
 "terms": ["time_series_momentum", "cross_sectional_momentum", "backtest", "sharpe_ratio"],
 "aliases": ["momentum", "trend following", "crypto momentum"],
 "filters": {"instruments": ["crypto"], "evidence_level_min": "backtested"}}
```

## Q7 — contradictions
"do traders disagree about holding through earnings?"
```json
{"intent": "find_contradictions", "question": "do traders disagree about holding through earnings?",
 "subject": "holding positions through earnings reports",
 "terms": ["earnings", "overnight_hold", "gap_risk"],
 "aliases": ["hold through earnings", "flat before earnings", "earnings gap"]}
```
The search returns cards; read `card_stats.contradictions` and `kb card get <id> --links` to present both sides.

## Q8 — Vietnamese question
"Cách đặt cắt lỗ khi giao dịch cổ phiếu?" ("How to set a stop loss when trading stocks?")
```json
{"intent": "find_rules", "question": "Cách đặt cắt lỗ khi giao dịch cổ phiếu?",
 "subject": "stop loss placement for stock trades",
 "terms": ["stop_loss", "risk_per_trade"],
 "broader_terms": ["risk_management"],
 "aliases": ["cắt lỗ", "stop loss", "điểm cắt lỗ"],
 "filters": {"instruments": ["equities"]}}
```
Answer in the user's language; cards are English, quotes stay original.

## Q9 — SMC entry model
"how do SMC traders enter on a change of character?"
```json
{"intent": "find_setups", "question": "how do SMC traders enter on a change of character?",
 "subject": "change of character entry in smart money concepts",
 "terms": ["change_of_character", "break_of_structure", "order_block", "liquidity_sweep", "tf_1m", "tf_15m"],
 "aliases": ["CHoCH", "ChoCh", "BOS", "smart money concepts", "SMC"],
 "filters": {"kind": ["setup", "rule"]}}
```
