---
name: smb-capital-breakouts
description: Execute trading strategies based on SMB Capital's verified empirical methods (youtube). Includes ADR volatility filters, overnight long swing rules, intraday short closing, and exponential bet sizing.
license: MIT
metadata:
  author: "finsocnet-synthesizer"
  creator: "SMB Capital"
  platform: "youtube"
  user_id: "UCg3B_joekBGJ1s_4fRjsMKA"
  version: "1.0.0"
---

# SMB Capital Trading Strategy (YOUTUBE)

Tactical trading workflow synthesized from SMB Capital's verified empirical data, focus group criteria, and trade execution rules.

## Strategy Summary
- **Source Platform:** Youtube
- **Primary Market:** Equities with High Volatility and Strong Liquidity.
- **Asymmetric Holding Period:** Hold momentum breakout longs overnight; close short selling positions intraday (no overnight short hold).
- **Setup Win Rate:** 72% historical win rate when matching all focus criteria vs 35% outside.
- **Sizing Mechanism:** Exponential bet sizing (size into A+ setups, scale down or avoid marginal trades).

---

## 1. Selection Checklist (Focus Criteria)
Before initiating any position, the asset must meet all four filter conditions:
1. **High ADR (Average Daily Range):** Require **ADR >= 4.0%**. Stocks with ADR < 3% lack expansion potential and must be skipped.
2. **High Liquidity & Volume:** Strong institutional interest, tight spreads, large daily dollar volume.
3. **Larger Market Cap & Daily Chart Setup:** Multi-day breakout setup on the daily chart.
4. **Sector Momentum Tailwind:** Favor leading hype/momentum sectors (e.g. semiconductors, memory, storage) with sector-wide volume.

---

## 2. Long Trade Execution (Overnight Continuation)
- **Setup:** Trend-following breakout on daily chart meeting all 4 Focus Criteria.
- **Holding Period:** **Overnight / 2-Day Swing**.
- **Execution Rule:** If a day-trading long exhibits strong closing momentum, hold the position overnight to capture secondary-day continuation. Data demonstrates overnight longs substantially outperform same-day closing.
- **Reference Quote:**
  > *"My overnight and swing trades generally performed better than my same-day longs... a lot of times I see continuation and strength into the second day."*

---

## 3. Short Trade Execution (Intraday Close Only)
- **Setup:** Short-term momentum exhaustion or reversal in high ADR names.
- **Holding Period:** **Intraday ONLY (Same-Day Close)**.
- **Execution Rule:** Close all short positions prior to the market close. **NEVER swing short positions overnight.**
- **Risk Invalidation:** Overnight holding on shorts exposes positions to gap-up risk and long-term upward drift, turning positive expectancy into heavy losses.
- **Reference Quote:**
  > *"I found the same-day trading shorts performed much better than swing shorts. So that's a sign that I need to avoid short selling as a swing trade."*

---

## 4. Risk Management & Position Sizing
- **Exponential Bet Sizing:** Treat sizing as an exponential function of setup quality.
  - **A+ Setup (Matches all 4 focus criteria):** Maximum planned risk allocation.
  - **B/C Setups:** Minimize risk or pass completely.
  - **Outside Focus Criteria:** Do not trade (35% empirical win rate).
- **Selective Trading:** High-conviction setups do not occur daily. If every trade appears to be A+, reassess grading criteria.

---

## References
- [references/hypotheses.md](references/hypotheses.md): Detailed table of mined hypotheses with timestamps and quotes.
- [references/checklists.md](references/checklists.md): Pre-market screening checklist and execution sheet.
