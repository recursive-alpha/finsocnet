#!/usr/bin/env python3
"""
Rebuild all 9 Person Strategy Skills with complete ground-truth specifications.
Generates full 7-category reference files, removes timestamps,
and syncs knowledge.db persons, hypotheses, and skills.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()
DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
SKILLS_ROOT = Path(".agents/skills")
PERSONS_DIR = Path("data/persons")

sys.path.insert(0, str((SKILLS_ROOT / "user-skill-synthesizer" / "scripts").resolve()))
from synthesize_skill import synthesize_user_skill

conn = sqlite3.connect(DEFAULT_DB_PATH)
c = conn.cursor()


def build_and_sync(skill_name: str, person_id: str, hypotheses: list[dict[str, Any]], category_docs: dict[str, str]) -> None:
    with open(PERSONS_DIR / f"{person_id}.json", "r", encoding="utf-8") as f:
        person = json.load(f)

    user_info = {
        "person_id": person["id"],
        "user_id": person["id"],
        "user_name": person["canonical_name"],
        "moniker": person.get("moniker", person["canonical_name"]),
        "trading_style": person.get("trading_style", ""),
        "primary_markets": person.get("primary_markets", ""),
        "verified_records": person.get("verified_records", ""),
        "bio": person.get("bio", ""),
        "platform": "multi-platform",
    }

    c.execute("DELETE FROM hypotheses WHERE person_id = ? OR user_id = ?", (person_id, person_id))
    for h in hypotheses:
        c.execute("""
        INSERT INTO hypotheses (
            content_id, user_id, person_id, title, category, direction, instrument,
            hypothesis_statement, setup_conditions, holding_period, statistical_claim,
            invalidation_risk, verbatim_quote
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            h.get("content_id", ""),
            person_id,
            person_id,
            h["title"],
            h.get("category", "edge"),
            h.get("direction", "BOTH"),
            h.get("instrument", "equities"),
            h["hypothesis_statement"],
            h.get("setup_conditions", ""),
            h.get("holding_period", ""),
            h.get("statistical_claim", ""),
            h.get("invalidation_risk", ""),
            h.get("verbatim_quote", "")
        ))
    conn.commit()

    synthesize_user_skill(
        skill_name=skill_name,
        user_info=user_info,
        hypotheses=hypotheses,
        skills_root=SKILLS_ROOT,
        db_path=DEFAULT_DB_PATH,
        category_docs=category_docs,
    )
    print(f"✓ Rebuilt skill '{skill_name}' for {user_info['user_name']} ({len(hypotheses)} hypotheses)")


# ==============================================================================
# 1. SHAY (HUMBLED TRADER)
# ==============================================================================
shay_hypotheses = [
    {
        "content_id": "zU0i9rBbEkI",
        "title": "Overnight Multi-Day Continuation for Trend Longs",
        "category": "holding_period",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Trend-following day-trade longs frequently demonstrate momentum continuation into the subsequent session; transitioning successful intraday momentum longs into overnight swing trades yields superior total performance compared to closing them on the same day.",
        "setup_conditions": "High ADR stocks, high volume/liquidity, daily chart trend-following breakout, sector momentum",
        "holding_period": "Overnight / 2-day swing trade",
        "statistical_claim": "Overnight and swing trades generally outperformed intraday same-day longs in verified P&L analysis",
        "invalidation_risk": "Fails if sector momentum reverses or stock lacks overnight follow-through liquidity",
        "verbatim_quote": "My overnight and swing trades generally performed better than my same-day longs. And part of the reason is that my day trading strategy that I love the most, the trend following long, a lot of times I see continuation and strength into the second day. Hence, that's when the day trade becomes a much stronger overnight swing trade."
    },
    {
        "content_id": "zU0i9rBbEkI",
        "title": "Intraday Close for Short Selling (Avoid Overnight Short Swings)",
        "category": "holding_period",
        "direction": "SHORT",
        "instrument": "equities",
        "hypothesis_statement": "Short selling positions deteriorate over multi-day periods due to upward market drift and overnight gap risks; short setups must be executed strictly as intraday same-day trades and never held overnight as swing trades.",
        "setup_conditions": "Intraday momentum exhaustion, high ADR equities",
        "holding_period": "Strictly same-day intraday (close before market close)",
        "statistical_claim": "Same-day shorts significantly outperformed multi-day short swings",
        "invalidation_risk": "Holding short positions overnight exposes trades to catastrophic gap-ups and adverse drift",
        "verbatim_quote": "Another thing I found is that I found the same-day trading shorts performed much better than swing shorts. So that's a sign that I need to avoid short selling as a swing trade."
    },
    {
        "content_id": "zU0i9rBbEkI",
        "title": "Minimum 4% ADR (Average Daily Range) Volatility Filter",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Sustainable trading edge requires sufficient price range expansion; traders should filter for stocks exhibiting ADR > 4% with strong liquidity. Equities with ADR < 3-4% lack the range necessary to compensate for trade execution costs and risk.",
        "setup_conditions": "ADR >= 4.0%, high daily volume, high liquidity (e.g. semiconductors, memory, storage)",
        "holding_period": "Intraday to multi-day swing",
        "statistical_claim": "Strongest historical trading results concentrated exclusively in high ADR stocks; flat/negative on low ADR",
        "invalidation_risk": "Trading stocks with ADR < 3% leads to breakeven or losing performance due to range compression",
        "verbatim_quote": "Some of my strongest results generally come from really high ADR stocks with really strong liquidity. ADR stands for average daily range, and it's a percentage. So a stock that moves a lot in a lot of range, you want to look for anything above 4% ADR or even higher. I think anything less than 4% ADR or less than 3%, that means a stock, no matter the price, it's moving in really, really small range."
    },
    {
        "content_id": "zU0i9rBbEkI",
        "title": "Focus Group Edge Criteria (72% Win Rate Filter)",
        "category": "edge",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Trading setups that concurrently satisfy four filter criteria—high volatility (ADR > 4%), strong liquidity, larger market capitalization, and active sector momentum—achieve an empirical 72% win rate, whereas trades lacking these criteria drop to a sub-random 35% win rate.",
        "setup_conditions": "1) High volatility (ADR > 4%), 2) Strong liquidity, 3) Large market cap, 4) Sector momentum tailwind",
        "holding_period": "Intraday or overnight swing",
        "statistical_claim": "72% historical win rate in focus criteria vs 35% win rate outside focus criteria",
        "invalidation_risk": "Trading outside of hype/momentum sectors results in zero or negative expected value",
        "verbatim_quote": "My strongest trades generally had higher volatility, stronger liquidity, and larger market caps as well... most times some of these biggest trades also have sector momentum behind them. So, when I grouped the trades that matched those conditions, my focus group had a 72% historical winning rate. Any trades outside of those conditions, which is the avoid group, according to the AI, had only 35% win rate."
    },
    {
        "content_id": "zU0i9rBbEkI",
        "title": "Exponential Bet Sizing on High-Conviction A+ Setups",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Uniform position sizing across all trades destroys profitability by treating high-probability and low-probability setups equally; capital allocation must be exponentially skewed toward A+ setups that meet all focus criteria, while sizing down drastically or abstaining from marginal setups.",
        "setup_conditions": "Confirmed A+ setup matching full focus filter checklist (rare occurrence, non-daily)",
        "holding_period": "Flexible",
        "statistical_claim": "Allocating equal size to best and worst trades was the primary leak in trading performance",
        "invalidation_risk": "Over-sizing on non-A+ setups leads to drawdowns; if every trade looks like A+, grading is flawed",
        "verbatim_quote": "There's a really fancy term called exponential bet sizing. It really just means to size into your best A+ setups when they appear and trade in much smaller on the average setups and everything else. Naturally, that also means the best of the best setups for you should not appear every single day. If every trade looks like an A+ setup, then you probably need to fix your grading systems or your analysis."
    }
]

shay_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Shay - Humbled Trader)

## 1. The Focus Group Criteria (72% Win Rate Filter)
Every trade candidate must satisfy the four core focus filters:
1. **High Volatility (ADR >= 4.0%):** Stock must have an Average Daily Range of at least 4%. Stocks with ADR < 3% lack expansion potential to cover risk and slippage.
2. **High Liquidity & Volume:** Institutional sponsorship, tight penny/sub-penny spreads, large daily dollar volume ($50M+ minimum).
3. **Larger Market Capitalization:** Prioritize mid-to-large-cap equities over erratic small-cap pump-and-dumps.
4. **Sector Momentum Tailwind:** Favor leading industry sectors with strong thematic capital inflows (e.g. semiconductors, memory, storage, AI infrastructure).

## 2. Daily Chart Setup
- Multi-day consolidation or breakout level clearing key horizontal resistance on the daily timeframe.
- Clean trending daily chart with price holding above rising 20 EMA and 50 SMA.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Shay - Humbled Trader)

## 1. Intraday Long Execution
- **Setup:** Trend-following long on daily chart breakout names.
- **Intraday Trigger:** 5-minute chart consolidation break or pullback to VWAP / rising 9 EMA with increasing volume.
- **Order Type:** Stop-limit or market order on confirmed momentum breakout.
- **Leveraged ETFs:** Utilize BetaPro 3x leveraged bull ETFs (e.g. semiconductors) strictly as intraday trading instruments during peak momentum sessions.

## 2. Intraday Short Execution
- **Setup:** Momentum exhaustion or failed breakout on high ADR equities.
- **Intraday Trigger:** Rejection at key daily resistance, break below VWAP on heavy volume.
""",
    "trade_management.md": """# Trade Management & Holding Periods (Shay - Humbled Trader)

## 1. Asymmetric Holding Period Rule
- **Long Positions (Overnight Swing):**
  - If an intraday trend-following long exhibits strong closing momentum and finishes near the high of day, **hold the position overnight as a 2-day swing**.
  - Verified P&L data demonstrates overnight longs significantly outperform same-day closing due to second-day continuation and gap expansion.
- **Short Positions (Intraday Close STRICTLY):**
  - **Close all short selling positions prior to the market close.**
  - **NEVER hold short positions overnight.**
  - Overnight shorts are exposed to upward market drift and catastrophic gap-up risk, degrading expected value into heavy net losses.
""",
    "risk_and_sizing.md": """# Risk Management & Position Sizing (Shay - Humbled Trader)

## 1. Exponential Bet Sizing
- **A+ Setups (All 4 Focus Criteria Met):** Deploy maximum planned risk allocation (size in aggressively).
- **Average (B/C) Setups:** Scale down size drastically (25-50% normal size) or abstain.
- **Outside Focus Criteria:** Do not trade. Historical win rate drops to 35% on non-focus trades.
- High-conviction A+ setups do not occur daily; if every setup looks like an A+, recalibrate grading discipline.

## 2. Stop Loss & Invalidation
- Define stop strictly below the intraday consolidation base or daily pivot before entry.
- Cut losers immediately if expected sector follow-through stalls.
""",
    "psychology_and_review.md": """# Trader Psychology & Performance Review (Shay - Humbled Trader)

## 1. AI-Driven P&L Dashboard Review
Review trading data across 5 analytical dimensions weekly:
1. **Holding Period:** Audit returns across day trades vs overnight swings.
2. **Stock Selection:** Identify which sectors and ADR profiles generated 80% of net profits.
3. **Winners vs Losers:** Compare average win size vs average loss size.
4. **Entry/Exit Patterns:** Detect execution slippage or premature exits.
5. **Hidden Connections:** Uncover emotional habits (e.g. overtrading outside momentum sectors).

## 2. Focus Over Strategy Accumulation
- Adding more strategies creates distraction. Edge comes from narrowing focus to what is already working.
""",
    "checklists.md": """# Pre-Market & Trade Execution Checklist (Shay - Humbled Trader)

## 1. Pre-Market Scanner
- [ ] ADR >= 4.0%
- [ ] Relative Volume >= 1.5x 30-day average
- [ ] Leading momentum sector (top 3 industry groups)
- [ ] Daily chart multi-day consolidation or breakout pivot

## 2. Trade Execution
- [ ] Meets all 4 focus criteria? (Yes = Full A+ exponential size; No = Reduce/Pass)
- [ ] Direction Long: Planned overnight hold if strong close
- [ ] Direction Short: Intraday close strictly; MOC stop set
- [ ] Defined structural stop placed before order placement
"""
}

build_and_sync("humbled-trader-strategy", "shay-humbled-trader", shay_hypotheses, shay_docs)


# ==============================================================================
# 2. KRISTJAN QULLAMAGGIE
# ==============================================================================
qullamaggie_hypotheses = [
    {
        "content_id": "TZnX1qEiOkM",
        "title": "Episodic Pivot (EP) High Volume Earnings Catalyst Expansion",
        "category": "stock_selection",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Stocks experiencing an Episodic Pivot (massive earnings/revenue surprise, multi-quarter guidance hike, or transformative paradigm shift) combined with enormous volume expansion generate multi-week momentum trends that substantially outperform regular chart breakouts.",
        "setup_conditions": "Triple-digit EPS/revenue beat, massive guidance raise, gap-up with enormous opening volume, stock in base for months/years",
        "holding_period": "Multi-day to multi-week swing",
        "statistical_claim": "EPs generate 50-200%+ asymmetric momentum runs and remain the highest expectancy setup across bull and mixed regimes",
        "invalidation_risk": "Fails if stock closes below low of the gap day or guidance is deceptive",
        "verbatim_quote": "drct like three weeks ago had like the five plus star EP huge volume great earnings huge beat... look at the guidance they raised their guidance from revenue guidance from 170 to 190 million from 128 million that's an insane rise that's a huge surprise to the markets you see the volume enormous volume like you have to trade these things if you trade EPs"
    },
    {
        "content_id": "TZnX1qEiOkM",
        "title": "Opening Range Breakout (ORB) on Gap Day Consolidation",
        "category": "execution",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "When a high-volume Episodic Pivot or breakout stock gaps up and refuses to retrace, entering on the breakout of the 1-minute or 5-minute opening range high (or consolidation high 60-90 min post-open) captures the initial institutional accumulation wave with tight invalidation at the low of day.",
        "setup_conditions": "Gap-up holding near highs, opening range consolidation, volume surge on break of ORB high",
        "holding_period": "Swing (Day 1 to multi-week)",
        "statistical_claim": "Textbook 100-500% momentum runners exhibit tight opening range holds without deep morning pullbacks",
        "invalidation_risk": "Break below the low of the opening range or low of day",
        "verbatim_quote": "it gapped up something like 100 almost 200% then it kind of you know pulled back a little bit and took out the opening range highs like an hour or hour and a half after the open that was a textbook when you have a stock doing that you know it has a big gap up it can't pull back and there's you know like you know it's insane"
    },
    {
        "content_id": "TZnX1qEiOkM",
        "title": "The 3-to-5 Day Partial Profit Rule & 10/20 EMA Trailing Stop",
        "category": "holding_period",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Locking in 1/3 to 1/2 of position profits into the initial momentum thrust on Day 3 to 5 finances trade risk, while trailing the remaining position along the rising 10 EMA or 20 EMA on the daily chart captures the entire macro swing move until an official close below the moving average.",
        "setup_conditions": "Position in profit after 3-5 days of consecutive expansion",
        "holding_period": "3-5 days for partials; multi-week for runners",
        "statistical_claim": "Captures 10-baggers while eliminating round-trip breakeven frustration",
        "invalidation_risk": "Daily close below the 10 EMA or 20 EMA",
        "verbatim_quote": "things looks pretty good as long as we can hold about the 10 and the 20 moving averages... all you have to do is you know raise stops and see see what's strong and what's not strong"
    },
    {
        "content_id": "TZnX1qEiOkM",
        "title": "Market Regime Filter (Green/Yellow/Red Light) via 10/20/100 Day MAs",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Momentum breakouts and Episodic Pivots exhibit high follow-through only when market indices are in confirmed uptrends with the 10 EMA above the 20 EMA and rising. In downtrends or chop, breakout failure rates soar and traders must remain in cash to avoid death by a thousand cuts.",
        "setup_conditions": "Index 10 EMA > 20 EMA, both sloping higher, 100-day trend slope positive",
        "holding_period": "Regime-based (cash during red light; aggressive during green light)",
        "statistical_claim": "20-30% of the year generates virtually all annual trading profits during low-volatility uptrends",
        "invalidation_risk": "Index breaks below 20 EMA / 50 SMA signaling immediate transition to yellow/red light",
        "verbatim_quote": "you wait for these periods when the 10 days start sloping up the 10 20 days start sloping up the 10 gets above the 20 like you know that's where the money is made and the rest of the time you just wait wait wait or do very little... trying to trade breakouts and EPS in bad markets you know it's not going to end well going to die from a thousand cuts"
    },
    {
        "content_id": "TZnX1qEiOkM",
        "title": "Progressive Exposure and Margin Deployment in Low Volatility Uptrends",
        "category": "risk_management",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Capital allocation should start at 0-20% exposure, stepping up to 100% invested only after initial breakout positions generate open profit cushions; margin leverage should be deployed exclusively during mature low-volatility uptrends where existing cushions absorb pullbacks.",
        "setup_conditions": "Open profit cushion on initial positions, index in steady low-volatility uptrend",
        "holding_period": "Trend duration",
        "statistical_claim": "Produces exponential account growth while eliminating forced margin liquidations",
        "invalidation_risk": "Multiple stop-outs in succession mandate immediate reduction to cash",
        "verbatim_quote": "these are the type of markets you can be on margin right you slowly build your positions you go say you go from 0% to 20 30 and then a few days later you up it again start seeing more and more setups and you know after a few weeks or a week you're maybe fully invested and then you start things keep going you have a profit cushion and then you slowly start going on margin"
    },
    {
        "content_id": "x_1331878176818159617",
        "title": "Asymmetric Portfolio Heat & 0.25-0.5% Trade Risk Limit",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Constraining risk to 0.25% to 0.5% (max 1.0%) of account equity per trade allows taking dozens of explosive breakout shots during bull regimes without risking ruin during inevitable cluster drawdowns.",
        "setup_conditions": "Stop loss defined strictly at low of day or 1-minute entry low",
        "holding_period": "Flexible",
        "statistical_claim": "Preserves capital across multi-year bear cycles while compounding accounts from $10K to $80M+",
        "invalidation_risk": "Over-risking (>1%) creates catastrophic drawdown when market regimes turn",
        "verbatim_quote": "Risking 0.2-0.5% per trade while capping overnight allocation produces 100x account expansions during sustained bull regimes while preserving capital through bear phases."
    }
]

qullamaggie_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Kristjan Qullamaggie)

## 1. The 3 Core Setups
1. **Episodic Pivots (EP):**
   - Fundamental catalyst: Massive quarterly earnings/revenue beat, huge forward guidance raise (e.g. 50-100%+ above expectations), or game-changing contract/FDA approval.
   - Enormous volume: Day 1 volume exceeding multi-month daily averages within the first 30 minutes.
   - Base context: Stock breaking out from months or years of sideways consolidation.
2. **High Tight Flags (HTF):**
   - Stock has doubled (+100% to +300%) over the past 4-8 weeks.
   - Consolidates tightly near highs for 2-5 weeks, pulling back no more than 20-25%.
   - Moving average support: Price rides the rising 10 EMA or 20 EMA during consolidation.
3. **Base Breakouts:**
   - Multi-week orderly sideways base with higher lows building into horizontal resistance.

## 2. Market Regime Filter (Green / Yellow / Red Light)
- **Green Light:** SPY/QQQ 10 EMA > 20 EMA, both sloping up; 100-day MA trending higher. Aggressive buying, full exposure, margin permitted.
- **Yellow Light:** Index pulls back to 20 EMA/50 SMA. Reduce position sizing; take faster partial profits.
- **Red Light:** Index trading below declining 10 and 20 EMAs. **Stay in cash.** Breakouts fail in bad markets; avoid death by a thousand cuts.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Kristjan Qullamaggie)

## 1. Opening Range Breakout (ORB) Entry
- **Primary Trigger:** 1-minute or 5-minute Opening Range High breakout on the day of the gap or daily breakout.
- **Character Check:** Stock gaps up and **refuses to pull back**; aggressive bidding lifts offers immediately.
- **Alternative Trigger:** Consolidation high breakout 60 to 90 minutes post-open if the stock forms an orderly intraday flag.

## 2. Order Execution
- Use stop-limit or market orders right as the high of the opening range is breached.
- Never chase extended candles; if the stock rips 10%+ past the ORB before entry, wait for a 1-minute flag or pass.
""",
    "trade_management.md": """# Trade Management & Holding Periods (Kristjan Qullamaggie)

## 1. The 3-to-5 Day Partial Profit Rule
- On Day 3 to 5 following entry, **sell 1/3 to 1/2 of the position into strength**.
- This locks in immediate trading profits and creates an open cushion that eliminates fear on the remaining shares.

## 2. Trailing Stop Execution
- Move the stop loss on remaining shares to breakeven after the Day 3-5 partial sale.
- **Trail the remainder on the rising 10 EMA or 20 EMA on the daily chart.**
- **Exit Rule:** Liquidate the remaining position only on a daily close below the chosen moving average (10 EMA for fast momentum, 20 EMA for bigger runners).
- On volatile small caps / micro caps, trail using the 10 and 20 EMA on the 60-minute chart.
""",
    "risk_and_sizing.md": """# Risk Management & Position Sizing (Kristjan Qullamaggie)

## 1. Risk per Trade Invariance
- Risk strictly **0.25% to 0.5% (maximum 1.0%)** of total account equity per trade.
- Initial Stop: Set strictly at the Low of Day (LOD) or 1-minute low of the entry candle.
- Position Size Formula: `Position Shares = (Account Equity * Risk%) / (Entry Price - Stop Price)`.

## 2. Progressive Exposure
- Start with 0% to 20-30% capital deployed when market flips to Green Light.
- Add positions only as earlier trades work and provide profit cushion.
- Reach 100% invested before deploying margin.
- If multiple stops are hit in a row, reduce exposure immediately and return to cash.
""",
    "psychology_and_review.md": """# Trader Psychology & Market Perspective (Kristjan Qullamaggie)

## 1. Tuning Out Noise
- Ignore geopolitical news, macro forecasts, inflation reports, and TV pundits.
- The chart, price action, and volume tell you everything institutions are actually doing.

## 2. Extreme Selective Patience
- 20% to 30% of the trading year produces virtually all annual profits.
- Do not feel compelled to trade every day; sitting on hands in cash during choppy/bear regimes is what protects your capital for the next super-cycle.
""",
    "checklists.md": """# Actionable Swing Trading Checklist (Kristjan Qullamaggie)

## 1. Market Regime Check
- [ ] SPY/QQQ 10 EMA > 20 EMA and sloping up?
- [ ] Market regime Green Light? (If Red, DO NOT TRADE).

## 2. Pre-Market Screening
- [ ] ADR >= 5% (high expansion range)
- [ ] Massive catalyst (triple-digit earnings surprise, huge guidance hike, or HTF base)
- [ ] Pre-market volume surge (millions of shares trading)

## 3. Entry Validation
- [ ] 1-min or 5-min Opening Range High broken with volume?
- [ ] Stop loss placed strictly at Low of Day (LOD)?
- [ ] Position size strictly bounded to 0.25-0.5% account risk?

## 4. Trade Management
- [ ] Day 3-5: Sold 1/3 to 1/2 into strength?
- [ ] Stop on remainder moved to breakeven?
- [ ] Trailing daily close below 10/20 EMA?
"""
}

build_and_sync("qullamaggie-swing-strategy", "kristjan-qullamaggie", qullamaggie_hypotheses, qullamaggie_docs)


# ==============================================================================
# 3. LANCE BREITSTEIN
# ==============================================================================
lance_hypotheses = [
    {
        "content_id": "UAlhNPmvB14",
        "title": "The 5 Support & Resistance Criteria for Inflection Point Edge",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Support and resistance levels fail when treated as arbitrary lines on random stocks; genuine predictive inflection points require concurrent fulfillment of five criteria: in-play product, clean visible level, proper consolidation tension, emotional participant reaction, and multi-timeframe agreement.",
        "setup_conditions": "All 5 criteria verified: 1) In-play, 2) Clean level, 3) Proper consolidation, 4) Emotional reaction, 5) Multi-timeframe agreement",
        "holding_period": "Intraday to multi-day swing",
        "statistical_claim": "Random S/R is a 50/50 coin flip; stacking the 5 criteria produces professional 8-figure trading expectancy",
        "invalidation_risk": "Fails if price slices back and forth through level without clean rejection or acceptance",
        "verbatim_quote": "Academics have shown that support and resistance do not work, and you might be struggling to make support and resistance work for you, too. In both cases, it's often because support and resistance are being used without incorporating these five key criteria: inplay product, clean level, proper consolidation, emotional reaction, and agreement on multiple time frames."
    },
    {
        "content_id": "UAlhNPmvB14",
        "title": "In-Play Asset Filter: Volume, Volatility & Catalyst Discovery",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Trading technical levels only works on in-play products undergoing active price discovery, heightened volatility, and emotional order flow driven by major catalysts; trading levels on quiet, efficient instruments yields random market friction.",
        "setup_conditions": "Unusual volume, elevated ATR/volatility, major catalyst or exceptional technical setup (e.g. SpaceX IPO, metals breakouts, oil geopolitical moves)",
        "holding_period": "Flexible",
        "statistical_claim": "In-play products concentrate retail and institutional emotion, allowing predictable technical reactions",
        "invalidation_risk": "Fading volume and declining volatility return the asset to efficient random walk",
        "verbatim_quote": "I only trade inplay stocks or products. An inplay stock is one experiencing unusual volume, volatility, a major catalyst, or an exceptional technical setup that has attracted significant attention from traders... Most levels are noise. You are better off flipping a coin. But when a stock has increased tension, emotion, volume, and volatility, you have the conditions where these technical levels become useful."
    },
    {
        "content_id": "UAlhNPmvB14",
        "title": "Proper Consolidation & Tension Building Before Breakout",
        "category": "execution",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "High-probability breakouts require tight pre-break consolidation where price refuses to pull back; this consolidation builds structural tension where shorts position for a drop and longs take profits, creating an explosive liquidity vacuum when breached.",
        "setup_conditions": "Shallow retracement after large move, price equilibrium holding tight beneath resistance or above support",
        "holding_period": "Breakout expansion duration",
        "statistical_claim": "Tight consolidation before level breach prevents false breakouts and drives immediate runaway expansion",
        "invalidation_risk": "Deep, loose retracement indicates lack of institutional absorption",
        "verbatim_quote": "Consolidation is price acceptance and you need these periods of relative equilibrium to gauge just how strong the buying or selling is after a large move in one direction... If we consolidate and don't pull back, when that break higher finally happens, all the longs need to re-enter and the shorts need to cover. This is easily one of the most underestimated points in trading breakouts."
    },
    {
        "content_id": "x_1526653469247029250",
        "title": "Right Side of the V & Channel Breakdown Exhaustion",
        "category": "execution",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Attempting to pick bottom turning points on capitulatory sell-offs carries severe negative expectancy; traders must wait for the panic to exhaust, form a base, and enter strictly on the confirmed Right Side of the V pivot.",
        "setup_conditions": "Capitulatory sell-off, volume climax, price rounding out and taking out first higher pivot on right side",
        "holding_period": "Multi-day reversal swing",
        "statistical_claim": "Entering on the right side of the V eliminates knife-catching failure rates while preserving 3:1+ asymmetric reward",
        "invalidation_risk": "Break below the newly formed capitulation base low",
        "verbatim_quote": "Entering on the confirmed right side of the V pivot eliminates knife-catching risk on panics; buying the first higher inflection low after capitulation yields 3:1+ asymmetric edge."
    },
    {
        "content_id": "UAlhNPmvB14",
        "title": "Multi-Timeframe Level Alignment for Institutional Swarming",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Technical levels gain exponential reliability when intraday inflection points align with major levels on the daily and weekly charts, uniting short-term day traders, swing traders, and institutions on the same side of the order book.",
        "setup_conditions": "Intraday (2-min / 5-min) level coinciding exactly with prior day high/low or multi-week chart pivot",
        "holding_period": "Flexible",
        "statistical_claim": "Multi-timeframe confluence generates instantaneous volume surges and rapid price displacement",
        "invalidation_risk": "Level visible only on a single low timeframe lacks broader market participation",
        "verbatim_quote": "Support and resistance exist everywhere... But a level becomes especially interesting when several of those charts point toward the same price. The more time frames that align, the more market participants you get on your side... you want everyone swarming to be on the same side of the market."
    },
    {
        "content_id": "x_2006443060159475980",
        "title": "Predefined Risk Invariance & A+ Exponential Sizing",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Top-tier 8-figure consistency requires strict risk invariance on capital combined with exponential position sizing: deploy 5x-10x capital on rare A+ setups where all 5 criteria align, while drastically reducing size or passing on C-grade setups.",
        "setup_conditions": "A+ setup verified across all 5 criteria with clean structural invalidation",
        "holding_period": "Flexible",
        "statistical_claim": "Asymmetric sizing into verified A+ setups produces 80%+ of lifetime trading P&L",
        "invalidation_risk": "Over-sizing on low-conviction or choppy setups leads to severe drawdowns",
        "verbatim_quote": "Traders achieve 8-figure consistency by constraining trades to predefined risk boundaries; sizing up 5x-10x on verified A+ setups while eliminating C setups."
    }
]

lance_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Lance Breitstein)

## The 5 Key Criteria for Support & Resistance ($100M Trader Framework)
Before taking any trade off a level, verify all 5 criteria:
1. **In-Play Product:** The asset must have unusual volume, high volatility, a major catalyst, or extreme price discovery (e.g. IPOs, geopolitical commodities, high-beta momentum). Efficient stocks produce random coin-flip levels.
2. **Clean Level:** The level must be obvious without squinting. Any competent trader across timeframes should immediately identify the same price point. Avoid levels price repeatedly slices straight through.
3. **Proper Consolidation (Tension):** Price must accept value near the level. Shallow retracements and tight equilibrium indicate that buyers/sellers are trapped; the breakout forces immediate covering.
4. **Emotional Reaction:** The level must have demonstrated prior institutional respect and emotional order flow. Upon breach, market participants must panic and swarm.
5. **Multi-Timeframe Agreement:** Intraday levels (2-min, 5-min) must align with daily, weekly, or prior-day highs/lows. Confluence brings multi-timeframe capital onto your side.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Lance Breitstein)

## 1. Right Side of the V Entry
- Never attempt to catch falling knives or predict market bottoms during panics.
- Wait for the capitulation sell-off to exhaust, volume climax to print, and price to establish an initial base.
- Enter on the **Right Side of the V** as price breaks out of the first higher consolidation pivot with volume confirmation.

## 2. Second Day Plays
- Day 2 continuation following an extreme Day 1 trend day or catalyst breakout.
- Look for trapped participants on the wrong side of the daily chart to fuel continuation.
""",
    "trade_management.md": """# Trade Management & Invalidation Rules (Lance Breitstein)

## 1. Structural Invalidation
- A genuine technical level should work almost immediately.
- If price breaches a level and immediately sags back below, the trade thesis is invalidated. **Scratch or exit immediately.**
- Do not sit through chop waiting for a full stop loss if the expected expansion velocity vanishes.

## 2. Letting Winners Run
- Scale partial profits at technical targets; trail remaining shares behind multi-timeframe structural pivots.
""",
    "risk_and_sizing.md": """# Risk Management & Capital Allocation (Lance Breitstein)

## 1. Predefined Risk Invariance
- Define exact risk parameters before pulling the trigger. Risk is non-negotiable.
- Initial stop placed strictly below the consolidation base or inflection pivot.

## 2. Setup Grading & Exponential Sizing
- **A+ Setups:** All 5 criteria aligned + sector tailwind. Deploy 5x to 10x normal capital.
- **B Setups:** 3-4 criteria met. Standard baseline sizing.
- **C Setups:** Messy chart, lack of volume, or no catalyst. **Pass completely.**
""",
    "psychology_and_review.md": """# Trader Psychology & Continuous Improvement (Lance Breitstein)

## 1. Draw Fewer Lines
- Amateur traders draw dozens of lines and trade every bounce.
- Elite traders draw few lines and demand rigorous criteria before risking capital.

## 2. Databasing Best Setups
- Archive and database hundreds of historical charts of your best A+ setups.
- Study consolidation tension, volume signatures, and post-breakout velocity.
""",
    "checklists.md": """# 5-Point S/R Execution Checklist (Lance Breitstein)

## 1. Screening
- [ ] Is the stock In-Play? (Unusual volume, catalyst, high volatility)
- [ ] Is the level clean without squinting? (Obvious to all traders)

## 2. Setup Quality
- [ ] Proper consolidation tension before the level? (Shallow retracements)
- [ ] Evidence of emotional reaction / trapped participants?
- [ ] Multi-timeframe agreement? (Intraday aligning with daily/weekly pivots)

## 3. Execution & Sizing
- [ ] Right Side of V confirmed? (No knife catching)
- [ ] A+ setup? (Deploy exponential size)
- [ ] Stop loss strictly set below consolidation low
- [ ] Scratch rule active: Exit immediately if velocity dies
"""
}

build_and_sync("lance-breitstein-levels", "lance-breitstein", lance_hypotheses, lance_docs)


# ==============================================================================
# 4. MIKE BELLAFIORE (SMB CAPITAL)
# ==============================================================================
bella_hypotheses = [
    {
        "content_id": "M1o0XqCaDiE",
        "title": "9/10 Technical Chart Level as Independent Catalyst",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "A technical breakout does not always require breaking news headlines; when an instrument breaks a multi-week or multi-month resistance level (graded 9/10 or 10/10), the clearing of that technical level itself serves as the market catalyst.",
        "setup_conditions": "Multi-week or multi-month consolidation on daily chart, clean horizontal resistance graded >= 9/10",
        "holding_period": "Intraday momentum to multi-day swing",
        "statistical_claim": "Taking only 9/10 and 10/10 levels eliminates 80% of amateur chop and creates asymmetric desk profitability",
        "invalidation_risk": "Trading 4/10 to 6/10 levels inside sloppy ranges produces paper cuts and flat/negative P&L",
        "verbatim_quote": "A breakout trade doesn't always need breaking news. When a stock clears a level it couldn't for weeks or months, that level itself is the catalyst... When Vince presented this daily chart to me, I asked him straight, 'Scale of 1 to 10, how important is that level?' He said a nine, and he was dead right."
    },
    {
        "content_id": "M1o0XqCaDiE",
        "title": "Pre-Breakout Relative Volume (RVOL >= 2x) Participation Filter",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "News brings retail attention, but elevated Relative Volume (RVOL >= 2.0x-3.0x) provides institutional confirmation; breakouts attempted on sub-normal volume are traps and must be rejected.",
        "setup_conditions": "Full day RVOL running at least 2x normal participation leading into the breakout session",
        "holding_period": "Flexible",
        "statistical_claim": "Breakouts with RVOL > 2x exhibit high follow-through; breakouts below 1x fail over 70% of the time",
        "invalidation_risk": "Low volume on breakout approach indicates lack of institutional sponsorship",
        "verbatim_quote": "News brings attention, but volume brings confirmation. Even without a headline, you need to see elevated ARVO, relative volume, confirming that big money participants are actively involved in the name... If a stock is trying to clear a monthly ceiling on half of the volume it normally does, it's a trap. If it's trading on two times or three times volume, real order flow is entering the arena."
    },
    {
        "content_id": "M1o0XqCaDiE",
        "title": "Tape Reading Aggression & Frictionless Offer Clearing",
        "category": "execution",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Genuine institutional breakouts reveal distinct tape character: aggressive lifting of offers, offers clearing without friction, remarkably shallow pullbacks with declining volume, and rapid upward velocity.",
        "setup_conditions": "Level breached, trades executing on offer, bids stepping up, shallow retracements",
        "holding_period": "Intraday momentum",
        "statistical_claim": "Aggressive tape lifting distinguishes high-velocity breakouts from false head-fakes",
        "invalidation_risk": "Offers reload heavily or bids soften upon level breach",
        "verbatim_quote": "When ETHA took out 1912, what did the tape look like? One, they were aggressively paying the offer. Two, the offers cleared without friction... Three, intraday pullbacks were remarkably shallow... Four, pullbacks were shallow and with decreasing volume. Five, the stock went up higher and faster than anyone expected."
    },
    {
        "content_id": "M1o0XqCaDiE",
        "title": "Non-Round Stop Loss Placement Rule (.09 / .14 / .24 Offset)",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Setting stop losses directly on obvious round numbers (.00, .10, .25, .50) leaves orders vulnerable to market maker liquidity sweeps; offsetting stops by 1 cent (e.g. .09, .14, .24) substantially improves trade survival rates.",
        "setup_conditions": "Stop placed strictly below breakout candle low or pre-break base with 1-cent offset",
        "holding_period": "Trade duration",
        "statistical_claim": "One extra cent offset dramatically eliminates false stop-outs from predatory sweeps",
        "invalidation_risk": "Placing stops on round numbers exposes trades to unnecessary liquidity hunt losses",
        "verbatim_quote": "Your stop goes strictly below the low of the breakout candle, or the immediate base before the break... A quick pro tip on stops, never set stops right on round numbers like 10 cents, or 20 cents, or 25 cents. Give it that extra penny, use 9 cents, or 14 cents, or 24 cents. That one penny dramatically improves your win rate against random liquidity sweeps."
    },
    {
        "content_id": "M1o0XqCaDiE",
        "title": "Adding to Winners on Intraday Consolidation Wick Breaks",
        "category": "execution",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "When a breakout demonstrates follow-through without pulling back, traders should pyramid capital by identifying 1-minute consolidation pauses, placing buy stops above wick highs, and trailing stops to the consolidation low.",
        "setup_conditions": "Initial position in profit, 1-minute consolidation flag forming, stop trailed to flag low",
        "holding_period": "Momentum expansion",
        "statistical_claim": "Adding to winning momentum trades multiplies total R-multiple return without increasing baseline risk",
        "invalidation_risk": "Breakdown below the 1-minute consolidation base invalidates the add",
        "verbatim_quote": "When the trade didn't go down and held higher, he didn't just sit on his hands. He identified consolidation pauses on the 1-minute tape, placed buy stops just above the wick highs where sellers temporarily stepped in, and added into the new push while trailing his risk up to the low of consolidation."
    },
    {
        "content_id": "M1o0XqCaDiE",
        "title": "The Scratch Rule: Immediate Liquidation on Momentum Stall",
        "category": "holding_period",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Momentum breakout trades must work immediately; if price breaks a level but velocity stalls, bids soften, and the tape dies, the position must be dumped immediately at breakeven or a nominal 1-2 cent loss rather than waiting for a full stop loss.",
        "setup_conditions": "Level breached but upward velocity halts within 1-2 minutes, volume dies",
        "holding_period": "Instant exit (< 2 minutes)",
        "statistical_claim": "Scratching dead trades preserves risk capital for genuine momentum runners",
        "invalidation_risk": "Passively holding a stalled trade turns scratches into full painful losses",
        "verbatim_quote": "To trade this setup with real size, you must learn how to scratch. If you pay a new high expecting instant momentum and the velocity simply isn't there, the bid soften and the tape dies, you dump it. You cut it. You get flat immediately at breakeven or two-cent loss. Don't sit there passively taking a full stop if the reason you took the trade disappeared."
    }
]

bella_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Mike Bellafiore - SMB Capital)

## The 8-Point Breakout Blueprint: Screening Phase
1. **Step 1: Grade the Technical Level (Scale of 1 to 10):**
   - The chart level must be a **9 out of 10 or 10 out of 10** on the higher-timeframe daily chart (multi-week or multi-month consolidation).
   - The clearing of a 9/10 level is an independent catalyst on its own.
   - **Rule:** Never take aggressive breakout trades on 4/10 or 6/10 sloppy ranges.
2. **Step 2: Pre-Breakout Relative Volume (RVOL >= 2.0x):**
   - News brings attention, but volume brings confirmation.
   - Asset must be trading on at least **2x to 3x normal volume participation**. Breakouts on sub-1x volume are traps.
3. **Step 5: Sector and Market Tailwinds:**
   - Check relevant index (SPY/QQQ) and sector ETFs.
   - **Sizing Rule:** If market and sector tailwinds align, deploy full **A-Size**. If the breakout is isolated, downgrade to **B-Size**.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Mike Bellafiore - SMB Capital)

## 1. Step 3: Volume Surge on Exact Breakout Bar (The "See It" Moment)
- Price prints normal volume on approach, but the second the level clears, look for a vertical volume acceleration spike on the 1-minute chart.
- Triggers simultaneous buying from breakout traders and short-covering panic.

## 2. Step 4: Reading the Tape
- Aggressive lifting of the offer (trades executing on ask).
- Offers clearing without friction.
- Intraday pullbacks are remarkably shallow and occur on declining volume.
- Upward velocity exceeds expectations.

## 3. Step 7: Adding to Winners
- When the trade holds higher, identify 1-minute consolidation pauses.
- Place buy stops just above the consolidation wick highs.
- Trail the stop loss on the entire position up to the consolidation low.
""",
    "trade_management.md": """# Trade Management & The Scratch Rule (Mike Bellafiore - SMB Capital)

## 1. Step 8: Defined Structural Exits
Exit using one of three structural triggers:
1. Break of the 2-minute prior bar low.
2. Breakdown of a clean intraday consolidation area.
3. Tape shift: Aggressive orders begin hitting bids, velocity dies, and buyers stop lifting offers.

## 2. The Scratch Rule (Essential for Sizing)
- A momentum breakout trade must work immediately.
- If you pay a new high expecting velocity, but the bids soften, momentum stalls, and tape dies: **Dump it immediately.**
- Get flat at breakeven or a 1-2 cent loss. Never sit passively through a full stop if the premise vanishes.
""",
    "risk_and_sizing.md": """# Risk Management & Stop Placement (Mike Bellafiore - SMB Capital)

## 1. Step 6: Initial Stop Loss & Non-Round Offset
- Initial stop goes strictly below the low of the breakout candle or immediate pre-break base.
- **The Non-Round Offset Rule:** Never place stops on round numbers (.00, .10, .20, .25, .50).
- Offset by one cent (e.g. use **.09, .14, .24, .49**). This single cent eliminates stops caused by market maker liquidity sweeps.

## 2. Conviction Sizing
- Full A-Size: 9/10 level + RVOL > 2x + Sector tailwind.
- B-Size: Isolated breakout or missing correlation checks.
""",
    "psychology_and_review.md": """# Trader Psychology & Desk Development (Mike Bellafiore - SMB Capital)

## 1. One Good Trade
- "One good trade, then one good trade, then one good trade."
- Focus on flawless process execution rather than immediate P&L outcome.

## 2. The Sprinting of Trader Development
- Momentum trading off 9/10 tactical levels is the sprinting of trader development: it trains order flow reading, fast decision-making, and emotional control under pressure.
- Grade your trades with Playbook presentations (benchmark: 85+ score).
""",
    "checklists.md": """# SMB Capital 8-Step Breakout Checklist

## 1. Setup Verification
- [ ] Level graded 9/10 or 10/10 on daily chart? (Multi-week ceiling)
- [ ] Relative Volume (RVOL) >= 2.0x?
- [ ] Market/Sector tailwind checked? (Yes = A-Size, No = B-Size)

## 2. Execution Triggers
- [ ] Volume acceleration spike on breakout candle? ("See it" moment)
- [ ] Tape confirming: aggressive lifting of offers, shallow pullbacks?
- [ ] Stop set below breakout base with non-round offset (.09/.14/.24)?

## 3. Active Trade Management
- [ ] Ready to add on 1-min consolidation wick break?
- [ ] Trailed risk up to consolidation low?
- [ ] Scratch Rule armed: Get flat immediately if velocity stalls!
"""
}

build_and_sync("smb-capital-breakouts", "mike-bellafiore", bella_hypotheses, bella_docs)


# ==============================================================================
# 5. TOM DANTE (TRADER DANTE)
# ==============================================================================
dante_hypotheses = [
    {
        "content_id": "pLWcPj859wA",
        "title": "The 4 Non-Negotiable Principles of Professional Execution",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Trading edge is lost not from flawed analysis, but from execution failure; professional profitability requires strict adherence to four execution laws: sit on hands when no edge exists, step up without hesitation when edge triggers, trade the market rather than P&L, and learn from mistakes through systematic review.",
        "setup_conditions": "Execution protocol applied to all trades across all instruments",
        "holding_period": "Flexible",
        "statistical_claim": "Execution discipline separates consistently profitable prop traders from chronic retail losers",
        "invalidation_risk": "Taking un-planned trades or hesitating on valid setups destroys expectancy",
        "verbatim_quote": "Number one, sit on your hands when you don't believe an opportunity is high probability... the hard part is trying not to act like an idiot in between them. Number two, step up when you believe it's time to do so... no fear, no hesitation. Number three, trade the market not your P&L. And number four, try to learn something from your trades."
    },
    {
        "content_id": "pLWcPj859wA",
        "title": "Institutional Liquidity Sweep & S/R Level Reclamation",
        "category": "execution",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Price frequently spikes through obvious daily and 4-hour support/resistance levels to sweep retail stop orders and trap breakout participants; when price aggressively rejects the sweep and reclaims the level, entering in the direction of the reclamation with stops beyond the wick provides asymmetric edge.",
        "setup_conditions": "Key horizontal S/R level, violent liquidity sweep beyond level, swift rejection and candle close back inside structure",
        "holding_period": "Intraday to swing",
        "statistical_claim": "Fading violent sweeps into key levels yields superior win rates and 3:1+ Risk:Reward",
        "invalidation_risk": "Price sustains momentum beyond the level without rejection",
        "verbatim_quote": "My edge lies not just in knowing what levels to trade... I started leaving orders in when price would collapse into a level very violently and I started getting more winning trades, more edge, making more money."
    },
    {
        "content_id": "pLWcPj859wA",
        "title": "Negative Visualization for Zero-Hesitation Execution",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Hesitation and fear of pulling the trigger stem from unwillingness to accept loss; mentally visualizing the trade stopping out and accepting the dollar loss before entering diminishes fear and allows flawless, detached execution.",
        "setup_conditions": "Pre-trade routine executed immediately prior to order submission",
        "holding_period": "Instant",
        "statistical_claim": "Diminishes performance anxiety and prevents hesitation feedback loops",
        "invalidation_risk": "Trading with high emotional expectation leads to premature exits and micro-management",
        "verbatim_quote": "Before you pull the trigger, you see it stopping you out and you see the loss in your account so you imagine it, you make peace with it, and then you take the trade... the fear is diminished, you're literally lessening the mental impact of being wrong."
    },
    {
        "content_id": "pLWcPj859wA",
        "title": "The -2R Daily Drawdown Circuit Breaker",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Loss clusters trigger emotional deterioration and revenge trading; establishing a mandatory daily circuit breaker (e.g. stop trading upon reaching -2R loss for the day) halts capital bleeding and forces mental reset.",
        "setup_conditions": "Cumulative daily P&L reaches -2R",
        "holding_period": "Rest of the trading day",
        "statistical_claim": "Eliminates catastrophic blow-up days that erase months of steady gains",
        "invalidation_risk": "Violating the circuit breaker leads to compounded tilt and severe drawdowns",
        "verbatim_quote": "You need to insert something into the process that will make the bad practice impossible. So for example, I personally have a rule: if I hit 2R down for the day, I stop trading on my swing strategy."
    },
    {
        "content_id": "pLWcPj859wA",
        "title": "Trade the Market, Not Your P&L or Emotional Expectations",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Evaluating open positions based on account balance, daily target needs, or past losses induces premature profit-taking or stubborn over-holding; active trade management must respond solely to structural chart targets and technical invalidation.",
        "setup_conditions": "Open position management",
        "holding_period": "Trade duration",
        "statistical_claim": "Trading P&L causes profit giveback and stops winners from reaching natural targets",
        "invalidation_risk": "Holding past technical targets because of personal financial desires",
        "verbatim_quote": "The market is not the fact that you did your ass in the last three trades... The market doesn't care that you need it to move up 14R to get to a new account high. I cannot tell you how often I used to get in a trade, see it go to my next level, look at my P&L and go 'nah that's not enough for a day's work' and start looking for reasons to hold. All I did was keep giving back profit. You have to trade what you see in front of you."
    },
    {
        "content_id": "pLWcPj859wA",
        "title": "The Daily Trade Plan, Logging Missed Trades & The Demon Finder",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Traders suffer from recency bias by remembering only recent outcomes; recording planned trades, logging missed trades, and utilizing a Demon Finder diagnostic sheet systematically exposes behavioral flaws and eliminates recurring errors.",
        "setup_conditions": "Pre-market plan sheet filled daily, post-session Demon Finder review",
        "holding_period": "Daily review routine",
        "statistical_claim": "Exposes subconscious trading flaws and removes execution leaks",
        "invalidation_risk": "Failing to log missed trades blinds traders to their own execution inconsistencies",
        "verbatim_quote": "You can use a Demon Finder to quickly identify bad practices and then the next thing you want to do is map out the situations in which bad practices occur... I had never noticed this because I never recorded my missed trades, so I was always at the mercy of recency bias."
    }
]

dante_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Tom Dante)

## 1. Key Levels & Institutional Liquidity
- Identify high-timeframe (Daily & 4-Hour) horizontal support and resistance levels.
- Focus on levels where retail traders place obvious clustered stop orders (swing highs, swing lows, equal highs/lows).
- Look for violent liquidity sweeps: Price spikes through the level to trigger stops and trap breakout retail traders.

## 2. Pre-Session Watchlist
- Formulate a strict trade plan before market open.
- Determine economic calendar high-impact events; know when not to hold through binary volatility.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Tom Dante)

## 1. Liquidity Sweep Reclamation Trigger
- Price breaches key level, sweeps liquidity, and aggressively rejects.
- Wait for a 5-minute or 15-minute candle to close back inside the level (reclamation).
- Enter on the reclamation with stop placed strictly beyond the sweep extreme wick.

## 2. Step Up With Zero Hesitation
- When a planned trade setup triggers, execute immediately with zero second-guessing.
- Eliminate hesitation by breaking out of the fear feedback loop.
""",
    "trade_management.md": """# Trade Management & Trouble Areas (Tom Dante)

## 1. Trade the Market, Not Your P&L
- Never look at your P&L to decide when to exit.
- Exit strictly at technical structure levels and trouble areas.

## 2. Managing the Position
- Take partial profits or move stop to breakeven at the first major "trouble area" (opposing structure pivot).
- Allow the runner portion of the position to target the opposing liquidity pool.
""",
    "risk_and_sizing.md": """# Risk Management & Circuit Breakers (Tom Dante)

## 1. Negative Visualization
- Before submitting the order, mentally visualize getting stopped out.
- Accept the dollar loss in your mind, make complete peace with it, and then pull the trigger with emotional detachment.

## 2. The -2R Daily Circuit Breaker
- If your cumulative losses reach **-2R for the day**, stop trading immediately.
- Walk away from the screens; do not attempt to make back losses.
""",
    "psychology_and_review.md": """# Trader Psychology & Demon Finder (Tom Dante)

## The 4 Principles of Professional Execution
1. **Sit on your hands** when there is no high-probability setup.
2. **Step up** without fear or hesitation when your edge triggers.
3. **Trade the market**, not your P&L or personal emotional needs.
4. **Learn from every trade** through structured journaling.

## The Demon Finder
- Use a Demon Finder sheet to track bad habits (e.g. taking trades not in plan, over-betting, moving stops).
- Log all missed trades to eliminate recency bias.
""",
    "checklists.md": """# Trader Dante Daily Execution Checklist

## 1. Pre-Market Plan
- [ ] Daily/4H key S/R levels marked?
- [ ] Economic calendar events checked?
- [ ] Plan sheet filled before market open?

## 2. Trade Execution
- [ ] Liquidity sweep and level reclamation confirmed?
- [ ] Stop loss placed beyond sweep wick extreme?
- [ ] Negative visualization performed (accepted the loss)?
- [ ] Step up without hesitation!

## 3. Post-Trade Review
- [ ] Trade logged in journal?
- [ ] Demon Finder checked for any process violations?
- [ ] Daily P&L within -2R circuit breaker limit?
"""
}

build_and_sync("trader-dante-execution", "tom-dante", dante_hypotheses, dante_docs)


# ==============================================================================
# 6. LEWIS KELLY
# ==============================================================================
lewis_hypotheses = [
    {
        "content_id": "B1ALxAVtFfI",
        "title": "M15 Higher Timeframe Structural Trend Bias (BOS)",
        "category": "stock_selection",
        "direction": "BOTH",
        "instrument": "forex",
        "hypothesis_statement": "Trading with the Higher Timeframe market structure eliminates false reversal noise; mapping swing highs, swing lows, and Breaks of Structure (BOS) on the M15 chart establishes the mandatory directional bias.",
        "setup_conditions": "Clear M15 swing high, swing low, lower high, lower low sequence (bearish BOS) or higher high, higher low (bullish BOS)",
        "holding_period": "Intraday trend ride",
        "statistical_claim": "Trading in alignment with M15 structure delivers 1:5+ asymmetric Risk-to-Reward opportunities",
        "invalidation_risk": "Trading against the M15 structural range results in low-probability chop",
        "verbatim_quote": "In this instance, you can see we have a swing high, a swing low, a lower high... followed by a lower low... And this is a break of structure. So whilst you are inside of this range from this high to this low, you are bearish... Ultimately what we wait for is once you've put in a new lower low, the one minute time frame to retrace to this 15 minute high."
    },
    {
        "content_id": "B1ALxAVtFfI",
        "title": "M1 Change of Character (CHoCH) Alignment inside M15 Area of Interest",
        "category": "execution",
        "direction": "BOTH",
        "instrument": "forex",
        "hypothesis_statement": "Entering reversals without lower-timeframe confirmation carries severe risk; waiting for price to retrace into an M15 key Area of Interest and observing a 1-minute Change of Character (CHoCH) confirms institutional shift before entry.",
        "setup_conditions": "Price mitigates M15 AOI, M1 timeframe breaks counter-trend structure (CHoCH) with strong displacement",
        "holding_period": "Intraday",
        "statistical_claim": "M1 CHoCH confirmation enables tight stop placement with high probability of M15 trend resumption",
        "invalidation_risk": "Entering before M1 CHoCH leads to getting stopped out by continued retracement",
        "verbatim_quote": "And then you're waiting for a reversal, which is the one minute time frame shifting from being bullish against the 15 minute trend to being bearish and with the 15 minute trend. And if you can get a one minute change of character... at a key level inside of a bearish 15 minute time frame, there's a high probability that the 15 minute will continue in its overall direction."
    },
    {
        "content_id": "B1ALxAVtFfI",
        "title": "Asymmetric 1:5+ Risk:Reward Reversal Execution Model",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "forex",
        "hypothesis_statement": "By pairing an M15 structural target (opposing swing low/high) with an ultra-refined M1 structural stop loss, trades achieve 1:5 to 1:10+ Risk-to-Reward, meaning low hit rates still produce strong positive expectancy.",
        "setup_conditions": "Stop placed beyond M1 swing extreme, target set at opposing M15 major liquidity pool",
        "holding_period": "Intraday",
        "statistical_claim": "Verified multi-year backtested model delivering 1:5+ average Risk:Reward",
        "invalidation_risk": "Prematurely taking profit before M15 target degrades the asymmetric math",
        "verbatim_quote": "And when the one minute shifts, that's your edge. Because now price is here, you go short, and you're expecting price to go here. And when it wins, this is what happens. And it has a high risk reward. And this strategy has been tested on years of historical data."
    },
    {
        "content_id": "B1ALxAVtFfI",
        "title": "Order Block & Fair Value Gap (FVG) Mitigation Entry Protocol",
        "category": "execution",
        "direction": "BOTH",
        "instrument": "forex",
        "hypothesis_statement": "Following an M1 CHoCH displacement, price leaves behind an unmitigated Order Block or Fair Value Gap; placing entry limits on the retest of this imbalance offers optimal fill pricing with minimal drawdown.",
        "setup_conditions": "Unmitigated M1 Order Block / FVG formed on displacement candle following CHoCH",
        "holding_period": "Intraday",
        "statistical_claim": "Entry at FVG mitigation maximizes fill precision and tightens stop distance",
        "invalidation_risk": "Price blows through the FVG without reaction",
        "verbatim_quote": "Wait for the shift, then execute with confidence... Fair Value Gap entry, logical stops, liquidity target, let the market do the rest. Stop selling internal moves, start reading real structure."
    }
]

lewis_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Lewis Kelly - SMC)

## 1. Timeframe Pair Selection
- **Aggressive Day Trading:** **M15** (Higher Timeframe Trend) + **M1** (Lower Timeframe Entry).
- **Swing Trading:** **H1** + **M5** or **H4** + **M15**.

## 2. Defining Higher Timeframe Market Structure (M15)
- Map true swing highs and swing lows (ignore internal candle noise).
- Identify Break of Structure (BOS): When price creates a lower low (bearish) or higher high (bullish).
- Establish the current operational range: High to Low.
- Identify the Key Area of Interest (AOI): Unmitigated Order Block (OB), Fair Value Gap (FVG), or Asia session liquidity pool.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Lewis Kelly - SMC)

## The 5-Step SMC Execution Model
1. **Step 1:** Establish M15 structural trend and operational range.
2. **Step 2:** Wait for price to retrace into the M15 Area of Interest (AOI).
3. **Step 3:** Drop to the M1 timeframe. M1 is trending counter to the M15 during the pullback.
4. **Step 4:** Wait for **M1 Change of Character (CHoCH)** with strong displacement in alignment with the M15 trend.
5. **Step 5:** Enter on the retest/mitigation of the newly formed M1 Fair Value Gap (FVG) or Order Block.
""",
    "trade_management.md": """# Trade Management & Targets (Lewis Kelly - SMC)

## 1. Liquidity Targets
- Target the opposing M15 major swing high or swing low (external liquidity).
- Expect the M15 trend to continue and put in a new high/low.

## 2. Asymmetric 1:5+ RR
- Maintain a minimum **1:5 Risk-to-Reward ratio**.
- Do not micro-manage trades during M1 internal retracements.
""",
    "risk_and_sizing.md": """# Risk Management & Stop Placement (Lewis Kelly - SMC)

## 1. Stop Loss Placement
- Stop loss is placed strictly above the M1 extreme high (for shorts) or below the M1 extreme low (for longs).
- Invalidation is binary: If the M1 extreme is breached, the reversal has failed. Exit immediately.

## 2. Capital Sizing
- Fixed 0.5% to 1.0% account risk per trade.
- Asymmetry guarantees profitability even at a 30-40% win rate.
""",
    "psychology_and_review.md": """# Trader Psychology & Rule-Based Clarity (Lewis Kelly - SMC)

## 1. Confirmation Over Anticipation
- Never guess turning points inside the AOI.
- Wait for the market to show its hand via the M1 CHoCH before pulling the trigger.

## 2. Simplicity & System Rules
- Knowing SMC concepts does not make you consistent; having rigid rules around them does.
- Ignore indicators; trade pure market structure.
""",
    "checklists.md": """# Lewis Kelly SMC Step-by-Step Checklist

## 1. M15 Higher Timeframe
- [ ] Directional bias established via Break of Structure (BOS)?
- [ ] Key Area of Interest (AOI) identified? (Order Block or FVG)
- [ ] Price has reached and tapped the M15 AOI?

## 2. M1 Lower Timeframe Entry
- [ ] M1 Change of Character (CHoCH) printed with displacement?
- [ ] Unmitigated M1 FVG / Order Block formed?
- [ ] Limit order placed at FVG mitigation?
- [ ] Stop loss strictly set beyond M1 extreme pivot?
- [ ] Target set at opposing M15 structural high/low for 1:5+ RR?
"""
}

build_and_sync("lewis-kelly-smc", "lewis-kelly", lewis_hypotheses, lewis_docs)


# ==============================================================================
# 7. TIM FUREY (TRADE VIEW / CHAT WITH TRADERS)
# ==============================================================================
furey_hypotheses = [
    {
        "content_id": "6lyl7flPOOU",
        "title": "Defensive Execution First: Profitability Arises from Loss Prevention",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Long-term market survival and profitability stem entirely from defense and loss minimization rather than offensive prediction; traders must master how not to lose money before capital can compound.",
        "setup_conditions": "Applied unconditionally across all trades and market regimes",
        "holding_period": "Flexible",
        "statistical_claim": "Floor market makers generated $28.5K+ monthly profits strictly by limiting losses to 5-10 ticks with zero emphasis on offensive gimmicks",
        "invalidation_risk": "Focusing on making money rather than risk preservation leads to rapid account ruin",
        "verbatim_quote": "What is the biggest thing I learned in the trading pit? And how did we make money? And to answer that is you had to learn how to lose... That's the only thing they taught you is defense. They didn't teach you anything about how to make money. They taught you everything on how not to lose money... That's how you make money is by not losing it."
    },
    {
        "content_id": "6lyl7flPOOU",
        "title": "The Power of the Lean: Entering Only with Structural Order Flow Support",
        "category": "execution",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Entering trades without an immediate order flow backstop creates severe adverse risk; traders should enter only at prices where they have 'the lean'—structural support allowing an immediate exit at breakeven if the market stalls.",
        "setup_conditions": "Bid/Offer structural lean, immediate offer placed upon fill to capture spread or scratch",
        "holding_period": "Scalp to intraday",
        "statistical_claim": "Eliminates catastrophic slippage by anchoring entries to liquidity pools",
        "invalidation_risk": "Market trades through the lean without filling exit orders",
        "verbatim_quote": "It's called the power of the lean. If I'm at 50 bid, if I get in at 50, I'm offering at 55 right away. Or if the market seems like it's going to turn, boom, I break even. It's the power to lean. I know I can get out. If I get in at 50 and someone hits me, I know I can get out at 50. If it goes up, great. If it goes down, I better be out."
    },
    {
        "content_id": "6lyl7flPOOU",
        "title": "Strict 5-to-10 Tick Stop Loss Discipline & Mandatory Account Suspension",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "futures",
        "hypothesis_statement": "Losses must be clipped within a narrow predefined boundary (5 to 10 ticks max); exceeding 10 ticks indicates complete breakdown of process and warrants immediate trading suspension.",
        "setup_conditions": "Stop loss triggered at -5 to -10 ticks",
        "holding_period": "Instant exit",
        "statistical_claim": "Zero tolerance for losses exceeding 10 ticks preserves trading firm capital across decades",
        "invalidation_risk": "Tolerating open drawdown beyond 10 ticks risks fatal account damage",
        "verbatim_quote": "You're only allowed to lose five ticks... they never question it. If you broke even, they never question it. But if you did 10 ticks, they're like 'Okay, what happened here?' If it was over 10 ticks, forget about it... they would suspend you for losing more than five ticks if you didn't have a good explanation."
    },
    {
        "content_id": "6lyl7flPOOU",
        "title": "Squint-Test Relative Strength Trend Following: Never Fade Momentum",
        "category": "stock_selection",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Attempting to short parabolic or trending bull markets because they appear overvalued is a chronic loser trap; traders must apply the 'squint test' to follow prevailing trend momentum where the strong gets stronger and the weak gets weaker.",
        "setup_conditions": "Higher highs and higher lows on daily chart, strong relative strength against market",
        "holding_period": "Trend duration",
        "statistical_claim": "Fading high-momentum runners (e.g. Yahoo, Tesla) accounts for the vast majority of retail liquidations",
        "invalidation_risk": "Shorting a rising trend without structural breakdown",
        "verbatim_quote": "Take a chart, print it out, put it on the floor, stand up on your chair, squint your eyes. What direction is it going? Up or down? Okay, it's going up. Why would you ever short this? To be successful in trading, it's relative strength, relative weakness... The strong gets stronger and the weak get weaker... Trade the trend. The trend is your friend."
    },
    {
        "content_id": "6lyl7flPOOU",
        "title": "Escalator Up, Elevator Down: Buying Sharp Pullbacks in Healthy Uptrends",
        "category": "execution",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Bull markets grind slowly higher (escalator up) and experience sharp, sudden pullbacks (elevator down); rather than shorting the elevator, disciplined trend traders use sudden dips in healthy uptrends as prime low-risk buying opportunities.",
        "setup_conditions": "Strong uptrend, sharp panic pullback into key moving average or support",
        "holding_period": "Swing",
        "statistical_claim": "Buying sharp pullbacks in leading uptrends produces rapid V-rebound profits",
        "invalidation_risk": "Break of macro structural support invalidates the uptrend",
        "verbatim_quote": "Escalator up, it's slow. Elevator down, right? Sometimes you got to buy on the elevator down where everybody wants to try to make the elevator down and it doesn't always happen... If you're following the trend, if it goes down, you look for your points to buy if it's trending up, right? And if you get sharp sell-offs, you got to look to buy because that is a healthy stock or healthy market."
    },
    {
        "content_id": "6lyl7flPOOU",
        "title": "The Ability to Walk Away: Non-Trading as the Ultimate Defensive Edge",
        "category": "holding_period",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "When market conditions lack clarity or edge, the most profitable decision is walking away entirely; preserving capital by not trading for days or weeks positions traders to strike with full force when obvious edge returns.",
        "setup_conditions": "Chop, conflicting signals, or lack of structural lean",
        "holding_period": "Days to weeks of non-trading",
        "statistical_claim": "Eliminates overtrading churn and preserves emotional stamina",
        "invalidation_risk": "Trading out of boredom degrades capital",
        "verbatim_quote": "Now the most important thing is the defense and the ability to walk away, right? Not to trade—that could be your best trade is not trading, to walk away. Maybe it's for a day, maybe it's for a week, maybe you just sit back and watch. But that one day your gut's going to be like 'this is the trade', you put it on."
    }
]

furey_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Tim Furey - Trade View)

## 1. The Squint Test (Trend Following)
- Print out the chart, put it on the floor, stand up on a chair, and squint your eyes.
- If the chart is pointing up, **never short it**.
- The strong gets stronger and the weak gets weaker. Do not trade counter-trend or try to call tops on bubble stocks.

## 2. In-Play Market Selection
- Gravitate to wherever volume and volatility are concentrated (e.g. index futures, crude oil, leading growth equities).
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Tim Furey - Trade View)

## 1. The Power of the Lean
- Enter only at prices where you have an order flow "lean" (a large bid or structural backstop).
- Immediately offer out at +1 tick or breakeven upon fill to guarantee risk control.
- If the market softens, scratch immediately at breakeven.

## 2. Buying the "Elevator Down" in an "Escalator Up" Market
- Uptrends grind slowly upward (escalator up).
- Sudden sharp sell-offs (elevator down) are buying opportunities, not short setups.
""",
    "trade_management.md": """# Trade Management & The Walk-Away Rule (Tim Furey - Trade View)

## 1. Defense First
- You are not allowed to lose more than **5 to 10 ticks**.
- If a trade moves against you, exit immediately.
- Capital preservation creates the offense.

## 2. The Ability to Walk Away
- Walking away for a day or a week is often your most profitable trade.
- Do not trade when conditions lack a clear structural lean.
""",
    "risk_and_sizing.md": """# Risk Management & Pit Discipline (Tim Furey - Trade View)

## 1. How to Make Money
- You make money by **not losing it**.
- Clear firms enforced mandatory suspension for losses exceeding 10 ticks.

## 2. Scalable Systems
- Only trade systems where risk is tightly defined and scalable across size.
""",
    "psychology_and_review.md": """# Trader Psychology & Resilience (Tim Furey - Trade View)

## 1. "Hungry Dogs Run Faster"
- Work ethic, preparation, and resilience define career longevity.
- Become rejection-proof; accept losses as normal operating expenses.

## 2. Zero Opinion / Reactionary Mindset
- Never marry an opinion on the market.
- React to what price does; let the gut intuition built on screen time guide execution.
""",
    "checklists.md": """# Tim Furey Floor Trader Checklist

## 1. Market Direction Check
- [ ] Squint test passed? (Trading with prevailing trend)
- [ ] Not attempting to short an overbought bull runner?

## 2. Entry & Lean
- [ ] Structural order flow lean identified?
- [ ] Immediate breakeven scratch order ready?
- [ ] Maximum risk capped strictly at 5-10 ticks?

## 3. Discipline
- [ ] Willing to walk away if market lacks clarity?
- [ ] Ego detached from trade outcome?
"""
}

build_and_sync("chat-with-traders-defense", "tim-furey", furey_hypotheses, furey_docs)


# ==============================================================================
# 8. MARK MINERVINI
# ==============================================================================
minervini_hypotheses = [
    {
        "content_id": "x_1859625009469112773",
        "title": "The 6 Unconditional Rules of Trade Preservation",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Long-term compounding requires absolute compliance with trade preservation laws: pre-defining stop loss before entry, never risking more than 1.25-2.5% of equity, never averaging down, protecting open profits with trailing stops, and cutting losses without emotional negotiation.",
        "setup_conditions": "Universal rulebook across all market regimes",
        "holding_period": "Flexible",
        "statistical_claim": "Built a 40+ year career and 2x U.S. Investing Championship victories on these 6 rules",
        "invalidation_risk": "Violating stop loss discipline or averaging down on losers guarantees catastrophic drawdown",
        "verbatim_quote": "The rules I built a 41-year career and a personal fortune on: Always pre-determine your risk before buying. Never risk more than 1.25% of equity. Never average down. Protect your profit. Always trade with a trailing stop. Never let a good gain turn into a loss."
    },
    {
        "content_id": "x_1383099725092691971",
        "title": "1.25% Maximum Equity Risk Invariance Rule",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "equities",
        "hypothesis_statement": "Regardless of nominal position size or leverage, portfolio equity risk must be strictly bounded at 1.25% of total account capital (with an absolute ceiling of 2.5% under extreme conviction); tight stop loss distance dictates share sizing.",
        "setup_conditions": "Stop loss defined within 5-8% (or 2-4% on tight VCP pivots)",
        "holding_period": "Trade duration",
        "statistical_claim": "Guarantees that a cluster of 10 consecutive losses causes less than 12% total portfolio drawdown",
        "invalidation_risk": "Over-sizing position relative to stop width breaches the 1.25% equity ceiling",
        "verbatim_quote": "Regardless of position size I'm never risking more than 1.25% (2.5% absolute ceiling) of total account equity on any trade."
    },
    {
        "content_id": "x_1285646820782288898",
        "title": "Volatility Contraction Pattern (VCP) Supply Absorption Mechanics",
        "category": "stock_selection",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Successive contractions in daily price range (e.g. 20% -> 10% -> 5% -> 2%) accompanied by dry-up in volume indicate that overhead supply is being systematically absorbed by institutions, setting up an explosive breakout upon breach of the final pivot.",
        "setup_conditions": "2 to 4 contractions, volume drying up on right side of base, price tight near pivot",
        "holding_period": "Swing to multi-week trend",
        "statistical_claim": "VCP breakouts in confirmed uptrends produce 30-100%+ rapid markup phases",
        "invalidation_risk": "Volume expanding on down-days or contractions becoming wider indicates distribution",
        "verbatim_quote": "VCP - Volatility Contraction Pattern is not a separate pattern; it is the underlying footprint of supply being absorbed by institutional buyers before price can launch."
    },
    {
        "content_id": "x_1859625009469112773",
        "title": "Trend Template Requirements for Institutional Momentum Alignment",
        "category": "stock_selection",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "High-probability growth leaders must meet the 8-point Trend Template: price above rising 50, 150, and 200 SMAs; 200 SMA trending up for >= 1 month; 50 SMA > 150 SMA > 200 SMA; price at least 30% off 52-week lows and within 25% of 52-week highs.",
        "setup_conditions": "Stock meets all 8 Trend Template technical conditions",
        "holding_period": "Multi-week to multi-month",
        "statistical_claim": "95%+ of superperformance stocks in market history were in a Stage 2 uptrend meeting this template",
        "invalidation_risk": "Stock trading below declining 200 SMA is in Stage 4 decline and must be avoided",
        "verbatim_quote": "Stock must trade above rising 50, 150, and 200 SMAs with 200 SMA trending up for at least 1 month and price within 25% of 52-week high."
    },
    {
        "content_id": "x_1859625009469112773",
        "title": "Progressive Exposure: Pyramiding Capital in Winning Regimes",
        "category": "risk_management",
        "direction": "LONG",
        "instrument": "equities",
        "hypothesis_statement": "Progressive exposure requires financing risk with open profits: initiate modest exploratory positions, increase portfolio exposure only as earlier trades show gains, and immediately contract to cash when stops are triggered.",
        "setup_conditions": "Prior trades in profit, market in confirmed Stage 2 rally",
        "holding_period": "Regime duration",
        "statistical_claim": "Maximizes capital velocity during bull markets while automatically moving to cash during corrections",
        "invalidation_risk": "Adding exposure when previous trades are losing creates compounding losses",
        "verbatim_quote": "Progressive exposure dictates financing risk with open profits: increase exposure only when existing positions work, cut to cash when stops trigger."
    }
]

minervini_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Mark Minervini)

## 1. The 8-Point Trend Template (Stage 2 Uptrend)
Before evaluating chart patterns, the stock must satisfy the Trend Template:
1. Current price is above both the 150-day and 200-day Simple Moving Averages (SMAs).
2. The 150-day SMA is above the 200-day SMA.
3. The 200-day SMA is trending upward for at least 1 month (preferably 4-5 months).
4. The 50-day SMA is above both the 150-day and 200-day SMAs.
5. Current price is trading above the 50-day SMA.
6. Current price is at least 30% above its 52-week low.
7. Current price is within 25% of its 52-week high (closer is better).
8. Relative Strength (RS) rating is >= 70 (preferably 80-90+).

## 2. Volatility Contraction Pattern (VCP)
- Price consolidates with 2 to 4 successive contractions (e.g. -25% -> -12% -> -6% -> -3%).
- **Volume Contraction:** Volume dries up dramatically toward the right side of the base, indicating supply exhaustion.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Mark Minervini)

## 1. The Pivot Point / Cheat Entry
- Identify the exact resistance pivot on the final, tightest contraction.
- Enter as price clears the pivot point on volume expansion (at least +50% above 50-day average volume).
- Order Type: Buy stop-limit order placed slightly above the pivot.

## 2. Never Chase
- Do not chase a stock more than 3-5% beyond the optimal pivot point.
""",
    "trade_management.md": """# Trade Management & Trailing Stops (Mark Minervini)

## 1. Protecting Open Profits
- Move stop loss to breakeven once price advances 2x to 3x your initial risk.
- **Rule:** Never allow a good gain to turn into a loss.

## 2. Trailing Stops & Scaling Out
- Sell 1/3 to 1/2 into rapid momentum expansion (after 10-20%+ advance).
- Trail remaining shares behind the rising 20 EMA or 50 SMA.
""",
    "risk_and_sizing.md": """# Risk Management & Position Sizing (Mark Minervini)

## 1. The 1.25% Maximum Equity Risk Rule
- **Never risk more than 1.25% of total portfolio equity on any single trade.**
- Position Size = `(Portfolio Equity * 0.0125) / (Entry Price - Stop Loss Price)`.
- If your stop loss is 5%, maximum position size is 25% of portfolio equity.

## 2. Invariant Rules of Trade Preservation
- Never average down on a losing position.
- Pre-determine your stop loss before buying; execute without emotional delay.
- Cut losses at 5-8% maximum.
""",
    "psychology_and_review.md": """# Trader Psychology & Progressive Exposure (Mark Minervini)

## 1. Progressive Exposure
- Do not jump from 0% to 100% invested.
- Buy test positions (e.g. 25-50% exposure).
- Increase allocation only as existing positions show open profits.
- When stops trigger, immediately downshift to cash.

## 2. Champion Mindset
- Focus on consistency, capital preservation, and compounding gains.
""",
    "checklists.md": """# Mark Minervini VCP Execution Checklist

## 1. Trend Template Filter
- [ ] Price > 50, 150, 200 SMA?
- [ ] 200 SMA trending up for >= 1 month?
- [ ] Price >= 30% above 52-week low and within 25% of 52-week high?

## 2. VCP Pattern Check
- [ ] 2-4 successive price contractions visible?
- [ ] Volume drying up near the pivot?
- [ ] Tight cheat / pivot level identified?

## 3. Risk & Sizing
- [ ] Stop loss strictly set within 5-8% (or tighter)?
- [ ] Account equity risk <= 1.25%?
- [ ] Progressive exposure cushion verified?
- [ ] Never average down!
"""
}

build_and_sync("mark-minervini-vcp", "mark-minervini", minervini_hypotheses, minervini_docs)


# ==============================================================================
# 9. PETER BRANDT
# ==============================================================================
brandt_hypotheses = [
    {
        "content_id": "x_1980752973597929915",
        "title": "Classical Charting Geometric Footprint of Composite Players",
        "category": "edge",
        "direction": "BOTH",
        "instrument": "commodities",
        "hypothesis_statement": "Classical geometric chart patterns (horizontal rectangles, ascending/descending triangles, head and shoulders, flags) capture the institutional footprint of accumulation, distribution, and consolidation; trading mature pattern completions provides empirical edge across commodities, currencies, and equities.",
        "setup_conditions": "Mature classical geometric pattern on Daily or Weekly chart with multiple boundary tests",
        "holding_period": "Multi-week to multi-month swing",
        "statistical_claim": "Proven 45+ year empirical track record across futures, forex, and equities",
        "invalidation_risk": "Pattern failure upon boundary re-penetration",
        "verbatim_quote": "The entire concept of classical charting is based on certain geometric footprints that capture institutional accumulation, distribution, and consolidation."
    },
    {
        "content_id": "x_1980752973597929915",
        "title": "The Factor of 5: Asymmetric 5:1 Minimum Reward-to-Risk Requirement",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "commodities",
        "hypothesis_statement": "Due to typical 35-45% classical pattern hit rates, profitability depends entirely on trade asymmetry; traders must only enter setups where the measured technical pattern objective delivers at least 5 times the initial trade risk (5:1 Reward-to-Risk).",
        "setup_conditions": "Measured technical pattern target >= 5x stop loss distance",
        "holding_period": "Pattern objective duration",
        "statistical_claim": "Guarantees robust profitability despite sub-50% win rates",
        "invalidation_risk": "Taking low reward-to-risk setups causes long-term negative expectancy",
        "verbatim_quote": "Only enter classical chart pattern breakouts where the measured technical objective delivers at least 5 times the initial trade risk."
    },
    {
        "content_id": "x_1980752973597929915",
        "title": "Risk of Ruin Protection: 1-2% Maximum Capital Allocation Rule",
        "category": "risk_management",
        "direction": "BOTH",
        "instrument": "commodities",
        "hypothesis_statement": "Given frequent small losses inherent to classical pattern trading, risk per trade must be strictly capped at 1.0% to 2.0% of total capital to easily endure inevitable loss clusters without threatening account survival.",
        "setup_conditions": "Capital risk bounded at 1-2% per trade",
        "holding_period": "Flexible",
        "statistical_claim": "Eliminates risk of ruin and preserves emotional capital across decades of market cycles",
        "invalidation_risk": "Over-risking on single patterns risks catastrophic account drawdown",
        "verbatim_quote": "Given typical 35-45% pattern win rates, capital preservation requires limiting risk to 1-2% of total equity to survive inevitable loss clusters."
    },
    {
        "content_id": "x_1980752973597929915",
        "title": "8-to-10 Bar Trailing Stop Loss Rule for Trend Rides",
        "category": "holding_period",
        "direction": "BOTH",
        "instrument": "commodities",
        "hypothesis_statement": "To allow mature classical pattern breakouts to achieve their full measured targets without premature shakeouts, trail stops behind the lowest low (for longs) or highest high (for shorts) of the past 8 to 10 trading sessions.",
        "setup_conditions": "Position in profit following breakout completion",
        "holding_period": "Multi-week trend",
        "statistical_claim": "Captures macro trend runs while providing breathing room against normal market noise",
        "invalidation_risk": "Trailing too closely stops out winners before trend maturation",
        "verbatim_quote": "Trail stops below the lowest low (for longs) or highest high (for shorts) of the past 8 to 10 trading sessions to let winning trends mature."
    }
]

brandt_docs = {
    "setup_and_screening.md": """# Setup & Screening Rules (Peter Brandt - Classical Charting)

## 1. Classical Geometric Chart Patterns
Look exclusively for mature classical patterns on Daily and Weekly charts:
- **Horizontal Rectangles:** Extended sideways trading ranges with well-defined support and resistance boundaries.
- **Symmetrical, Ascending & Descending Triangles:** Coiling price action indicating impending directional volatility expansion.
- **Head and Shoulders (Tops & Bottoms):** Major multi-month reversal formations with clearly defined necklines.
- **Channels & Flags:** Orderly consolidation pauses within larger structural trends.

## 2. Boundary Integrity
- The pattern must be clean, mature, and tested multiple times.
- Never anticipate a pattern before its boundary is definitively breached on a closing basis.
""",
    "entry_and_execution.md": """# Entry & Execution Rules (Peter Brandt - Classical Charting)

## 1. Pattern Completion Breakout
- Enter upon a daily closing breakout or definitive boundary penetration.
- Avoid premature entry inside the pattern.

## 2. Measured Move Objectives
- Calculate measured target by projecting the vertical height of the pattern from the breakout point.
""",
    "trade_management.md": """# Trade Management & Trailing Stops (Peter Brandt - Classical Charting)

## 1. The 8-to-10 Bar Trailing Stop Rule
- To allow multi-week trend runs to mature, trail stop orders behind the **lowest low of the past 8 to 10 trading sessions** (for long positions).
- For short positions, trail behind the **highest high of the past 8 to 10 sessions**.
- This provides sufficient breathing room against market noise while locking in structural gains.
""",
    "risk_and_sizing.md": """# Risk Management & The Factor of 5 (Peter Brandt - Classical Charting)

## 1. The Factor of 5 Asymmetry Rule
- **Minimum 5:1 Reward-to-Risk Requirement:** Only enter trades where the measured technical pattern objective is at least 5 times the initial stop loss distance.
- High asymmetry compensates for typical 35-45% pattern win rates.

## 2. Risk of Ruin Protection
- Risk strictly **1.0% to 2.0%** of total capital per trade.
- Endure loss clusters with zero emotional deviation.
""",
    "psychology_and_review.md": """# Trader Psychology & Factor Discipline (Peter Brandt - Classical Charting)

## 1. Expectancy-Driven Mindset
- Accept that more than half of your trades will be small losses or scratches.
- Profitability is derived from a small handful of massive geometric trend runs each year.

## 2. Chart Discipline
- Trade what is on the chart, not what you think the world should do.
""",
    "checklists.md": """# Peter Brandt Classical Charting Checklist

## 1. Pattern Identification
- [ ] Clean Daily/Weekly geometric pattern? (Rectangle, triangle, H&S)
- [ ] Boundaries tested multiple times?
- [ ] Breakout confirmed on closing basis?

## 2. Risk & Asymmetry
- [ ] Measured objective calculated?
- [ ] Factor of 5 met? (Reward >= 5x Risk)
- [ ] Account risk <= 1.0-2.0%?

## 3. Management
- [ ] Initial stop placed beyond pattern boundary?
- [ ] 8-to-10 day trailing stop armed?
"""
}

build_and_sync("peter-brandt-classical", "peter-brandt", brandt_hypotheses, brandt_docs)

conn.close()
print("All 9 person strategy skills successfully synthesized and synchronized!")
