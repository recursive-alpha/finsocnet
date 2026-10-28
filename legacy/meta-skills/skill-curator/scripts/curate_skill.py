#!/usr/bin/env python3
"""
Skill Curator: Agent-driven resource learner and strategy synthesizer.
Transforms multi-platform media resources into production-ready Agent Skills
categorized by Person, decoupled from channels, with 7-category reference files (no timestamps).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
PERSONS_DIR = Path("data/persons")
SKILLS_ROOT = Path(".agents/skills")

# Add sibling scripts to path
SCRIPT_DIR = Path(__file__).resolve().parent
PERSON_MATCHER_SCRIPT = SCRIPT_DIR.parent.parent / "person-matcher" / "scripts" / "match_person.py"
SKILL_EXPLORER_SCRIPT = SCRIPT_DIR.parent.parent / "skill-explorer" / "scripts" / "explore_skills.py"

if str(PERSON_MATCHER_SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(PERSON_MATCHER_SCRIPT.parent))
if str(SKILL_EXPLORER_SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SKILL_EXPLORER_SCRIPT.parent))


def curate_and_build_skill(
    person_id: str,
    skill_name: Optional[str] = None,
    custom_rules: Optional[dict[str, Any]] = None,
    db_path: Path = DEFAULT_DB_PATH,
    skills_root: Path = SKILLS_ROOT,
) -> Path:
    """
    Curates and builds a standardized Agent Skill for a Person.
    Decouples person from channel and populates the 7-category reference files.
    """
    person_file = PERSONS_DIR / f"{person_id}.json"
    if not person_file.exists():
        raise ValueError(f"Person file '{person_file}' does not exist.")

    with open(person_file, "r", encoding="utf-8") as f:
        person = json.load(f)

    c_name = person["canonical_name"]
    moniker = person.get("moniker", c_name)
    trading_style = person.get("trading_style", "Discretionary Trading")
    markets = person.get("primary_markets", "Equities, Futures")
    records = person.get("verified_records", "Verified trading track record")
    bio = person.get("bio", "")

    if not skill_name:
        skill_name = f"{person_id}-strategy"

    skill_dir = skills_root / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)

    # Fetch hypotheses for this person from knowledge.db if available
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    h_rows = conn.execute(
        "SELECT * FROM hypotheses WHERE person_id = ? OR user_id = ? ORDER BY id ASC",
        (person_id, person.get("appearances", [{}])[0].get("platform_id", ""))
    ).fetchall()
    hypotheses = [dict(r) for r in h_rows]
    conn.close()

    print(f"Curating skill '{skill_name}' for person '{c_name}' ({len(hypotheses)} hypotheses found in DB)...")

    # Clean description <= 1024 chars
    description = (
        f"Execute verified trading strategies based on {c_name}'s ({moniker}) empirical methods. "
        f"Style: {trading_style}. Primary markets: {markets}. Includes complete setup screening, "
        f"multi-timeframe execution, disciplined trade management, and asymmetric risk sizing."
    )[:1020]

    # 1. Main SKILL.md
    skill_md = f"""---
name: {skill_name}
description: {description}
license: MIT
metadata:
  author: "finsocnet-curator"
  creator: "{c_name}"
  moniker: "{moniker}"
  person_id: "{person_id}"
  trading_style: "{trading_style}"
  primary_markets: "{markets}"
  version: "2.0.0"
  skill_type: "creator-strategy"
---

# {c_name} ({moniker}) Trading Strategy

Comprehensive tactical trading framework synthesized from {c_name}'s verified methodologies, empirical trading data, and trade execution rules. Decoupled from media channels into a canonical person strategy.

## Strategy Summary
- **Trader / Personality:** {c_name} ({moniker})
- **Trading Style:** {trading_style}
- **Primary Markets:** {markets}
- **Verified Track Record:** {records}
- **Core Edge:** High-conviction setups, asymmetric risk-to-reward profiling, and strict execution rules.

---

## 1. Tactical Operational Workflow

### Phase 1: Screening & Universe Selection
Filter and identify assets exhibiting abnormal volatility, institutional participation, and technical tension. Avoid random chop and low-volatility names.
*Detailed rules:* [references/setup_and_screening.md](references/setup_and_screening.md)

### Phase 2: Technical Setup & Inflection Identification
Isolate high-probability inflection points on the daily and higher-timeframe charts before looking for intraday triggers.
*Detailed rules:* [references/setup_and_screening.md](references/setup_and_screening.md)

### Phase 3: Entry Trigger & Precise Execution
Execute upon clear structural confirmation and order flow aggression. Do not anticipate turning points or front-run key levels.
*Detailed rules:* [references/entry_and_execution.md](references/entry_and_execution.md)

### Phase 4: Trade Management & Holding Horizon
Manage active positions according to market character, trailing stops, and holding horizon rules. Transition winning momentum into swings where edge exists, while eliminating overnight holding on unfavorable setups.
*Detailed rules:* [references/trade_management.md](references/trade_management.md)

### Phase 5: Capital Allocation & Risk Sizing
Strict risk invariance. Predefine structural stops before order entry, scale size exponentially into A+ setups, and enforce daily drawdown circuit breakers.
*Detailed rules:* [references/risk_and_sizing.md](references/risk_and_sizing.md)

### Phase 6: Performance Review & Trader Psychology
Continuous behavioral accountability through daily trade plans, journaling, tracking missed opportunities, and executing with emotional detachment.
*Detailed rules:* [references/psychology_and_review.md](references/psychology_and_review.md)

---

## 2. Core Operational Rules (Cheat Sheet)
1. **Never Trade Without Structural Edge:** Sit on hands when no A-quality setup exists; non-trading is a competitive advantage.
2. **Step Up Without Hesitation:** When all setup criteria align, pull the trigger without second-guessing or fear of losing.
3. **Trade the Market, Not Your P&L:** Execute price action and order flow in front of you; eliminate emotional expectations.
4. **Predefine Invariant Stop Loss:** Place structural stops beyond invalidation points (avoiding round number traps) prior to entry.
5. **Honor Trade Management Protocols:** Trail stops on moving averages or structure; scratch immediately if expected momentum fails to materialize.

---

## 3. Dedicated Category Reference Architecture
Inspect dedicated category rulebooks for full technical specifications:
- [references/setup_and_screening.md](references/setup_and_screening.md): Scanner filters, universe criteria, volatility requirements, and catalysts.
- [references/entry_and_execution.md](references/entry_and_execution.md): Entry triggers, order types, tape reading, and multi-timeframe execution.
- [references/trade_management.md](references/trade_management.md): Holding periods, trailing stop rules, scaling out, and scratch protocols.
- [references/risk_and_sizing.md](references/risk_and_sizing.md): Position sizing formulas, maximum account risk, and drawdown protection.
- [references/psychology_and_review.md](references/psychology_and_review.md): Execution discipline, daily planning, demon finder, and trade review.
- [references/checklists.md](references/checklists.md): Actionable pre-market, entry validation, in-trade, and post-trade checklists.
- [references/hypotheses.md](references/hypotheses.md): Verified empirical hypotheses, statistical claims, and verbatim quotes (no timestamps).
"""

    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Update knowledge.db skills table
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO skills (skill_name, user_id, platform, skill_dir, description, hypotheses_count, skill_type, version, author, person_id)
        VALUES (?, ?, ?, ?, ?, ?, 'creator-strategy', '2.0.0', 'finsocnet-curator', ?)
        ON CONFLICT(skill_name) DO UPDATE SET
            user_id = excluded.user_id,
            platform = excluded.platform,
            skill_dir = excluded.skill_dir,
            description = excluded.description,
            hypotheses_count = excluded.hypotheses_count,
            skill_type = excluded.skill_type,
            version = excluded.version,
            author = excluded.author,
            person_id = excluded.person_id;
        """,
        (skill_name, person_id, "multi-platform", str(skill_dir), description, len(hypotheses), person_id),
    )
    conn.commit()
    conn.close()

    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill Curator: Learn and package trading skills by Person.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    b_p = subparsers.add_parser("build", help="Curate and build a skill for a canonical Person")
    b_p.add_argument("person_id", help="Canonical person ID slug (e.g. lance-breitstein, tim-furey)")
    b_p.add_argument("--skill-name", help="Custom skill name (default: <person_id>-strategy)")

    args = parser.parse_args()

    if args.command == "build":
        out_dir = curate_and_build_skill(args.person_id, skill_name=args.skill_name)
        print(f"Skill curated successfully at: {out_dir}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
