---
name: skill-explorer
description: Explore, vector-search, and discover synthesized trading skills stored in Chroma vector DB. Matches trading queries, execution styles, and risk parameters to agent skills.
license: MIT
metadata:
  author: "finsocnet"
  version: "1.0.0"
---

# Skill Explorer (Vector DB for Agent Skills)

Semantic exploration and discovery engine for synthesized trading skills stored in the Chroma vector database (`data/chroma_db`). Allows agents and users to search the strategy library by trading concepts, holding periods, market regimes, or execution styles.

## Capabilities
1. **Semantic Vector Search:** Finds trading skills matching natural language descriptions (e.g. "breakout longs held overnight on high ADR equities" or "liquidity sweep false breakout").
2. **Skill Library Indexing:** Extracts frontmatter and category references across all `.agents/skills/` to build persistent embeddings in Chroma.
3. **Multi-Agent Discovery:** Enables harness agents (Claude, Codex, Hermes, Pi, OMP) to discover which person skill is best equipped for current market conditions.

## CLI Usage

### 1. Re-index All Skills into Vector Store
```bash
uv run .agents/skills/skill-explorer/scripts/explore_skills.py reindex
```

### 2. Search Skills by Trading Style
```bash
uv run .agents/skills/skill-explorer/scripts/explore_skills.py search "trailing stop 10 EMA swing"
uv run .agents/skills/skill-explorer/scripts/explore_skills.py search "support resistance liquidity sweep"
```
