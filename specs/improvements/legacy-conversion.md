# Legacy conversion (Phase 2)

> Date: 2026-10-28. Work done by the harness agent (Claude Code, claude-sonnet-5-5) on the migrated `data/knowledge.db`; one run per person (`kb run list --skill market-idea-miner`).
> **Needs your decision:** the lost rules below, and the deletion of `legacy/person-skills/`, `legacy/meta-skills/`, `legacy/scripts/` (nothing was deleted).

## Result

| | Legacy | Now |
|---|---|---|
| Hypotheses | 66 | 46 converted into cards (some into several), 11 duplicates, 9 not converted (below) |
| Knowledge cards | 0 | 58 active, each with a verified quote (except 2 flagged arXiv stub cards), 22 links, 58 dedup decisions |
| Person rulebooks | 9 folders on disk | 9 rulebooks in `person_skills` (46 rows), `kb skill get <person> --render markdown` |

## What the conversion found (please read)

The legacy hypotheses were not verbatim: **44 of the 66 quotes could not be matched in the stored text** (some only because they span two segments or use "..." ellipses, the rest because the words are not there), and several statements added rules that the source never states (a 5:1 reward-to-risk rule attributed to a post that has no such sentence, a 3-5 day partial-profit rule attributed to a stream that never says it, and so on). The spec says to rewrite each rule as a card citing the original content, "with a legacy citation if needed". I did **not** create cards whose citation contradicts the source text, because that would attribute claims to a real person that the stored content does not support. Instead:

- every card was rewritten from the actual segment text, with an exact quote (the validator checks it);
- hypotheses whose claim is not in the source are listed below as **not converted**, with the reason;
- the legacy rulebook rules that no stored source supports are listed under **Lost rules**.

Several of those rules are genuine, well known methods of the person (for example Minervini's trend template, Brandt's factor of 5). They should come back through real sources: use `/finsocnet:explore` to fetch the person's own posts, books and videos, and the miner will create cards with real citations.

Two cards (11 and 12, from arXiv stubs) keep `quote_verified = 0`: the stored content is a metadata stub, so their quotes could not be checked. Retire them (`kb card retire`) if you prefer.

## Hypothesis mapping

| Legacy | Person | Title | Outcome |
|---|---|---|---|
| H1 | UCcIvNGMBSQWwo1v3n-ZRBCw | Overnight Multi-Day Continuation for Trend Longs | cards 1 |
| H2 | UCcIvNGMBSQWwo1v3n-ZRBCw | Intraday Close for Short Selling (Avoid Overnight Short Swin | cards 2 |
| H3 | UCcIvNGMBSQWwo1v3n-ZRBCw | Minimum 4% ADR (Average Daily Range) Volatility Filter | cards 7 |
| H4 | UCcIvNGMBSQWwo1v3n-ZRBCw | Focus Group Edge Criteria (72% Win Rate Filter) | cards 23 |
| H5 | UCcIvNGMBSQWwo1v3n-ZRBCw | Exponential Bet Sizing on High-Conviction A+ Setups | cards 3 |
| H80 | reddit_ehtelgaeb | Options Theta Decay vs Directional Timing Friction | cards 8 |
| H82 | reddit_ehtelgaeb | 0DTE Credit Spreads Overnight Risk Elimination | cards 10 |
| H83 | medium_mediumauthor | Causal Conditioning of Fund Leverage on Liquidity | cards 4 |
| H84 | arxiv_org | Deep RL Execution with Non-Linear Market Impact Penalty | cards 11 |
| H85 | arxiv_org | Level-2 Limit Order Book Depth Representation for Tick Alpha | cards 12 |
| H86 | x_qullamaggie | Asymmetric Portfolio Heat & 0.2-0.5% Trade Risk Limit | cards 13 |
| H87 | x_qullamaggie | Setup Grading & Market Regime Filter (5-Star vs 3-Star) | cards 14 |
| H88 | x_theonelanceb | Right Side of the V & Channel Breakdown Exhaustion | NO CARD: the post only says the concept is important; it states no rule |
| H89 | x_theonelanceb | Defined Risk Invariance & Multi-Timeframe Performance Review | cards 16 |
| H90 | x_peterlbrandt | Classical Charting Geometric Footprint of Composite Players | cards 5 |
| H91 | x_markminervini | The 6 Unconditional Rules of Trade Preservation | cards 17 |
| H92 | x_markminervini | 1.25% Maximum Equity Risk Invariance Rule | cards 18 |
| H93 | x_markminervini | Volatility Contraction Pattern (VCP) Supply Absorption Mecha | cards 19 |
| H94 | shay-humbled-trader | Overnight Multi-Day Continuation for Trend Longs | duplicate of H1 (same quote, same card) |
| H95 | shay-humbled-trader | Intraday Close for Short Selling (Avoid Overnight Short Swin | duplicate of H2 |
| H96 | shay-humbled-trader | Minimum 4% ADR (Average Daily Range) Volatility Filter | duplicate of H3 |
| H97 | shay-humbled-trader | Focus Group Edge Criteria (72% Win Rate Filter) | duplicate of H4 |
| H98 | shay-humbled-trader | Exponential Bet Sizing on High-Conviction A+ Setups | duplicate of H5 |
| H99 | kristjan-qullamaggie | Episodic Pivot (EP) High Volume Earnings Catalyst Expansion | cards 24 |
| H100 | kristjan-qullamaggie | Opening Range Breakout (ORB) on Gap Day Consolidation | cards 25 |
| H101 | kristjan-qullamaggie | The 3-to-5 Day Partial Profit Rule & 10/20 EMA Trailing Stop | NOT CONVERTED: the stream never states a 3-5 day partial rule or a 10/20 EMA trail; the only support is 'as long as we can hold the 10 and 20' (covered by the regime card) |
| H102 | kristjan-qullamaggie | Market Regime Filter (Green/Yellow/Red Light) via 10/20/100  | cards 26 |
| H103 | kristjan-qullamaggie | Progressive Exposure and Margin Deployment in Low Volatility | cards 27 |
| H104 | kristjan-qullamaggie | Asymmetric Portfolio Heat & 0.25-0.5% Trade Risk Limit | duplicate of H86; its quote ('produces 100x account expansions') is not in the source post |
| H105 | lance-breitstein | The 5 Support & Resistance Criteria for Inflection Point Edg | cards 28, 31 |
| H106 | lance-breitstein | In-Play Asset Filter: Volume, Volatility & Catalyst Discover | cards 29 |
| H107 | lance-breitstein | Proper Consolidation & Tension Building Before Breakout | cards 30 |
| H108 | lance-breitstein | Right Side of the V & Channel Breakdown Exhaustion | duplicate of H88 |
| H109 | lance-breitstein | Multi-Timeframe Level Alignment for Institutional Swarming | cards 32 |
| H110 | lance-breitstein | Predefined Risk Invariance & A+ Exponential Sizing | NOT CONVERTED: the post does not state 5x-10x sizing or A+/C grading; its 'simple repeatable setups with defined risk' and 'reviews' are converted (H89, H90) |
| H111 | mike-bellafiore | 9/10 Technical Chart Level as Independent Catalyst | cards 33, 37 |
| H112 | mike-bellafiore | Pre-Breakout Relative Volume (RVOL >= 2x) Participation Filt | cards 38, 39 |
| H113 | mike-bellafiore | Tape Reading Aggression & Frictionless Offer Clearing | cards 40 |
| H114 | mike-bellafiore | Non-Round Stop Loss Placement Rule (.09 / .14 / .24 Offset) | cards 41, 42, 43 |
| H115 | mike-bellafiore | Adding to Winners on Intraday Consolidation Wick Breaks | cards 44 |
| H116 | mike-bellafiore | The Scratch Rule: Immediate Liquidation on Momentum Stall | cards 45 |
| H117 | tom-dante | The 4 Non-Negotiable Principles of Professional Execution | cards 34 |
| H118 | tom-dante | Institutional Liquidity Sweep & S/R Level Reclamation | cards 50 |
| H119 | tom-dante | Negative Visualization for Zero-Hesitation Execution | cards 49 |
| H120 | tom-dante | The -2R Daily Drawdown Circuit Breaker | cards 48 |
| H121 | tom-dante | Trade the Market, Not Your P&L or Emotional Expectations | cards 46 |
| H122 | tom-dante | The Daily Trade Plan, Logging Missed Trades & The Demon Find | cards 47 |
| H123 | lewis-kelly | M15 Higher Timeframe Structural Trend Bias (BOS) | cards 35 |
| H124 | lewis-kelly | M1 Change of Character (CHoCH) Alignment inside M15 Area of  | cards 51 |
| H125 | lewis-kelly | Asymmetric 1:5+ Risk:Reward Reversal Execution Model | cards 52 |
| H126 | lewis-kelly | Order Block & Fair Value Gap (FVG) Mitigation Entry Protocol | NOT CONVERTED: the 7-segment transcript never mentions fair value gaps or order blocks |
| H127 | tim-furey | Defensive Execution First: Profitability Arises from Loss Pr | cards 36 |
| H128 | tim-furey | The Power of the Lean: Entering Only with Structural Order F | cards 53 |
| H129 | tim-furey | Strict 5-to-10 Tick Stop Loss Discipline & Mandatory Account | cards 54 |
| H130 | tim-furey | Squint-Test Relative Strength Trend Following: Never Fade Mo | cards 55, 56 |
| H131 | tim-furey | Escalator Up, Elevator Down: Buying Sharp Pullbacks in Healt | cards 58 |
| H132 | tim-furey | The Ability to Walk Away: Non-Trading as the Ultimate Defens | cards 57 |
| H133 | mark-minervini | The 6 Unconditional Rules of Trade Preservation | duplicate of H91/H92; the quote mixes rules the post does not state (the post has no 1.25% rule, no trailing-stop rule) |
| H134 | mark-minervini | 1.25% Maximum Equity Risk Invariance Rule | duplicate of H92 (cards from the original post) |
| H135 | mark-minervini | Volatility Contraction Pattern (VCP) Supply Absorption Mecha | duplicate of H93 |
| H136 | mark-minervini | Trend Template Requirements for Institutional Momentum Align | NOT CONVERTED: the post does not state the trend template |
| H137 | mark-minervini | Progressive Exposure: Pyramiding Capital in Winning Regimes | NOT CONVERTED: the post does not state progressive exposure (the same idea from Qullamaggie is card 27) |
| H138 | peter-brandt | Classical Charting Geometric Footprint of Composite Players | duplicate of H90 |
| H139 | peter-brandt | The Factor of 5: Asymmetric 5:1 Minimum Reward-to-Risk Requi | NOT CONVERTED: the post does not state a 5:1 minimum reward to risk |
| H140 | peter-brandt | Risk of Ruin Protection: 1-2% Maximum Capital Allocation Rul | NOT CONVERTED: the post does not state 1-2% risk or 35-45% win rates |
| H141 | peter-brandt | 8-to-10 Bar Trailing Stop Loss Rule for Trend Rides | NOT CONVERTED: the post does not state an 8-10 bar trailing stop |

(H105 became the five-criteria cards 28, 29, 30, 31, 32; H117 became card 34 plus H121, H122 and H120 cards; H127-H132 and H123-H125 are in the table above.)

## Lost rules (legacy rulebook rules with no supporting stored source)

| Person | Rules not present in any stored content (dropped) |
|---|---|
| Kristjan Qullamaggie | High Tight Flag and base-breakout setups; green/yellow/red light details (100-day MA, EMA/SMA pullback levels); stop at the low of day; position-size formula; 3-5 day partial profit and breakeven stop; 10/20 EMA daily or 60-minute trailing exit; "ignore macro news"; "20-30% of the year produces the profits" (the stream says something close; can be re-added) |
| Lance Breitstein | Right Side of the V entry steps; second-day plays; partial profits and multi-time-frame trailing; A+/B/C grading with 5x-10x sizing; "draw fewer lines"; databasing best setups (the video recommends it; can be re-added) |
| Lewis Kelly | Time-frame pair table; area-of-interest definition (order block, fair value gap, Asia liquidity); the 5-step model's FVG/order-block entry; liquidity targets; fixed 1:5 reward to risk; stop placement at the one-minute extreme; 0.5-1.0% risk; "confirmation over anticipation" |
| Mark Minervini | 8-point trend template; contraction counts and volume rules; pivot entry with +50% volume; never chase more than 3-5%; breakeven stop at 2-3x risk; sell 1/3-1/2 after 10-20%; trail on 20 EMA / 50 SMA; cut losses at 5-8%; progressive exposure |
| Mike Bellafiore | Sector and market tailwind step; volume-surge bar; defined structural exits (2-minute low, consolidation break, tape shift); conviction sizing (A vs B); "one good trade" mindset; playbook grading |
| Peter Brandt | Pattern list (rectangles, triangles, head and shoulders, flags) and boundary integrity; closing-basis breakout entry; measured move objective; 8-10 bar trailing stop; factor of 5; 1-2% risk; expectancy mindset (only the first principle of classical charting is supported) |
| Shay (Humbled Trader) | Daily chart setup (20 EMA / 50 SMA); intraday long and short triggers; leveraged ETF use; stop under the consolidation base; AI P&L dashboard review steps; "focus over strategy accumulation"; B/C setups at 25-50% size |
| Tim Furey | Offer out at +1 tick on fill; scalable-systems rule; "hungry dogs run faster"; "zero opinion" mindset; mandatory suspension beyond 10 ticks (the video says five ticks; card 54 keeps that) |
| Tom Dante | Liquidity-sweep reclamation entry (the video only says to leave resting orders in); partial profits or breakeven at the first trouble area; pre-session watchlist and economic calendar; the fourth principle as "structured journaling" (the video says learn from mistakes); logging missed trades |

## Acceptance

- `kb skill get <person> --render markdown` works for all 9 persons; every rule references active cards that cite that person (validator-enforced); no timestamps.
- 0 lost rules **only if you accept the table above**; otherwise tell me which rule to rebuild from a real source.
- `ls .agents/skills` contains no person folders (done in Phase 0).
