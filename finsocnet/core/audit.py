"""`kb audit`: read-only measurement of how complete and how trustworthy the database is.

An agent's own report is not evidence; this is. Provenance means a content was fetched by a platform skill
(`fetch_method` set, usually a stored raw record); text an agent wrote itself has neither."""

from __future__ import annotations

import sqlite3
from typing import Any

PROFILE_FIELDS = ("bio", "moniker", "profession", "affiliation", "domains", "homepage", "relevance")


def _n(conn: sqlite3.Connection, sql: str, *a: Any) -> int:
    return conn.execute(sql, a).fetchone()[0]


def run(conn: sqlite3.Connection, limit: int = 15) -> dict[str, Any]:
    out: dict[str, Any] = {}
    unsourced = [r[0] for r in conn.execute(
        "SELECT k.id FROM knowledge_cards k WHERE k.status = 'active' AND NOT EXISTS ("
        " SELECT 1 FROM card_citations cc JOIN contents c ON c.id = cc.content_id WHERE cc.card_id = k.id AND c.fetch_method IS NOT NULL)")]
    out["cards"] = {"active": _n(conn, "SELECT COUNT(*) FROM knowledge_cards WHERE status = 'active'"),
                    "retired": _n(conn, "SELECT COUNT(*) FROM knowledge_cards WHERE status = 'retired'"),
                    "unsourced_active": len(unsourced), "unsourced_ids": unsourced[:limit],
                    "without_person": _n(conn, "SELECT COUNT(*) FROM knowledge_cards k WHERE k.status = 'active' AND NOT EXISTS (SELECT 1 FROM card_citations WHERE card_id = k.id AND person_id IS NOT NULL)")}
    out["contents"] = {
        "total": _n(conn, "SELECT COUNT(*) FROM contents"),
        "fetched_with_text": _n(conn, "SELECT COUNT(*) FROM contents WHERE fetch_method IS NOT NULL AND process_status != 'metadata_only'"),
        "metadata_only": _n(conn, "SELECT COUNT(*) FROM contents WHERE process_status = 'metadata_only'"),
        "without_provenance": _n(conn, "SELECT COUNT(*) FROM contents WHERE fetch_method IS NULL AND process_status != 'metadata_only'"),
        "mined_processed": _n(conn, "SELECT COUNT(*) FROM contents WHERE process_status = 'processed'"),
        "fetched_not_mined": _n(conn, "SELECT COUNT(*) FROM contents WHERE fetch_method IS NOT NULL AND process_status IN ('new','processing')"),
        "by_platform": {r[0]: {"total": r[1], "fetched": r[2], "processed": r[3]} for r in conn.execute(
            "SELECT platform, COUNT(*), SUM(fetch_method IS NOT NULL AND process_status != 'metadata_only'), SUM(process_status = 'processed') FROM contents GROUP BY 1 ORDER BY 2 DESC")},
    }
    missing = {f: _n(conn, f"SELECT COUNT(*) FROM persons WHERE status = 'active' AND ({f} IS NULL OR TRIM({f}) = '')") for f in PROFILE_FIELDS}
    missing["avatar"] = _n(conn, "SELECT COUNT(*) FROM persons WHERE status = 'active' AND avatar_path IS NULL")
    out["persons"] = {
        "active": _n(conn, "SELECT COUNT(*) FROM persons WHERE status = 'active'"),
        "missing_field": missing,
        "without_confirmed_link": _n(conn, "SELECT COUNT(*) FROM persons p WHERE p.status = 'active' AND NOT EXISTS (SELECT 1 FROM person_links WHERE person_id = p.id AND match_status = 'confirmed')"),
        "without_source": _n(conn, "SELECT COUNT(*) FROM persons p WHERE p.status = 'active' AND NOT EXISTS (SELECT 1 FROM sources WHERE person_id = p.id)"),
        "without_active_card": _n(conn, "SELECT COUNT(*) FROM persons p WHERE p.status = 'active' AND NOT EXISTS (SELECT 1 FROM card_citations cc JOIN knowledge_cards k ON k.id = cc.card_id WHERE cc.person_id = p.id AND k.status = 'active')"),
        "without_rulebook": _n(conn, "SELECT COUNT(*) FROM persons p WHERE p.status = 'active' AND NOT EXISTS (SELECT 1 FROM person_skills WHERE person_id = p.id)"),
    }
    out["links"] = {
        "confirmed": _n(conn, "SELECT COUNT(*) FROM person_links WHERE match_status = 'confirmed'"),
        "needs_review": _n(conn, "SELECT COUNT(*) FROM person_links WHERE match_status = 'needs_review'"),
        "rejected": _n(conn, "SELECT COUNT(*) FROM person_links WHERE match_status = 'rejected'"),
        "confirmed_with_thin_evidence": _n(conn, "SELECT COUNT(*) FROM person_links WHERE match_status = 'confirmed' AND (LENGTH(COALESCE(evidence, '')) < 30 OR evidence LIKE 'Official homepage%' OR evidence LIKE 'Wikipedia biography%')"),
    }
    out["sources"] = {"total": _n(conn, "SELECT COUNT(*) FROM sources"),
                      "without_person": _n(conn, "SELECT COUNT(*) FROM sources WHERE person_id IS NULL"),
                      "by_platform": {r[0]: r[1] for r in conn.execute("SELECT platform, COUNT(*) FROM sources GROUP BY 1 ORDER BY 2 DESC")}}
    out["queue"] = {r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM explore_queue GROUP BY 1")}
    out["backlog"] = [dict(r) for r in conn.execute(
        "SELECT p.id, p.canonical_name, "
        " (SELECT COUNT(*) FROM sources s WHERE s.person_id = p.id) AS sources, "
        " (SELECT COUNT(*) FROM contents c JOIN sources s ON s.id = c.source_id WHERE s.person_id = p.id) AS listed, "
        " (SELECT COUNT(*) FROM contents c JOIN sources s ON s.id = c.source_id WHERE s.person_id = p.id AND c.fetch_method IS NOT NULL AND c.process_status != 'metadata_only') AS fetched, "
        " (SELECT COUNT(DISTINCT cc.card_id) FROM card_citations cc JOIN knowledge_cards k ON k.id = cc.card_id WHERE cc.person_id = p.id AND k.status = 'active') AS cards, "
        " (SELECT COUNT(*) FROM person_links l WHERE l.person_id = p.id AND l.match_status = 'confirmed') AS links "
        "FROM persons p WHERE p.status = 'active' ORDER BY cards ASC, fetched ASC, listed DESC LIMIT ?", (limit,))]
    todo = []
    if out["cards"]["unsourced_active"]:
        todo.append(f"{out['cards']['unsourced_active']} active cards cite no fetched content: retire them or re-mine from the real source")
    if out["contents"]["without_provenance"]:
        todo.append(f"{out['contents']['without_provenance']} contents have text but no fetch_method: re-fetch them with the platform skill")
    if out["links"]["confirmed_with_thin_evidence"]:
        todo.append(f"{out['links']['confirmed_with_thin_evidence']} confirmed links have thin evidence: open each page and write what you saw")
    if out["links"]["needs_review"]:
        todo.append(f"{out['links']['needs_review']} links wait for review: open them (person-profiler)")
    if out["persons"]["without_active_card"]:
        todo.append(f"{out['persons']['without_active_card']} people have no active card: fetch and mine their best content")
    if out["contents"]["fetched_not_mined"]:
        todo.append(f"{out['contents']['fetched_not_mined']} fetched contents are not mined yet (market-idea-miner)")
    if out["sources"]["without_person"]:
        todo.append(f"{out['sources']['without_person']} sources have no person: person-explorer / person-matcher")
    out["todo"] = todo
    return out
