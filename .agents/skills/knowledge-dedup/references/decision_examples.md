# Dedup decision examples

Cards are abbreviated to the fields that matter. Card ids are illustrative.

## D1 — Two people, same rule → `same`
New: `IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/3 ...` (person B, horizon swing_weeks)
Candidate 41: `IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position THEN EXIT remainder UNTIL first tf_daily close below ma_10` (person A)
```json
{"decision": "same", "target_card_id": 41, "candidate_ids": [41],
 "rationale": "Same trigger (3-5 days after breakout), same action (sell about a third), same horizon. Person B adds consensus."}
```

## D2 — Adds a variant → `refines`
New: same as 41 plus "use the 20 on slower names".
```json
{"decision": "refines", "target_card_id": 41, "candidate_ids": [41],
 "updates": {"conditions_add": ["slower stocks: trail with ma_20"], "terms_add": ["ma_20"], "aliases_add": ["the 20"], "notes_append": "Variant: ma_20 for slower stocks."},
 "rationale": "Same rule; new card adds the ma_20 variant."}
```

## D3 — Same setup, different part → `related`
New: `IF long entry on a pullback AND price trades below the pullback day low THEN EXIT full position (stop_loss)`
Candidate 90: `IF stock broke out AND first pullback reaches ema_21 THEN LONG on the pullback`
```json
{"decision": "related", "candidate_ids": [90], "links": [{"to_card": 90, "relation": "related", "rationale": "Stop rule for the setup in 90."}],
 "rationale": "Same setup family; this is the stop, 90 is the entry."}
```

## D4 — Opposite action, same conditions → `contradicts`
New: `IF position is a market_leader in a base AND earnings report before the next session THEN HOLD half position through the report`
Candidate 120: `IF open position AND earnings report before the next session THEN EXIT full position before the report`
```json
{"decision": "contradicts", "candidate_ids": [120], "links": [{"to_card": 120, "relation": "contradicts", "rationale": "HOLD through earnings vs EXIT before earnings under the same event."}],
 "rationale": "Same situation (earnings before next session), opposite action."}
```

## D5 — Special case of a general rule → `related` (example_of)
New: `IF small_caps gap_up > 50% AND no catalyst THEN SHORT after first_red_day`
Candidate 200: `parabolic small_caps TENDS TO fade WHEN volume_dry_up follows the first_red_day`
```json
{"decision": "related", "candidate_ids": [200], "links": [{"to_card": 200, "relation": "example_of", "rationale": "A concrete short setup exploiting the fade tendency in 200."}],
 "rationale": "Observation vs actionable setup; different kind and action."}
```

## D6 — Same subject, different timeframe → `related`
New: `IF tf_5m close above vwap after a gap_down THEN LONG ...` (intraday)
Candidate 310: `IF tf_daily close above ma_50 after a pullback THEN LONG ...` (swing_days)
```json
{"decision": "related", "candidate_ids": [310], "links": [{"to_card": 310, "relation": "related", "rationale": "Both are reclaim entries; different timeframe and level."}],
 "rationale": "Different horizon and level; not the same rule."}
```

## D7 — Same rule, different number → `refines` with a note
New: `IF position loss reaches 8% from entry THEN EXIT full position`
Candidate 15: `IF position loss reaches 7% from entry THEN EXIT full position` (numbers.stop_loss_pct = 7)
```json
{"decision": "refines", "target_card_id": 15, "candidate_ids": [15],
 "updates": {"notes_append": "Other sources use 8% instead of 7%."},
 "rationale": "Same fixed-percentage stop rule; the number differs, so it is noted, not overwritten."}
```

## D8 — No candidates → `new`
```json
{"decision": "new", "candidate_ids": [], "rationale": "no candidates"}
```

## D9 — Topic overlap only → `new`
New: `rising real_yield CAUSES multiple_compression in long-duration growth_stocks BECAUSE ...`
Candidates 400 (`FOMC day TENDS TO ... WHEN ...`), 401 (`IF cpi above estimate THEN AVOID new longs ...`)
```json
{"decision": "new", "candidate_ids": [400, 401], "rationale": "Candidates share macro terms but state different claims; not related enough to link."}
```

## D10 — Candidate merged meanwhile → CONFLICT handling
`kb card commit` returns `CONFLICT` for target 41 (now `merged_into` 58). Rerun `kb card candidates --file chunk.cards.json --index 3`, read card 58, decide again (usually `same` with target 58).

## D11 — Paraphrase with stronger evidence → `refines` (evidence upgrade)
New: same claim as 77, but quote cites a 10-year backtest with method.
```json
{"decision": "refines", "target_card_id": 77, "candidate_ids": [77],
 "updates": {"evidence_level_upgrade": "backtested", "notes_append": "Backtested 2010-2020 in a later source."},
 "rationale": "Same claim; new source adds backtest evidence."}
```

## D12 — Two candidates, one same and one contradicting → `same` + link
New: `IF 3 consecutive losing days THEN SIZE down to 50% ...`
Candidate 500 (same rule, other person), candidate 501 (`IF losing_streak THEN SIZE up to win it back` — opposite).
```json
{"decision": "same", "target_card_id": 500, "candidate_ids": [500, 501],
 "links": [{"to_card": 501, "relation": "contradicts", "rationale": "Sizing up after losses vs sizing down."}],
 "rationale": "Same as 500; 501 is the opposite approach and gets a contradicts link from 500."}
```
When the decision is `same`/`refines`, links are created from the target card.
