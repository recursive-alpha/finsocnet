# Claim grammar

Uppercase words are fixed keywords. `<…>` is free text that should use vocabulary keys for indicators and patterns (`ma_10`, `opening_range`) and plain English otherwise. The validator applies the regex in the right column.

| kind | Template | Regex |
|---|---|---|
| `rule`, `setup` | `IF <conditions> THEN <ACTION> <object> [AND\|THEN <ACTION> <object>]… [WITHIN\|UNTIL <horizon or exit>]` | `^IF .+? THEN (EXIT_PARTIAL\|LONG\|SHORT\|ADD\|EXIT\|AVOID\|HOLD\|SIZE)\b.+` |
| `observation` | `<subject> TENDS TO <outcome> WHEN <condition>` | `^.+ TENDS TO .+ WHEN .+` |
| `mechanism` | `<cause> CAUSES <effect> BECAUSE <reason>` | `^.+ CAUSES .+ BECAUSE .+` |
| `definition` | `<term_key> IS <definition>` | `^[a-z0-9_]+ IS .+` |
| `metric` | `<subject> HAS <metric_key> = <value> [ON <sample>]` | `^.+ HAS [a-z0-9_]+ = .+` |
| `practice` | `<practice> IMPROVES\|HURTS <outcome> [FOR <who>]` | `^.+ (IMPROVES\|HURTS) .+` |

## rule / setup

Good
- `IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position THEN EXIT remainder UNTIL first tf_daily close below ma_10`
- `IF stock gaps up > 10% on earnings AND premarket volume > 2x average THEN LONG on break of opening_range high WITHIN first 60 minutes`
- `IF 3 consecutive losing days THEN SIZE down to 50% of normal UNTIL 2 consecutive winning days`

Bad (and why)
- `Sell a third after a few days` — no IF/THEN, vague numbers ("a few" must stay as the speaker said it, but put it in the grammar).
- `IF breakout THEN he sells some` — person reference, no action keyword.
- `IF price > ema_10 THEN BUY` — `BUY` is not a keyword; use `LONG`.

## observation

Good
- `low-float small_caps that gap_up TENDS TO fade after 10:30 WHEN there is no news catalyst`
- `breakouts in a downtrend market_regime TENDS TO fail more often WHEN breadth is negative`
- `round_number levels TENDS TO act as resistance WHEN price approaches them for the first time`

Bad
- `Stocks go up` — no condition.
- `NVDA TENDS TO rally tomorrow WHEN earnings` — single-ticker prediction; not a card.
- `[12:40] gap ups fade` — timestamp, no grammar.

## mechanism

Good
- `rising real_yield CAUSES multiple_compression in long-duration growth_stocks BECAUSE distant cash flows are discounted the most`
- `forced selling by leveraged funds CAUSES gap_down follow-through BECAUSE margin calls force sales at any price`
- `low float_shares CAUSES larger intraday ranges BECAUSE small supply meets concentrated demand`

Bad
- `rates affect stocks` — no CAUSES/BECAUSE.
- `the Fed CAUSES crashes` — no reason given; if the source gave none, make it an `observation` instead.
- `real yields CAUSES de-rating BECAUSE the author says so` — the reason must be a mechanism.

## definition

Good
- `adr_pct IS the average daily high-low range over 20 days expressed as a percentage of price`
- `launch_pad IS a tight multi-day consolidation just above a rising ma_10 after a large move`
- `inflection_level IS a price where control between buyers and sellers changed before`

Bad
- `ADR% is…` — must start with the term key.
- `launch pad IS …` — key must be snake_case.
- `adr_pct IS important` — not a definition.

## metric

Good
- `episodic_pivot setup HAS win_rate = 25-30% ON the speaker's own trades 2014-2020`
- `the strategy HAS sharpe_ratio = 1.4 ON a 2005-2023 backtest of S&P 500 stocks`
- `small_caps gap_up > 50% HAS fade_rate = most ON the speaker's observations`

Bad
- `wins a lot` — no metric key or value.
- `HAS win rate = 30%` — key must be snake_case (`win_rate`) and there must be a subject.
- `win_rate = 30%` — missing subject and `HAS`.

## practice

Good
- `reviewing every trade on video weekly IMPROVES execution discipline FOR discretionary day traders`
- `trading after a daily_loss_limit is hit HURTS P&L`
- `writing a daily_plan before the open IMPROVES selectivity`

Bad
- `journal your trades` — no IMPROVES/HURTS.
- `I journal and it is good` — first person, vague outcome.
- `discipline IMPROVES` — no outcome.
