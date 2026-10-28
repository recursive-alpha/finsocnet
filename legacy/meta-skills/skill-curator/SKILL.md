---
name: skill-curator
description: Learn, curate, and package expert trading skills from multi-platform resources (video transcripts, podcast audio, X threads, Reddit discussions, and books) into standardized Agent Skills categorized by Person.
license: MIT
metadata:
  author: "finsocnet"
  version: "1.0.0"
---

# Skill Curator (Resource Learner & Skill Synthesizer)

A meta-skill that allows AI agents (Claude, Codex, Hermes, Pi, OMP) to learn trading skills directly from multi-platform resources and synthesize production-ready Agent Skills conforming to [agentskills.io](https://agentskills.io).

## Core Principles
1. **Categorized by Person, Not Channel:** Attributes trading edge and rules to the human expert (e.g. Lance Breitstein, Tim Furey, Shay, Kristjan Qullamaggie), tracking appearances across multiple channels.
2. **Timestamp-Free Actionable Knowledge:** Strips raw video timestamps from skill instructions and reference documents, keeping clean operational trading rules and verbatim quotes.
3. **7-Category Modular Architecture:** Every synthesized person skill is partitioned into 7 dedicated reference category files:
   - `setup_and_screening.md`
   - `entry_and_execution.md`
   - `trade_management.md`
   - `risk_and_sizing.md`
   - `psychology_and_review.md`
   - `checklists.md`
   - `hypotheses.md` (Ground truth citations without timestamps)
4. **Vector Store Auto-Indexing:** Automatically registers and embeds synthesized skills into the Chroma vector database (`skill-explorer`) for semantic capability matching.

## CLI Usage

### Curate & Build a Skill from Person Resources
```bash
uv run .agents/skills/skill-curator/scripts/curate_skill.py build "lance-breitstein" --skill-name "lance-breitstein-levels"
```
