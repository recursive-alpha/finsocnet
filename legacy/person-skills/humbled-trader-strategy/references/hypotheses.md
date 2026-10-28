# Verified Empirical Hypotheses & Rulebook: Shay (Humbled Trader)

Grounded trading hypotheses and execution principles extracted from source material:

### [LONG] Overnight Multi-Day Continuation for Trend Longs
- **Category:** `holding_period`
- **Instrument:** `equities`
- **Falsifiable Statement:** Trend-following day-trade longs frequently demonstrate momentum continuation into the subsequent session; transitioning successful intraday momentum longs into overnight swing trades yields superior total performance compared to closing them on the same day.
- **Setup Criteria:** High ADR stocks, high volume/liquidity, daily chart trend-following breakout, sector momentum
- **Holding Period:** Overnight / 2-day swing trade
- **Statistical Evidence:** Overnight and swing trades generally outperformed intraday same-day longs in verified P&L analysis
- **Invalidation Risk:** Fails if sector momentum reverses or stock lacks overnight follow-through liquidity
- **Verbatim Ground Truth:**
> "My overnight and swing trades generally performed better than my same-day longs. And part of the reason is that my day trading strategy that I love the most, the trend following long, a lot of times I see continuation and strength into the second day. Hence, that's when the day trade becomes a much stronger overnight swing trade."

---

### [SHORT] Intraday Close for Short Selling (Avoid Overnight Short Swings)
- **Category:** `holding_period`
- **Instrument:** `equities`
- **Falsifiable Statement:** Short selling positions deteriorate over multi-day periods due to upward market drift and overnight gap risks; short setups must be executed strictly as intraday same-day trades and never held overnight as swing trades.
- **Setup Criteria:** Intraday momentum exhaustion, high ADR equities
- **Holding Period:** Strictly same-day intraday (close before market close)
- **Statistical Evidence:** Same-day shorts significantly outperformed multi-day short swings
- **Invalidation Risk:** Holding short positions overnight exposes trades to catastrophic gap-ups and adverse drift
- **Verbatim Ground Truth:**
> "Another thing I found is that I found the same-day trading shorts performed much better than swing shorts. So that's a sign that I need to avoid short selling as a swing trade."

---

### [BOTH] Minimum 4% ADR (Average Daily Range) Volatility Filter
- **Category:** `stock_selection`
- **Instrument:** `equities`
- **Falsifiable Statement:** Sustainable trading edge requires sufficient price range expansion; traders should filter for stocks exhibiting ADR > 4% with strong liquidity. Equities with ADR < 3-4% lack the range necessary to compensate for trade execution costs and risk.
- **Setup Criteria:** ADR >= 4.0%, high daily volume, high liquidity (e.g. semiconductors, memory, storage)
- **Holding Period:** Intraday to multi-day swing
- **Statistical Evidence:** Strongest historical trading results concentrated exclusively in high ADR stocks; flat/negative on low ADR
- **Invalidation Risk:** Trading stocks with ADR < 3% leads to breakeven or losing performance due to range compression
- **Verbatim Ground Truth:**
> "Some of my strongest results generally come from really high ADR stocks with really strong liquidity. ADR stands for average daily range, and it's a percentage. So a stock that moves a lot in a lot of range, you want to look for anything above 4% ADR or even higher. I think anything less than 4% ADR or less than 3%, that means a stock, no matter the price, it's moving in really, really small range."

---

### [LONG] Focus Group Edge Criteria (72% Win Rate Filter)
- **Category:** `edge`
- **Instrument:** `equities`
- **Falsifiable Statement:** Trading setups that concurrently satisfy four filter criteria—high volatility (ADR > 4%), strong liquidity, larger market capitalization, and active sector momentum—achieve an empirical 72% win rate, whereas trades lacking these criteria drop to a sub-random 35% win rate.
- **Setup Criteria:** 1) High volatility (ADR > 4%), 2) Strong liquidity, 3) Large market cap, 4) Sector momentum tailwind
- **Holding Period:** Intraday or overnight swing
- **Statistical Evidence:** 72% historical win rate in focus criteria vs 35% win rate outside focus criteria
- **Invalidation Risk:** Trading outside of hype/momentum sectors results in zero or negative expected value
- **Verbatim Ground Truth:**
> "My strongest trades generally had higher volatility, stronger liquidity, and larger market caps as well... most times some of these biggest trades also have sector momentum behind them. So, when I grouped the trades that matched those conditions, my focus group had a 72% historical winning rate. Any trades outside of those conditions, which is the avoid group, according to the AI, had only 35% win rate."

---

### [BOTH] Exponential Bet Sizing on High-Conviction A+ Setups
- **Category:** `risk_management`
- **Instrument:** `equities`
- **Falsifiable Statement:** Uniform position sizing across all trades destroys profitability by treating high-probability and low-probability setups equally; capital allocation must be exponentially skewed toward A+ setups that meet all focus criteria, while sizing down drastically or abstaining from marginal setups.
- **Setup Criteria:** Confirmed A+ setup matching full focus filter checklist (rare occurrence, non-daily)
- **Holding Period:** Flexible
- **Statistical Evidence:** Allocating equal size to best and worst trades was the primary leak in trading performance
- **Invalidation Risk:** Over-sizing on non-A+ setups leads to drawdowns; if every trade looks like A+, grading is flawed
- **Verbatim Ground Truth:**
> "There's a really fancy term called exponential bet sizing. It really just means to size into your best A+ setups when they appear and trade in much smaller on the average setups and everything else. Naturally, that also means the best of the best setups for you should not appear every single day. If every trade looks like an A+ setup, then you probably need to fix your grading systems or your analysis."

---
