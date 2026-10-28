#!/usr/bin/env python3
"""
Rebuild all 9 Person Strategy Skills from Source Ground Truth.
Generates full 7-category reference architecture, strips timestamps,
and synchronizes knowledge.db persons, hypotheses, and skills.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()
DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
SKILLS_ROOT = Path(".agents/skills")
PERSONS_DIR = Path("data/persons")

# Import synthesizer function
sys.path.insert(0, str((SKILLS_ROOT / "user-skill-synthesizer" / "scripts").resolve()))
from synthesize_skill import synthesize_user_skill

conn = sqlite3.connect(DEFAULT_DB_PATH)
c = conn.cursor()

# Ensure person_id columns exist
cols = [r[1] for r in c.execute("PRAGMA table_info(hypotheses)").fetchall()]
if "person_id" not in cols:
    c.execute("ALTER TABLE hypotheses ADD COLUMN person_id TEXT")
cols = [r[1] for r in c.execute("PRAGMA table_info(skills)").fetchall()]
if "person_id" not in cols:
    c.execute("ALTER TABLE skills ADD COLUMN person_id TEXT")
conn.commit()


def save_and_sync_skill(
    skill_name: str,
    person_id: str,
    hypotheses: list[dict[str, Any]],
    category_docs: dict[str, str],
) -> None:
    with open(PERSONS_DIR / f"{person_id}.json", "r", encoding="utf-8") as f:
        person = json.load(f)

    user_info = {
        "person_id": person["id"],
        "user_id": person["id"],
        "user_name": person["canonical_name"],
        "moniker": person.get("moniker", person["canonical_name"]),
        "trading_style": person.get("trading_style", ""),
        "primary_markets": person.get("primary_markets", ""),
        "verified_records": person.get("verified_records", ""),
        "bio": person.get("bio", ""),
        "platform": "multi-platform",
    }

    # Clean old hypotheses for this person in DB
    c.execute("DELETE FROM hypotheses WHERE person_id = ? OR user_id = ?", (person_id, person_id))
    
    # Insert new hypotheses
    for h in hypotheses:
        c.execute("""
        INSERT INTO hypotheses (
            content_id, user_id, person_id, title, category, direction, instrument,
            hypothesis_statement, setup_conditions, holding_period, statistical_claim,
            invalidation_risk, verbatim_quote
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            h.get("content_id", ""),
            person_id,
            person_id,
            h["title"],
            h.get("category", "edge"),
            h.get("direction", "BOTH"),
            h.get("instrument", "equities"),
            h["hypothesis_statement"],
            h.get("setup_conditions", ""),
            h.get("holding_period", ""),
            h.get("statistical_claim", ""),
            h.get("invalidation_risk", ""),
            h.get("verbatim_quote", "")
        ))

    conn.commit()

    # Synthesize the skill directory
    synthesize_user_skill(
        skill_name=skill_name,
        user_info=user_info,
        hypotheses=hypotheses,
        skills_root=SKILLS_ROOT,
        db_path=DEFAULT_DB_PATH,
        category_docs=category_docs,
    )
    print(f"✓ Rebuilt skill '{skill_name}' for {user_info['user_name']} ({len(hypotheses)} hypotheses)")


print("Starting synthesis of all 9 person strategy skills...")
