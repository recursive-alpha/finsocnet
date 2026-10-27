---
name: user-skill-synthesizer
description: Synthesize standardized Agent Skills (under .agents/skills/) conforming to agentskills.io from user/creator experiences, rules, and hypotheses across platforms (YouTube, TikTok, Facebook, X, etc.). Use to package any expert or creator strategy into a modular agent skill.
license: MIT
metadata:
  version: "2.0.0"
  author: "finsocnet"
---

# User Skill Synthesizer

Transforms raw mined hypotheses, execution rules, and trading frameworks into production-ready, standardized Agent Skills compliant with the [agentskills.io](https://agentskills.io) specification for users and creators across **YouTube, TikTok, Facebook, X, podcasts, and web**.

## Output Structure
Synthesized skills are placed directly into `.agents/skills/<skill-name>/`:

```
.agents/skills/<skill-name>/
├── SKILL.md                 # YAML frontmatter + strategy instructions
├── references/
│   ├── hypotheses.md        # Verbatim quotes, timestamps, statistical claims
│   └── checklists.md        # Pre-market filters & execution checklist
└── scripts/                 # (Optional) Execution & backtest scripts
```

## Usage

### 1. Synthesize a Skill from YouTube Video Content
```bash
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "momentum-trader-strategy" --content-id "zU0i9rBbEkI" --platform youtube
```

### 2. Synthesize from User Handle across Platforms
```bash
# TikTok creator
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "tiktok-swing-strategy" --user-id "@trader_tok" --platform tiktok

# X / Twitter trader
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "x-breakout-strategy" --user-id "@alphatrader" --platform x
```

### 3. Synthesize from Hypotheses JSON
```bash
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "custom-trader-strategy" --json-file data/hypotheses/user_hypotheses.json
```

## Validation & Registration
- Enforces strict lowercase hyphenated naming (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Verifies description limits (1-1024 chars).
- Registers the synthesized skill in the SQLite database (`data/knowledge.db`).
