"""
Database connection, querying, and ORM-lite helpers for FinSocNet.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))


def get_db(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return an active connection to knowledge.db with auto-migrations applied."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")

    # v1 helper kept until Phase 8: migrations are explicit now (`finsocnet kb migrate`), never run implicitly.
    return conn


def get_stats(conn: Optional[sqlite3.Connection] = None) -> dict[str, Any]:
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    u_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c_count = conn.execute("SELECT COUNT(*) FROM contents").fetchone()[0]
    h_count = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
    s_count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]

    platforms = conn.execute("SELECT platform, COUNT(DISTINCT id) as c FROM contents GROUP BY platform").fetchall()
    categories = conn.execute("SELECT category, COUNT(DISTINCT id) as c FROM hypotheses GROUP BY category").fetchall()
    directions = conn.execute("SELECT direction, COUNT(DISTINCT id) as c FROM hypotheses GROUP BY direction").fetchall()

    res = {
        "users": u_count,
        "contents": c_count,
        "hypotheses": h_count,
        "skills": s_count,
        "platforms": {r["platform"]: r["c"] for r in platforms},
        "categories": {r["category"]: r["c"] for r in categories},
        "directions": {r["direction"]: r["c"] for r in directions},
    }
    if close_after:
        conn.close()
    return res


def get_hypothesis(hyp_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    sql = """
        SELECT h.*, u.name as user_name, u.handle as user_handle, u.platform as user_platform,
               c.title as content_title, c.url as content_url, c.content_type
        FROM hypotheses h
        JOIN users u ON h.user_id = u.id
        JOIN contents c ON h.content_id = c.id
        WHERE h.id = ?
    """
    row = conn.execute(sql, (hyp_id,)).fetchone()
    res = dict(row) if row else None
    if close_after:
        conn.close()
    return res


def list_hypotheses(
    query: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> list[dict[str, Any]]:
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    sql = """
        SELECT h.*, u.name as user_name, u.handle as user_handle, u.platform as user_platform,
               c.title as content_title, c.url as content_url
        FROM hypotheses h
        JOIN users u ON h.user_id = u.id
        JOIN contents c ON h.content_id = c.id
        WHERE 1=1
    """
    params: list[Any] = []
    if category:
        sql += " AND h.category = ?"
        params.append(category)
    if direction:
        sql += " AND h.direction = ?"
        params.append(direction.upper())
    if platform:
        sql += " AND u.platform = ?"
        params.append(platform.lower())
    if query:
        sql += " AND (h.title LIKE ? OR h.hypothesis_statement LIKE ? OR h.setup_conditions LIKE ? OR h.verbatim_quote LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term, term])

    sql += " ORDER BY h.id ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    res = [dict(r) for r in rows]
    if close_after:
        conn.close()
    return res


def list_creators(platform: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    sql = """
        SELECT u.id, u.name, u.handle, u.platform, u.topics,
               COUNT(DISTINCT c.id) as content_count,
               COUNT(DISTINCT h.id) as hypothesis_count
        FROM users u
        LEFT JOIN contents c ON u.id = c.user_id
        LEFT JOIN hypotheses h ON u.id = h.user_id
        WHERE 1=1
    """
    params: list[Any] = []
    if platform:
        sql += " AND u.platform = ?"
        params.append(platform.lower())

    sql += " GROUP BY u.id ORDER BY content_count DESC, hypothesis_count DESC"
    rows = conn.execute(sql, params).fetchall()
    res = [dict(r) for r in rows]
    if close_after:
        conn.close()
    return res


def list_contents(platform: Optional[str] = None, content_type: Optional[str] = None, limit: int = 50, conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    sql = """
        SELECT c.*, u.name as user_name, u.handle as user_handle
        FROM contents c
        JOIN users u ON c.user_id = u.id
        WHERE 1=1
    """
    params: list[Any] = []
    if platform:
        sql += " AND c.platform = ?"
        params.append(platform.lower())
    if content_type:
        sql += " AND c.content_type = ?"
        params.append(content_type.lower())

    sql += " ORDER BY c.view_count DESC, c.id ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    res = [dict(r) for r in rows]
    if close_after:
        conn.close()
    return res
