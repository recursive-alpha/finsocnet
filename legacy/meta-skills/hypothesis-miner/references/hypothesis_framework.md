# Trading Hypothesis Extraction Framework

## What is a "Trading Hypothesis"?
A Trading Hypothesis is an empirical, testable, or experience-backed claim made by a creator, trader, or author about market dynamics, trade selection, execution, or risk management.

## Schema & Standard Fields

| Field | Description | Example |
|---|---|---|
| `title` | Concise identifier | `Overnight Trend Long vs Same-Day Short` |
| `category` | Domain classification | `holding_period`, `stock_selection`, `execution`, `risk_management`, `edge` |
| `direction` | Market bias | `LONG`, `SHORT`, `BOTH`, `NEUTRAL` |
| `instrument` | Asset class | `equities`, `futures`, `options`, `crypto` |
| `hypothesis_statement` | Exact falsifiable proposition | *Holding day-trading trend longs overnight produces continuation, whereas short positions deteriorate when swung overnight and must close same-day.* |
| `setup_conditions` | Required filters/triggers | High ADR (>4%), strong liquidity, large cap, sector momentum |
| `holding_period` | Exact timeframe | Overnight/2-day swing (longs) vs Intraday close (shorts) |
| `statistical_claim` | Empirical numbers or win rate | 72% win rate on focus setups vs 35% on outside trades |
| `invalidation_risk` | Failure modes / risk warnings | Short swing decay; low ADR stocks lack range |
| `timestamp_start` / `timestamp_end` | Second-level timing | `168.8` to `196.0` |
| `timestamp_formatted` | Human readable time | `02:48 - 03:16` |
| `verbatim_quote` | Unedited transcript citation | Direct excerpt grounding the claim |

## Extraction Heuristics
When scanning content from video transcripts, audio transcriptions, or social posts:
1. **Contrasts & Asymmetries:** Long vs short holding times, high ADR vs low ADR.
2. **Numbers & Stats:** Win rates, risk-reward ratios, portfolio breakdowns.
3. **Sizing & Risk:** When to size up (exponential bet sizing) vs when to sit in cash.
4. **Negative Knowledge (What NOT to do):** "Stop doing X", "Avoid swing shorting", "I lose money on Y".
