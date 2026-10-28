#!/usr/bin/env python3
"""
Synthesize an Agent Skill (.agents/skills/<skill-name>) adhering to agentskills.io
from extracted Person hypotheses and trading rules across platforms (YouTube, X, Reddit, Medium, etc.).
Generates 7 dedicated category reference files and removes raw timestamps from skill instructions.
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


def validate_skill_name(name: str) -> None:
    if not (1 <= len(name) <= 64):
        raise ValueError(f"Skill name length must be between 1 and 64 characters (got {len(name)})")
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name):
        raise ValueError(f"Skill name '{name}' must contain only lowercase letters, digits, and non-consecutive hyphens")


def load_hypotheses_from_db(
    db_path: Path,
    person_id: Optional[str] = None,
    user_id: Optional[str] = None,
    content_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if person_id:
        p_row = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
        if p_row:
            user_info = {
                "person_id": p_row["id"],
                "user_id": p_row["id"],
                "user_name": p_row["canonical_name"],
                "moniker": p_row["moniker"],
                "trading_style": p_row["trading_style"],
                "primary_markets": p_row["primary_markets"],
                "verified_records": p_row["verified_records"],
                "bio": p_row["bio"],
                "platform": "multi-platform",
            }
        else:
            user_info = {
                "person_id": person_id,
                "user_id": person_id,
                "user_name": person_id.replace("-", " ").title(),
                "moniker": person_id.replace("-", " ").title(),
                "platform": platform or "multi-platform",
            }
        h_rows = conn.execute(
            "SELECT * FROM hypotheses WHERE person_id = ? OR user_id = ? ORDER BY id ASC",
            (person_id, person_id)
        ).fetchall()

    elif content_id:
        c_row = conn.execute(
            """
            SELECT c.*, u.name as user_name, u.handle as user_handle, u.platform as user_platform
            FROM contents c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
            """,
            (content_id,),
        ).fetchone()
        if not c_row:
            raise ValueError(f"Content '{content_id}' not found in database.")
        user_info = {
            "user_id": c_row["user_id"],
            "user_name": c_row["user_name"],
            "user_handle": c_row["user_handle"],
            "platform": c_row["user_platform"],
            "content_title": c_row["title"],
        }
        h_rows = conn.execute("SELECT * FROM hypotheses WHERE content_id = ? ORDER BY id ASC", (content_id,)).fetchall()

    elif user_id:
        u_row = conn.execute("SELECT * FROM users WHERE id = ? OR handle = ?", (user_id, user_id)).fetchone()
        if not u_row:
            raise ValueError(f"User '{user_id}' not found in database.")
        user_info = {
            "user_id": u_row["id"],
            "user_name": u_row["name"],
            "user_handle": u_row["handle"],
            "platform": u_row["platform"],
            "content_title": f"Content from {u_row['name']}",
        }
        h_rows = conn.execute("SELECT * FROM hypotheses WHERE user_id = ? ORDER BY id ASC", (u_row["id"],)).fetchall()

    else:
        u_row = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
        user_info = {
            "user_id": u_row["id"] if u_row else "unknown_user",
            "user_name": u_row["name"] if u_row else "Content Creator",
            "user_handle": u_row["handle"] if u_row else "",
            "platform": u_row["platform"] if u_row else (platform or "youtube"),
            "content_title": "Aggregated Content",
        }
        h_rows = conn.execute("SELECT * FROM hypotheses").fetchall()

    conn.close()
    return user_info, [dict(r) for r in h_rows]


def synthesize_user_skill(
    skill_name: str,
    user_info: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    skills_root: Path = Path(".agents/skills"),
    db_path: Optional[Path] = None,
    category_docs: Optional[dict[str, str]] = None,
) -> Path:
    validate_skill_name(skill_name)
    skill_dir = skills_root / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    references_dir = skill_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)

    user_name = user_info.get("user_name", "Creator")
    moniker = user_info.get("moniker", user_name)
    person_id = user_info.get("person_id") or user_info.get("user_id", "")
    trading_style = user_info.get("trading_style", "Momentum & Discretionary Trading")
    markets = user_info.get("primary_markets", "Equities, Futures, FX")
    platform = user_info.get("platform", "multi-platform")

    description = (
        f"Execute verified trading strategies based on {user_name}'s ({moniker}) empirical methods. "
        f"Style: {trading_style}. Primary markets: {markets}. Includes complete setup screening, "
        f"multi-timeframe execution, disciplined trade management, and asymmetric risk sizing."
    )[:1020]

    # Partition hypotheses by category
    by_cat: dict[str, list[dict[str, Any]]] = {
        "stock_selection": [],
        "execution": [],
        "holding_period": [],
        "risk_management": [],
        "edge": [],
    }
    for h in hypotheses:
        cat = h.get("category", "edge")
        if cat in by_cat:
            by_cat[cat].append(h)
        else:
            by_cat.setdefault("edge", []).append(h)

    # Build SKILL.md
    skill_md = f"""---
name: {skill_name}
description: {description}
license: MIT
metadata:
  author: "finsocnet-curator"
  creator: "{user_name}"
  moniker: "{moniker}"
  person_id: "{person_id}"
  trading_style: "{trading_style}"
  primary_markets: "{markets}"
  version: "2.0.0"
  skill_type: "creator-strategy"
---

# {user_name} ({moniker}) Trading Strategy

Comprehensive tactical trading framework synthesized from {user_name}'s verified methodologies, empirical trading data, and trade execution rules. Decoupled from media channels into a canonical person strategy.

## Strategy Summary
- **Trader / Personality:** {user_name} ({moniker})
- **Trading Style:** {trading_style}
- **Primary Markets:** {markets}
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

    # Build clean hypotheses.md (WITHOUT timestamps)
    hyp_md_lines = [
        f"# Verified Empirical Hypotheses & Rulebook: {user_name} ({moniker})",
        "",
        "Grounded trading hypotheses and execution principles extracted from source material:",
        "",
    ]
    for h in hypotheses:
        hyp_md_lines.extend([
            f"### [{h.get('direction', 'BOTH')}] {h.get('title', 'Hypothesis')}",
            f"- **Category:** `{h.get('category', 'general')}`",
            f"- **Instrument:** `{h.get('instrument', 'equities')}`",
            f"- **Falsifiable Statement:** {h.get('hypothesis_statement')}",
            f"- **Setup Criteria:** {h.get('setup_conditions') or 'N/A'}",
            f"- **Holding Period:** {h.get('holding_period') or 'N/A'}",
            f"- **Statistical Evidence:** {h.get('statistical_claim') or 'N/A'}",
            f"- **Invalidation Risk:** {h.get('invalidation_risk') or 'N/A'}",
            f"- **Verbatim Ground Truth:**",
            f'> "{h.get("verbatim_quote")}"',
            "",
            "---",
            "",
        ])

    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    (references_dir / "hypotheses.md").write_text("\n".join(hyp_md_lines), encoding="utf-8")

    # If category_docs provided, write them; otherwise generate clean templates
    docs = category_docs or {}

    setup_content = docs.get("setup_and_screening.md") or f"""# Setup & Screening Rules: {user_name}

## 1. Market Selection & Universe Filters
- Focus exclusively on assets matching core volatility and liquidity thresholds.
- Prioritize leading momentum sectors and in-play products.

## 2. Technical Scanner Criteria
- Daily chart structure alignment: multi-week/month consolidation or clean inflection level.
- Relative volume surge confirming institutional order flow.
"""
    (references_dir / "setup_and_screening.md").write_text(setup_content, encoding="utf-8")

    entry_content = docs.get("entry_and_execution.md") or f"""# Entry & Execution Rules: {user_name}

## 1. Entry Triggers
- Confirm structural breakout or inflection before entering.
- Order type: Stop-limit or market order on confirmed break.

## 2. Order Flow & Tape Reading
- Look for aggressive lifting of offers and shallow pullbacks on declining volume.
"""
    (references_dir / "entry_and_execution.md").write_text(entry_content, encoding="utf-8")

    mgmt_content = docs.get("trade_management.md") or f"""# Trade Management & Holding Periods: {user_name}

## 1. Holding Period Horizon
- Align trade horizon strictly with setup edge (intraday only vs overnight swing).

## 2. Trailing Stops & Scaling
- Trail stop along key moving averages or structural swing levels.
- Take partial profits into initial strength.
"""
    (references_dir / "trade_management.md").write_text(mgmt_content, encoding="utf-8")

    risk_content = docs.get("risk_and_sizing.md") or f"""# Risk Management & Position Sizing: {user_name}

## 1. Position Sizing Model
- Size into high-conviction A+ setups exponentially.
- Keep fixed risk on initial capital.

## 2. Invalidation & Circuit Breakers
- Structural stop loss placed beyond key level prior to entry.
- Enforce daily max loss limits.
"""
    (references_dir / "risk_and_sizing.md").write_text(risk_content, encoding="utf-8")

    psych_content = docs.get("psychology_and_review.md") or f"""# Trader Psychology & Performance Review: {user_name}

## 1. Execution Discipline
- Sit on your hands when no edge is present.
- Step up without hesitation when the plan triggers.

## 2. Daily & Weekly Review
- Daily trade plan and journaling.
- Track missed opportunities and eliminate recency bias.
"""
    (references_dir / "psychology_and_review.md").write_text(psych_content, encoding="utf-8")

    check_content = docs.get("checklists.md") or f"""# Pre-Market & Trade Execution Checklist ({user_name})

## 1. Pre-Market Scanner
- [ ] Asset meets volatility and liquidity requirements
- [ ] Sector or market tailwind aligns with trade direction
- [ ] Daily chart setup shows clean technical level

## 2. Execution Validation
- [ ] Risk defined prior to order placement
- [ ] Entry trigger confirmed on intraday timeframe
- [ ] Invalidation point and initial stop loss set

## 3. Trade Management
- [ ] Follow predefined holding horizon rules
- [ ] Scratch immediately if momentum dies
- [ ] Journal trade execution against process
"""
    (references_dir / "checklists.md").write_text(check_content, encoding="utf-8")

    if db_path and db_path.exists():
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
            (skill_name, person_id, platform, str(skill_dir), description, len(hypotheses), person_id),
        )
        conn.commit()
        conn.close()

    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize an Agent Skill from mined user hypotheses across platforms.")
    parser.add_argument("skill_name", help="Directory and skill name (lowercase, hyphens only, e.g. momentum-trader-strategy)")
    parser.add_argument("--person-id", help="Filter by canonical person ID in database")
    parser.add_argument("--content-id", help="Filter by specific content ID in database")
    parser.add_argument("--user-id", help="Filter by user ID or handle in database")
    parser.add_argument("--platform", default="multi-platform")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--skills-root", type=Path, default=Path(".agents/skills"), help="Root skills directory")

    args = parser.parse_args()

    try:
        validate_skill_name(args.skill_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    user_info, hypotheses = load_hypotheses_from_db(
        args.db_path,
        person_id=args.person_id,
        user_id=args.user_id,
        content_id=args.content_id,
        platform=args.platform,
    )

    created_dir = synthesize_user_skill(
        skill_name=args.skill_name,
        user_info=user_info,
        hypotheses=hypotheses,
        skills_root=args.skills_root,
        db_path=args.db_path,
    )

    print(f"Successfully synthesized User Agent Skill ({user_info.get('user_name', 'unknown')}):")
    print(f"  Directory: {created_dir}")
    print(f"  SKILL.md:  {created_dir / 'SKILL.md'}")
    print(f"  Hypotheses Bundled: {len(hypotheses)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
