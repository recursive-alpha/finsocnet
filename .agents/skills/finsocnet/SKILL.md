---
name: finsocnet
description: Explore, search, filter, and inspect mined creator trading hypotheses, setups, and verbatim quotes across financial social media channels via single-binary Go CLI and Chat TUI.
metadata:
  version: "0.1.0"
---

# FinSocNet: Financial Social Network Hypothesis Explorer

A high-performance single-binary tool and interactive Chat TUI (built in Go) to explore mined trading hypotheses, verify second-level timestamped quotes, and bridge requests to harness agents (Claude, Codex, Pi, Hermes, OpenClaw, OMP, DeepSeek Harness/DSH).

## 1. When to Activate

Activate this skill when:
- Searching or verifying empirical trading hypotheses mined from creator channels (Lance Breitstein, Qullamaggie, SMB Capital, Trader Dante, Chat With Traders, Humbled Trader).
- Finding specific trading setups by category (`holding_period`, `execution`, `risk_management`, `stock_selection`, `edge`).
- Inspecting ground-truth transcript quotes, holding periods, statistical claims, and invalidation rules.
- Requesting automated backtests, rule reviews, or hypothesis critiques across harness agents.

## 2. CLI Execution Commands

Run directly from any terminal or bash tool:

```bash
# 1. Search hypotheses by statement, setup, or keywords
finsocnet search "daily positions"
finsocnet search "breakout"

# 2. View full hypothesis card with verbatim quotes and timestamps
finsocnet view 2
finsocnet view 18

# 3. Filter hypotheses by category or direction
finsocnet hypo holding_period
finsocnet hypo short
finsocnet hypo execution long

# 4. Creator and channel intelligence
finsocnet creators
finsocnet contents
finsocnet skills

# 5. Database metrics and statistics
finsocnet stats

# 6. Dispatch prompt to harness agent with auto-injected hypothesis context
finsocnet claude "analyze execution risk on #2"
finsocnet codex "write a polars backtest for #3"
finsocnet hermes "verify invalidation conditions on #5"
finsocnet dsh "evaluate statistical edge for #1"
```

## 3. Interactive Chat TUI (Codex / OMP Style)

Launch the interactive chat interface:
```bash
finsocnet
```

Inside the TUI, use slash commands with tab-autocompletion:
- `/search <query>`: Live search across statement, setup conditions, and quotes
- `/view <id>`: Inspect detailed card and set active hypothesis context
- `/hypo [cat/dir]`: Filterable hypotheses table
- `/creators`: Creator and channel statistics
- `/contents`: Ingested video sources and URLs
- `/skills`: Catalog of synthesized User Agent Skills
- `/stats`: Summary metrics
- `/<agent> <prompt>`: Send prompt to any harness agent (`/claude`, `/codex`, `/pi`, `/hermes`, `/openclaw`, `/omp`, `/dsh`)
- `/agents`: Check health and installation of all harness agents
- `/help`: Command manual
- `/exit` or `/quit`: Exit TUI

## 4. Hypothesis Data Rubric

Every hypothesis retrieved via `finsocnet` adheres to the empirical rubric:
1. **Category:** `holding_period`, `stock_selection`, `execution`, `risk_management`, `edge`.
2. **Direction:** `LONG`, `SHORT`, `BOTH`, or `NEUTRAL`.
3. **Falsifiable Statement:** Precise cause-and-effect proposition.
4. **Setup Conditions:** Explicit filters (e.g. `ADR >= 4.0%`, daily breakout, RVOL).
5. **Holding Period:** Intraday same-day close vs overnight swing.
6. **Empirical Evidence:** Reported win rate or edge differential.
7. **Verbatim Quote:** Timestamped transcript excerpt (`[MM:SS]`).
