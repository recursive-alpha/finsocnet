---
name: hypothesis-miner
description: Mine empirical trading hypotheses, setups, holding periods, and edge rules from creator video transcripts, audio transcriptions, and social posts. Use when analyzing trader content or extracting quantitative rules.
license: MIT
metadata:
  version: "2.0.0"
  author: "finsocnet"
---

# Hypothesis Miner

Extract structured, testable trading hypotheses from creator video transcripts, audio transcriptions, and cross-platform posts. Grounds every rule in verbatim quotes and precise timing markers.

## Hypothesis Anatomy
Every extracted hypothesis captures:
- **Title & Category:** (`holding_period`, `stock_selection`, `edge`, `risk_management`, `execution`).
- **Market Direction & Instrument:** (`LONG`, `SHORT`, `BOTH`, `NEUTRAL`; `equities`, `crypto`, `futures`).
- **Falsifiable Statement:** The exact predictive or behavioral thesis.
- **Setup Conditions:** Filters, indicators, ADR requirements, sector momentum.
- **Holding Period:** Intraday same-day close vs overnight / multi-day swing.
- **Statistical / Empirical Evidence:** Win rates, ratio comparisons, or backtest claims.
- **Invalidation & Risk Rule:** What invalidates the trade or causes edge decay.
- **Verbatim Quote & Timestamp:** Exact excerpt with second-level timing.

## Usage

### 1. Scan Content for Signal Passages
Scan keywords (e.g., "overnight", "short", "ADR", "win rate", "size") to locate key sections:

```bash
uv run .agents/skills/hypothesis-miner/scripts/extract_hypotheses.py data/transcripts/<content_id>.json --scan-only
```

### 2. Extract Structured Hypotheses to JSON
Extract verified hypotheses:

```bash
uv run .agents/skills/hypothesis-miner/scripts/extract_hypotheses.py data/transcripts/<content_id>.json -o data/hypotheses/<content_id>_hypotheses.json
```

### 3. Extract & Ingest Directly into Database & Vector Store
Extract and immediately insert into `knowledge.db` and Chroma vector store:

```bash
uv run .agents/skills/hypothesis-miner/scripts/extract_hypotheses.py data/transcripts/<content_id>.json --ingest-db --platform youtube
```

## References
Consult [references/hypothesis_framework.md](references/hypothesis_framework.md) for field definitions, scoring guidelines, and edge extraction patterns.
