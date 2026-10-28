#!/usr/bin/env python3
"""
Deduplicated Market Idea Ingestion Engine for FinSocNet.
Ensures knowledge.db stays strictly unique.
If a similar idea already exists (cosine similarity >= threshold), it appends the
content citation to 'alternative_resources' rather than creating a duplicate row.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()
DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from vector_store import encode_text, search_vector_sqlite, upsert_vector_embedding


def find_similar_idea(
    conn: sqlite3.Connection,
    statement: str,
    threshold: float = 0.75,
    person_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Find if a semantically equivalent idea already exists in knowledge.db.
    Checks vector similarity across the market_ideas collection.
    """
    matches = search_vector_sqlite(
        conn=conn,
        collection="market_ideas",
        query_text=statement,
        limit=3,
        person_id=person_id,
    )
    if matches and matches[0]["score"] >= threshold:
        top_match = matches[0]
        row = conn.execute("SELECT * FROM market_ideas WHERE id = ?", (int(top_match["entity_id"]),)).fetchone()
        if row:
            res = dict(row)
            res["similarity_score"] = top_match["score"]
            return res
    return None


def ingest_market_idea(
    conn: sqlite3.Connection,
    title: str,
    idea_statement: str,
    verbatim_quote: str,
    domain: str = "financial_markets",
    category: str = "market_dynamics",
    direction: str = "BOTH",
    instrument: str = "equities",
    setup_conditions: str = "",
    holding_period: str = "",
    statistical_claim: str = "",
    invalidation_risk: str = "",
    person_id: Optional[str] = None,
    content_id: Optional[str] = None,
    content_title: Optional[str] = None,
    platform: Optional[str] = None,
    similarity_threshold: float = 0.75,
) -> tuple[int, bool]:
    """
    Ingest a financial or stock market idea into knowledge.db.
    Returns (idea_id, is_new).
    If a similar idea exists, appends to alternative_resources.
    """
    query_text = f"{title}: {idea_statement}"
    similar = find_similar_idea(
        conn=conn,
        statement=query_text,
        threshold=similarity_threshold,
        person_id=person_id,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    if similar:
        idea_id = similar["id"]
        alt_res: list[dict[str, Any]] = []
        try:
            alt_res = json.loads(similar.get("alternative_resources") or "[]")
        except Exception:
            alt_res = []

        already_cited = any(a.get("content_id") == content_id for a in alt_res if content_id)
        if not already_cited and content_id:
            alt_res.append({
                "content_id": content_id,
                "content_title": content_title or "",
                "platform": platform or "unknown",
                "verbatim_quote": verbatim_quote,
                "similarity_score": similar["similarity_score"],
                "added_at": now_iso,
            })
            conn.execute(
                """
                UPDATE market_ideas
                SET alternative_resources = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(alt_res, ensure_ascii=False), idea_id),
            )
            conn.commit()

        return idea_id, False

    # Insert new unique record
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO market_ideas (
            person_id, content_id, domain, category, direction, instrument,
            title, idea_statement, setup_conditions, holding_period,
            statistical_claim, invalidation_risk, verbatim_quote, alternative_resources
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]')
        """,
        (
            person_id, content_id, domain, category, direction, instrument,
            title, idea_statement, setup_conditions, holding_period,
            statistical_claim, invalidation_risk, verbatim_quote,
        ),
    )
    new_id = cur.lastrowid
    conn.commit()

    # Index into vector_embeddings table
    upsert_vector_embedding(
        conn=conn,
        collection="market_ideas",
        entity_id=str(new_id),
        document=query_text,
        metadata={
            "domain": domain,
            "category": category,
            "direction": direction,
            "instrument": instrument,
            "person_id": person_id or "",
            "title": title,
        },
        person_id=person_id,
    )

    return new_id, True
