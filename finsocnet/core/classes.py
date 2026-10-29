"""The static classification of people (specs/16): a fixed list of classes, grouped, with `other` as the catch-all.

One source of truth: the schema enum (`person.schema.json`), the DB CHECK (migration 006), the web filters and the agent skills
use exactly this list. A person that fits nothing is `other` (and the agent says why in `relevance`); the list is not extended per person."""

from __future__ import annotations

import sqlite3
from typing import Any

CLASSES: list[dict[str, str]] = [
    {"id": "trader", "group": "Traders & investors", "label": "Trader", "hint": "trades own or prop capital, publishes how"},
    {"id": "investor", "group": "Traders & investors", "label": "Investor", "hint": "long-term or value investor, fund-letter author"},
    {"id": "portfolio_manager", "group": "Managers & analysts", "label": "Portfolio manager", "hint": "runs a fund or book"},
    {"id": "analyst", "group": "Managers & analysts", "label": "Analyst", "hint": "sell-side, buy-side or independent research"},
    {"id": "strategist", "group": "Managers & analysts", "label": "Strategist", "hint": "macro, asset-allocation or market strategist"},
    {"id": "executive", "group": "Business leaders", "label": "Executive", "hint": "CEO, CFO, CIO of a financial firm or exchange"},
    {"id": "founder", "group": "Business leaders", "label": "Founder", "hint": "founded a firm, fund, platform or school"},
    {"id": "economist", "group": "Policy & economics", "label": "Economist", "hint": "professional economist outside a university"},
    {"id": "central_banker", "group": "Policy & economics", "label": "Central banker", "hint": "central bank governor or board member"},
    {"id": "regulator", "group": "Policy & economics", "label": "Regulator", "hint": "securities, banking or competition regulator"},
    {"id": "academic", "group": "Academia", "label": "Academic", "hint": "professor or lecturer in finance or economics"},
    {"id": "researcher", "group": "Academia", "label": "Researcher", "hint": "quant or institute researcher publishing papers"},
    {"id": "author", "group": "Media & education", "label": "Author", "hint": "books about markets or economics"},
    {"id": "journalist", "group": "Media & education", "label": "Journalist", "hint": "columnist or reporter on markets"},
    {"id": "educator", "group": "Media & education", "label": "Educator", "hint": "courses, community or channel mainly for teaching"},
    {"id": "other", "group": "Other", "label": "Other", "hint": "in scope by what they publish, none of the above fits"},
]
IDS = [c["id"] for c in CLASSES]
DEFAULT = "other"


def normalize(value: str | None) -> str:
    """Anything missing or unknown is `other`."""
    return value if value in IDS else DEFAULT


def with_counts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    counts = {r[0]: r[1] for r in conn.execute("SELECT COALESCE(profession, 'other'), COUNT(*) FROM persons WHERE status = 'active' GROUP BY 1")}
    unknown = sum(n for k, n in counts.items() if k not in IDS)
    return [{**c, "count": counts.get(c["id"], 0) + (unknown if c["id"] == DEFAULT else 0)} for c in CLASSES]
