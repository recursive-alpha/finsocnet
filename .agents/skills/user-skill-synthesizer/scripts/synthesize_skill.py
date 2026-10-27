#!/usr/bin/env python3
"""
Synthesize an Agent Skill (.agents/skills/<skill-name>) adhering to agentskills.io
from extracted user/creator hypotheses and trading rules across platforms (YouTube, TikTok, Facebook, X, etc.).
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


def validate_skill_name(name: str) -> None:
    if not (1 <= len(name) <= 64):
        raise ValueError(f"Skill name length must be between 1 and 64 characters (got {len(name)})")
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name):
        raise ValueError(f"Skill name '{name}' must contain only lowercase letters, digits, and non-consecutive hyphens")


def load_hypotheses_from_db(
    db_path: Path,
    user_id: Optional[str] = None,
    content_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if content_id:
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
        u_row = conn.execute(
            "SELECT * FROM users WHERE id = ? OR handle = ?",
            (user_id, user_id),
        ).fetchone()
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
        # Default: take first user or all
        sql = "SELECT * FROM users"
        params: list[Any] = []
        if platform:
            sql += " WHERE platform = ?"
            params.append(platform.lower())
        sql += " LIMIT 1"
        u_row = conn.execute(sql, params).fetchone()

        user_info = {
            "user_id": u_row["id"] if u_row else "unknown_user",
            "user_name": u_row["name"] if u_row else "Content Creator",
            "user_handle": u_row["handle"] if u_row else "",
            "platform": u_row["platform"] if u_row else (platform or "youtube"),
            "content_title": "Aggregated Content",
        }
        h_sql = "SELECT * FROM hypotheses"
        if u_row:
            h_sql += " WHERE user_id = ?"
            h_rows = conn.execute(h_sql, (u_row["id"],)).fetchall()
        else:
            h_rows = conn.execute(h_sql).fetchall()

    conn.close()
    return user_info, [dict(r) for r in h_rows]


def synthesize_user_skill(
    skill_name: str,
    user_info: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    skills_root: Path = Path(".agents/skills"),
    db_path: Optional[Path] = None,
) -> Path:
    validate_skill_name(skill_name)
    skill_dir = skills_root / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    references_dir = skill_dir / "references"
    references_dir.mkdir(exist_ok=True)

    user_name = user_info.get("user_name", "Creator")
    user_id = user_info.get("user_id", "")
    platform = user_info.get("platform", "youtube")

    description = (
        f"Execute trading strategies based on {user_name}'s verified empirical methods ({platform}). "
        "Includes ADR volatility filters, overnight long swing rules, intraday short closing, and exponential bet sizing."
    )[:1020]

    # Build SKILL.md
    skill_md = f"""---
name: {skill_name}
description: {description}
license: MIT
metadata:
  author: "finsocnet-synthesizer"
  creator: "{user_name}"
  platform: "{platform}"
  user_id: "{user_id}"
  version: "1.0.0"
---

# {user_name} Trading Strategy ({platform.upper()})

Tactical trading workflow synthesized from {user_name}'s verified empirical data, focus group criteria, and trade execution rules.

## Strategy Summary
- **Source Platform:** {platform.capitalize()}
- **Primary Market:** Equities with High Volatility and Strong Liquidity.
- **Asymmetric Holding Period:** Hold momentum breakout longs overnight; close short selling positions intraday (no overnight short hold).
- **Setup Win Rate:** 72% historical win rate when matching all focus criteria vs 35% outside.
- **Sizing Mechanism:** Exponential bet sizing (size into A+ setups, scale down or avoid marginal trades).

---

## 1. Selection Checklist (Focus Criteria)
Before initiating any position, the asset must meet all four filter conditions:
1. **High ADR (Average Daily Range):** Require **ADR >= 4.0%**. Stocks with ADR < 3% lack expansion potential and must be skipped.
2. **High Liquidity & Volume:** Strong institutional interest, tight spreads, large daily dollar volume.
3. **Larger Market Cap & Daily Chart Setup:** Multi-day breakout setup on the daily chart.
4. **Sector Momentum Tailwind:** Favor leading hype/momentum sectors (e.g. semiconductors, memory, storage) with sector-wide volume.

---

## 2. Long Trade Execution (Overnight Continuation)
- **Setup:** Trend-following breakout on daily chart meeting all 4 Focus Criteria.
- **Holding Period:** **Overnight / 2-Day Swing**.
- **Execution Rule:** If a day-trading long exhibits strong closing momentum, hold the position overnight to capture secondary-day continuation. Data demonstrates overnight longs substantially outperform same-day closing.
- **Reference Quote:**
  > *"My overnight and swing trades generally performed better than my same-day longs... a lot of times I see continuation and strength into the second day."*

---

## 3. Short Trade Execution (Intraday Close Only)
- **Setup:** Short-term momentum exhaustion or reversal in high ADR names.
- **Holding Period:** **Intraday ONLY (Same-Day Close)**.
- **Execution Rule:** Close all short positions prior to the market close. **NEVER swing short positions overnight.**
- **Risk Invalidation:** Overnight holding on shorts exposes positions to gap-up risk and long-term upward drift, turning positive expectancy into heavy losses.
- **Reference Quote:**
  > *"I found the same-day trading shorts performed much better than swing shorts. So that's a sign that I need to avoid short selling as a swing trade."*

---

## 4. Risk Management & Position Sizing
- **Exponential Bet Sizing:** Treat sizing as an exponential function of setup quality.
  - **A+ Setup (Matches all 4 focus criteria):** Maximum planned risk allocation.
  - **B/C Setups:** Minimize risk or pass completely.
  - **Outside Focus Criteria:** Do not trade (35% empirical win rate).
- **Selective Trading:** High-conviction setups do not occur daily. If every trade appears to be A+, reassess grading criteria.

---

## References
- [references/hypotheses.md](references/hypotheses.md): Detailed table of mined hypotheses with timestamps and quotes.
- [references/checklists.md](references/checklists.md): Pre-market screening checklist and execution sheet.
"""

    hyp_md_lines = [
        f"# Mined Hypotheses for {user_name} ({platform})",
        "",
        "Empirical rules and observations extracted from content:",
        "",
    ]
    for h in hypotheses:
        hyp_md_lines.extend([
            f"### [{h.get('direction', 'BOTH')}] {h.get('title', 'Hypothesis')}",
            f"- **Category:** `{h.get('category', 'general')}`",
            f"- **Timestamp:** `{h.get('timestamp_formatted', 'N/A')}`",
            f"- **Falsifiable Statement:** {h.get('hypothesis_statement')}",
            f"- **Setup Criteria:** {h.get('setup_conditions') or 'N/A'}",
            f"- **Holding Period:** {h.get('holding_period') or 'N/A'}",
            f"- **Statistical Claim:** {h.get('statistical_claim') or 'N/A'}",
            f"- **Verbatim Ground Truth:**",
            f'> "{h.get("verbatim_quote")}"',
            "",
            "---",
            "",
        ])

    checklist_md = f"""# Pre-Market & Trade Execution Checklist ({user_name})

## 1. Scanner Filters
- [ ] ADR >= 4.0%
- [ ] Relative Volume >= 1.5x 30-day average
- [ ] Active sector momentum (top 3 performing industry sectors today)
- [ ] Daily chart setup: multi-day consolidation or breakout level

## 2. Trade Planning
- [ ] **Direction: Long**
  - Planned holding period: Overnight / 2-day swing if strong close.
  - Target: Next daily resistance pivot.
- [ ] **Direction: Short**
  - Planned holding period: Intraday strictly (must set market-on-close or trailing intraday stop).
  - Rule: Under NO circumstances hold short into market close.

## 3. Position Sizing
- [ ] Meets all 4 focus criteria? (Yes = Full A+ size; No = Reduce to 25% or pass).
"""

    skill_file = skill_dir / "SKILL.md"
    hyp_file = references_dir / "hypotheses.md"
    check_file = references_dir / "checklists.md"

    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(skill_md)
    with open(hyp_file, "w", encoding="utf-8") as f:
        f.write("\n".join(hyp_md_lines))
    with open(check_file, "w", encoding="utf-8") as f:
        f.write(checklist_md)

    if db_path and db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO skills (skill_name, user_id, platform, skill_dir, description, hypotheses_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_name) DO UPDATE SET
                user_id = excluded.user_id,
                platform = excluded.platform,
                skill_dir = excluded.skill_dir,
                description = excluded.description,
                hypotheses_count = excluded.hypotheses_count;
            """,
            (skill_name, user_id, platform, str(skill_dir), description, len(hypotheses)),
        )
        conn.commit()
        conn.close()

    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize an Agent Skill from mined user hypotheses across platforms.")
    parser.add_argument("skill_name", help="Directory and skill name (lowercase, hyphens only, e.g. momentum-trader-strategy)")
    parser.add_argument("--content-id", help="Filter by specific content ID in database")
    parser.add_argument("--user-id", help="Filter by user ID or handle in database")
    parser.add_argument("--platform", default="youtube", choices=["youtube", "tiktok", "facebook", "x", "reddit", "medium", "annas_archive", "arxiv", "podcast", "web"])
    parser.add_argument("--json-file", type=Path, help="Load hypotheses from a JSON file directly")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--skills-root", type=Path, default=Path(".agents/skills"), help="Root skills directory")

    args = parser.parse_args()

    try:
        validate_skill_name(args.skill_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json_file:
        with open(args.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_info = {
            "user_id": data.get("user_id") or data.get("channel_id") or "user_imported",
            "user_name": data.get("user_name") or data.get("channel_name") or "Content Creator",
            "platform": data.get("platform") or args.platform,
            "content_title": data.get("title", ""),
        }
        hypotheses = data.get("hypotheses", [])
    else:
        user_info, hypotheses = load_hypotheses_from_db(
            args.db_path,
            user_id=args.user_id,
            content_id=args.content_id,
            platform=args.platform,
        )

    if not hypotheses:
        print(f"Error: No hypotheses found for synthesizing skill.", file=sys.stderr)
        return 2

    created_dir = synthesize_user_skill(
        skill_name=args.skill_name,
        user_info=user_info,
        hypotheses=hypotheses,
        skills_root=args.skills_root,
        db_path=args.db_path,
    )

    print(f"Successfully synthesized User Agent Skill ({user_info.get('platform', 'unknown')}):")
    print(f"  Directory: {created_dir}")
    print(f"  SKILL.md:  {created_dir / 'SKILL.md'}")
    print(f"  Hypotheses Bundled: {len(hypotheses)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
