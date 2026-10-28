import json, os, re
# key | kind | category | action | subject | claim | terms | aliases | person
C = [
 ("trail_ma10","rule","trade_management","HOLD","trail the remainder with the 10-day average","IF position held after partial profit THEN HOLD remainder UNTIL tf_daily close below ma_10","trailing_stop ma_10 partial_profit tf_daily","the 10-day|trail with the 10","p1"),
 ("trail_ma20_slow","rule","trade_management","HOLD","use the 20-day average for slower stocks","IF stock is slow moving THEN HOLD remainder UNTIL tf_daily close below ma_20","trailing_stop ma_20 tf_daily","the 20-day|slower names","p1"),
 ("partial_3_5_days","rule","trade_management","EXIT_PARTIAL","sell a third after three to five days","IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/3 of position","partial_profit breakout","sell a third|take some off","p1"),
 ("never_avg_down","rule","risk_and_sizing","AVOID","never average down on a loser","IF position is losing THEN AVOID averaging_down","averaging_down stop_loss","dont add to losers","p2"),
 ("stop_before_entry","rule","risk_and_sizing","EXIT","define the stop before entering","IF entering any trade THEN EXIT at a stop_loss defined before entry","stop_loss","stop first|know your stop","p2"),
 ("risk_1pct","rule","risk_and_sizing","SIZE","risk at most 1% of equity per trade","IF sizing a position THEN SIZE so risk is at most 1% of equity","risk_per_trade position_sizing","one percent risk","p2"),
 ("risk_025","rule","risk_and_sizing","SIZE","risk a quarter to half a percent per trade","IF taking a trade THEN SIZE risk at 0.25-0.5% of equity","risk_per_trade position_sizing","small risk per trade","p3"),
 ("daily_loss_2r","rule","risk_and_sizing","AVOID","stop trading after a 2R loss day","IF the day reaches the 2R daily_loss_limit THEN AVOID further trading","daily_loss_limit r_multiple","circuit breaker|stop for the day","p3"),
 ("halve_after_streak","rule","risk_and_sizing","SIZE","halve size after a losing streak","IF 3 consecutive losing days THEN SIZE down to 50% UNTIL 2 winning days","position_sizing losing_streak","cut size after red days","p3"),
 ("orb_5m","setup","entry_and_execution","LONG","buy the 5 minute opening range breakout","IF price breaks opening_range high on tf_5m THEN LONG","opening_range tf_5m breakout","ORB|first five minutes high","p4"),
 ("gap_and_go","setup","entry_and_execution","LONG","gap and go on news with volume","IF stock gaps up on a catalyst with rvol above 3 THEN LONG on the first pullback","gap_and_go catalyst rvol","gap up on news","p4"),
 ("ep_setup","setup","setup_and_screening","LONG","episodic pivot on earnings","IF earnings gap_up AND huge volume after a long base THEN LONG","episodic_pivot earnings gap_up","EP|earnings gap","p1"),
 ("vcp_def","definition","concept","NONE","what a VCP is","vcp IS progressive volatility contraction with volume drying up into the pivot","vcp volume_dry_up","volatility contraction pattern","p2"),
 ("htf_setup","setup","setup_and_screening","LONG","high tight flag","IF stock doubles in 8 weeks AND flags tightly THEN LONG on the breakout","high_tight_flag breakout","HTF|tight flag","p1"),
 ("flag_stop","rule","risk_and_sizing","EXIT","stop under the flag low","IF long from a bull_flag breakout THEN EXIT if price closes below the flag low","bull_flag stop_loss","stop below the flag","p4"),
 ("round_number_stops","rule","risk_and_sizing","AVOID","do not put stops on round numbers","IF placing a stop_loss THEN AVOID round_number prices","stop_loss round_number","stop hunting|round numbers","p3"),
 ("scratch_rule","rule","trade_management","EXIT","scratch when momentum dies","IF a new high lacks velocity THEN EXIT at breakeven","scratch_trade tape_reading","cut it flat|scratch","p3"),
 ("add_on_flag","rule","trade_management","ADD","add on one minute consolidation","IF breakout holds higher AND tf_1m pause forms THEN ADD above the wick highs","scaling_in tf_1m","pyramid|add to winners","p3"),
 ("tape_signature","setup","entry_and_execution","LONG","tape signature of a real breakout","IF buyers pay the offer AND offers clear without friction THEN LONG","tape_reading breakout","reading the tape","p3"),
 ("rvol_confirm","rule","setup_and_screening","LONG","volume confirms the breakout","IF breakout on rvol of 2-3 THEN LONG","rvol breakout","relative volume|volume confirmation","p3"),
 ("thin_volume_trap","rule","setup_and_screening","AVOID","breakouts on thin volume fail","IF breakout on half normal volume THEN AVOID","rvol breakout","low volume breakout","p3"),
 ("regime_ma","rule","setup_and_screening","LONG","trade breakouts only when 10 and 20 slope up","IF ma_10 above ma_20 AND both slope up THEN LONG breakouts","market_regime ma_10 ma_20","market timing|green light","p1"),
 ("regime_cash","rule","setup_and_screening","AVOID","stay in cash in bad markets","IF index below falling ma_20 THEN AVOID breakouts and stay in cash","market_regime ma_20","cash in downtrend|red light","p1"),
 ("exposure_ramp","rule","risk_and_sizing","ADD","ramp exposure gradually","IF market in low_volatility uptrend THEN ADD exposure from 0 to 30 percent first","scaling_in uptrend","progressive exposure","p1"),
 ("overnight_cap","rule","risk_and_sizing","SIZE","cap overnight position size","IF holding overnight THEN SIZE at most 25% of funds","overnight_hold position_sizing","max overnight allocation","p1"),
 ("gap_risk_overnight","observation","market_dynamics","NONE","overnight gaps hurt held losers","held losers TENDS TO gap against you WHEN you hold overnight through news","gap_risk overnight_hold","gap against you","p2"),
 ("close_shorts_same_day","rule","trade_management","EXIT","close shorts the same day","IF short position THEN EXIT the same day","short_selling intraday_exit","do not swing shorts","p4"),
 ("longs_overnight","observation","trade_management","NONE","strong longs continue overnight","trend longs TENDS TO continue into day two WHEN strength holds at the close","trend_following overnight_hold","hold winners overnight","p4"),
 ("adr_filter","rule","setup_and_screening","AVOID","skip stocks with low ADR","IF adr_pct below 4% THEN AVOID","adr_pct","average daily range filter","p4"),
 ("liquidity_filter","rule","setup_and_screening","AVOID","trade liquid names only","IF stock lacks liquidity THEN AVOID","liquidity","illiquid names","p4"),
 ("in_play","rule","setup_and_screening","AVOID","only trade in-play stocks","IF stock shows no unusual volume or catalyst THEN AVOID its levels","catalyst support resistance","in play|stocks in play","p3"),
 ("clean_level","rule","setup_and_screening","AVOID","use clean obvious levels","IF a level is not obvious THEN AVOID its break","support resistance","clean level","p3"),
 ("mtf_alignment","observation","setup_and_screening","NONE","levels aligned across time frames matter more","levels TENDS TO matter more WHEN several time frames align","support resistance","multi timeframe|zoom out","p3"),
 ("consolidation_tension","mechanism","entry_and_execution","NONE","tight consolidation builds tension","consolidation without pullback CAUSES stronger breakouts BECAUSE shorts must cover","consolidation breakout","tension","p3"),
 ("journal_practice","practice","psychology_and_review","NONE","journal every trade with screenshots","keeping a trade_journal IMPROVES holding winners FOR discretionary traders","trade_journal","journaling|screenshots","p2"),
 ("weekly_review","practice","psychology_and_review","NONE","review trades weekly","weekly trade_review IMPROVES mistake reduction FOR traders","trade_review","weekend review","p2"),
 ("daily_plan","practice","psychology_and_review","NONE","write a daily plan before the open","a daily_plan IMPROVES selectivity FOR day traders","daily_plan","pre market plan","p3"),
 ("walk_away","rule","psychology_and_review","AVOID","walking away is a trade","IF no trade you believe in THEN AVOID trading to avoid overtrading","overtrading discipline","sit on your hands","p3"),
 ("revenge_trading","practice","psychology_and_review","NONE","revenge trading destroys accounts","revenge_trading HURTS account equity FOR traders after a loss","revenge_trading tilt","tilt after losses","p2"),
 ("negative_visualization","practice","psychology_and_review","NONE","visualize the loss before entering","visualizing the stop-out IMPROVES acceptance of loss FOR hesitant traders","stop_loss discipline","make peace with the loss","p3"),
 ("demon_finder","practice","psychology_and_review","NONE","track bad habits with a demon finder","a demon finder IMPROVES finding bad practices FOR traders","trade_review daily_plan","bad habit tracker","p3"),
 ("defense_first","practice","psychology_and_review","NONE","learn defense before offense","prioritizing defense IMPROVES profitability FOR new traders","discipline","not losing money first","p3"),
 ("trend_never_short","rule","setup_and_screening","AVOID","never short an uptrend","IF the trend is up THEN AVOID shorting because it looks overvalued","trend_following uptrend short_selling","dont fight the trend","p3"),
 ("buy_elevator_down","rule","entry_and_execution","LONG","buy sharp selloffs in uptrends","IF uptrend AND sharp sell-off THEN LONG the pullback","uptrend pullback","escalator up elevator down","p3"),
 ("relative_strength","observation","market_dynamics","NONE","strong stocks get stronger","stocks with relative_strength TENDS TO keep leading WHEN ranked","relative_strength","the strong get stronger","p3"),
 ("pullback_20ema_add","rule","entry_and_execution","ADD","add on the first pullback to the 20 EMA","IF breakout pulls back to ema_20 on light volume THEN ADD","pullback ema_20 breakout","first pullback","p4"),
 ("vwap_reclaim","setup","entry_and_execution","LONG","long on a VWAP reclaim","IF price reclaims vwap after a flush THEN LONG","vwap_reclaim vwap","reclaim of vwap","p4"),
 ("first_red_day","setup","entry_and_execution","SHORT","short the first red day after a parabolic run","IF parabolic_move ends with first_red_day THEN SHORT","parabolic_short first_red_day","first red day short","p4"),
 ("parabolic_exhaustion","observation","market_dynamics","NONE","parabolic moves end in climax","parabolic_move TENDS TO end in climax_top WHEN volume spikes","parabolic_move climax_top","blow off top","p4"),
 ("sharpe_momentum","metric","research_method","NONE","momentum sharpe in a backtest","12-1 momentum HAS sharpe_ratio = 0.6 ON US stocks 2005-2020","sharpe_ratio momentum backtest","sharpe of momentum","p2"),
 ("costs_matter","observation","research_method","NONE","costs erase small account scalping","transaction_costs TENDS TO erase edge WHEN trading frequency is high","transaction_costs slippage","fees kill scalping","p2"),
 ("overfitting","observation","research_method","NONE","backtests overfit easily","backtest results TENDS TO degrade WHEN parameters are tuned on the same data","overfitting backtest walk_forward","curve fitting","p2"),
 ("survivorship","mechanism","research_method","NONE","survivorship bias inflates results","survivorship_bias CAUSES inflated returns BECAUSE delisted stocks vanish","survivorship_bias backtest","delisted stocks","p2"),
 ("lookahead","mechanism","research_method","NONE","look-ahead bias invalidates a test","look_ahead_bias CAUSES false edges BECAUSE future data leaks","look_ahead_bias backtest","future leak","p2"),
 ("real_yields","mechanism","market_dynamics","NONE","rising real yields hit growth stocks","rising real_yield CAUSES multiple_compression BECAUSE cash flows are discounted","real_yield multiple_compression growth_stocks","rates vs growth","p2"),
 ("fomc_volatility","observation","market_dynamics","NONE","volatility around FOMC","volatility TENDS TO spike WHEN fomc decisions land","fomc volatility","fed day volatility","p2"),
 ("earnings_gap_fade","observation","market_dynamics","NONE","earnings gaps that close weak fade","earnings gap_up stocks TENDS TO fade WHEN they close near lows","gap_up earnings","gap fade","p4"),
 ("position_size_a_plus","rule","risk_and_sizing","SIZE","size up on A+ setups","IF a setup is an A+ setup THEN SIZE up","position_sizing","exponential bet sizing","p4"),
 ("kelly_caution","observation","risk_and_sizing","NONE","full kelly is too aggressive","full kelly_criterion TENDS TO cause deep drawdowns WHEN edge is overestimated","kelly_criterion max_drawdown","half kelly","p2"),
 ("expectancy_def","definition","concept","NONE","what expectancy means","expectancy IS win rate times average win minus loss rate times average loss","expectancy win_rate average_win average_loss","edge per trade","p2"),
 ("r_multiple_thinking","practice","risk_and_sizing","NONE","think in R multiples","thinking in r_multiple IMPROVES risk consistency FOR traders","r_multiple","measure in R","p2"),
 ("premarket_prep","practice","setup_and_screening","NONE","prepare a pre-market watchlist","pre-market premarket_prep IMPROVES selectivity FOR day traders","premarket_prep premarket","watchlist","p3"),
 ("open_chop","practice","entry_and_execution","NONE","avoid the first 15 minutes","avoiding entries in the first 15 minutes after market_open IMPROVES results FOR chop-prone traders","market_open overtrading","open chop","p4"),
 ("short_squeeze","mechanism","market_dynamics","NONE","short squeezes feed themselves","rising price with high short_interest CAUSES more buying BECAUSE shorts must cover","short_squeeze short_interest","forced covering","p4"),
 ("options_theta","observation","market_dynamics","NONE","theta decay hurts long options","long options TENDS TO lose to theta_decay WHEN timing is off","theta_decay options","time decay","p4"),
 ("zero_dte_cycles","practice","trade_management","NONE","0dte removes overnight risk","trading zero_dte options IMPROVES turnover FOR premium sellers","zero_dte options","same day expiry","p4"),
 ("level2_reading","practice","entry_and_execution","NONE","read level 2 for absorption","reading level_2 IMPROVES entry timing FOR day traders","level_2 tape_reading","order book absorption","p4"),
 ("stop_hunt","observation","market_dynamics","NONE","stops cluster at obvious levels","stop orders TENDS TO cluster at round_number levels WHEN levels are obvious","stop_order round_number liquidity_sweep","liquidity sweep","p3"),
]
PERSONS = ["p1","p2","p3","p4"]
q = lambda s: "'" + s.replace("'", "''") + "'"
out = ["-- Search eval fixture: ~%d fictional cards over a handful of persons. Generated by evals/search/gen_fixture.py; each card's `notes` carries `fixture_key: <key>`." % len(C),
       "INSERT INTO agent_runs (id, skill, harness, model) VALUES (900, 'eval-fixture', 'manual', 'fixture');"]
for pid in PERSONS:
    out.append(f"INSERT INTO persons (id, canonical_name) VALUES ('fx-{pid}', 'Fixture Person {pid[1]}');")
out.append("INSERT INTO sources (id, platform, kind, title) VALUES ('file:site:fixture', 'file', 'site', 'fixture');")
out.append("INSERT INTO contents (id, source_id, platform, content_type, title, process_status) VALUES ('file:fixture0000000001', 'file:site:fixture', 'file', 'file', 'fixture document', 'processed');")
for i, (key, kind, cat, act, subj, claim, terms, aliases, pid) in enumerate(C):
    quote = claim.split(" THEN ")[0].replace("IF ", "").capitalize() + " -- " + subj
    out.append(f"INSERT INTO content_segments (content_id, seq, kind, locator_json, text) VALUES ('file:fixture0000000001', {i}, 'paragraph', '{{\"para\": {i}}}', {q(quote)});")
    ts = json.dumps(terms.split()); al = json.dumps(aliases.split("|"))
    out.append("INSERT INTO knowledge_cards (id, card_version, kind, domain, category, subject, claim, conditions_json, action, horizon, terms_json, aliases_json, evidence_level, notes, transformer_version, produced_by, run_id) "
               f"VALUES ({i+1}, 1, '{kind}', 'trading_strategy', '{cat}', {q(subj)}, {q(claim)}, '[]', '{act}', 'n/a', {q(ts)}, {q(al)}, 'claimed', 'fixture_key: {key}', 'kt-1.0', 'manual/fixture', 900);")
    out.append(f"INSERT INTO card_citations (card_id, content_id, segment_seq, locator_json, person_id, speaker_role, quote) VALUES ({i+1}, 'file:fixture0000000001', {i}, '{{\"para\": {i}}}', 'fx-{pid}', 'owner', {q(quote)});")
open("evals/search/fixture_db.sql", "w").write("\n".join(out) + "\n")
# 15 cases: question -> expected keys (cards that answer it); must_not = clearly unrelated keys
S = [
 ("how should I trail a stop on a winner after taking profits", ["trail_ma10","trail_ma20_slow","partial_3_5_days"], ["vwap_reclaim"]),
 ("what percent of my account should I risk on one trade", ["risk_1pct","risk_025"], ["fomc_volatility"]),
 ("when should I stop trading for the day", ["daily_loss_2r","halve_after_streak","walk_away"], ["vcp_def"]),
 ("is it ok to hold positions overnight", ["gap_risk_overnight","longs_overnight","overnight_cap","close_shorts_same_day"], ["journal_practice"]),
 ("how do I know a breakout is real", ["rvol_confirm","tape_signature","thin_volume_trap","consolidation_tension"], ["kelly_caution"]),
 ("where should I place my stop loss", ["stop_before_entry","flag_stop","round_number_stops","stop_hunt"], ["sharpe_momentum"]),
 ("should I average down on a losing trade", ["never_avg_down"], ["gap_and_go"]),
 ("which market conditions are good for breakout trading", ["regime_ma","regime_cash","exposure_ramp"], ["options_theta"]),
 ("how do I stop overtrading and revenge trading", ["walk_away","revenge_trading","open_chop","daily_plan"], ["real_yields"]),
 ("what mistakes make backtests unreliable", ["overfitting","survivorship","lookahead","costs_matter"], ["orb_5m"]),
 ("how do support and resistance levels work best", ["clean_level","in_play","mtf_alignment","consolidation_tension"], ["options_theta"]),
 ("what is a volatility contraction pattern", ["vcp_def"], ["short_squeeze"]),
 ("how to handle shorting in an uptrend", ["trend_never_short","close_shorts_same_day"], ["journal_practice"]),
 ("how should I review my trades to improve", ["journal_practice","weekly_review","demon_finder","negative_visualization"], ["htf_setup"]),
 ("why do growth stocks fall when interest rates rise", ["real_yields"], ["orb_5m"]),
]
for i, (qn, exp, mn) in enumerate(S, 1):
    json.dump({"question": qn, "expected_card_refs": exp, "must_not": mn}, open(f"evals/search/s{i:02d}.json", "w"), indent=1)
    open(f"evals/search/s{i:02d}.json", "a").write("\n")
print(len(C), len(S))
