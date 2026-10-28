"""Exploration frontier, knowledge gaps and browsing history (docs/spec/01 §2.7, §6.7; 06 §1)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from finsocnet.core import browser, budgets
from finsocnet.core.db import dumps, loads, transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.normalize import quote_key
from finsocnet.core.output import CliError

TARGET_KINDS = ("url", "handle", "source", "content", "query", "person", "book", "paper")
ACTIONS = ("fetch", "list", "profile", "search", "crawl_source")
ORIGINS = ("user", "mention", "gap", "history", "citation", "person_crosslink", "search_result", "source_refresh", "retry")
STATUSES = ("pending", "in_progress", "done", "failed", "deferred", "skipped")
VERDICTS = ("no_answer", "weak_answer", "conflicting")
GAP_STATUSES = ("open", "exploring", "filled", "wont_fill")


def requires_session(platform: str) -> bool:
    return bool(browser.platforms().get(platform, {}).get("requires_session"))


def add(conn: sqlite3.Connection, item: dict[str, Any], run_id: int) -> dict[str, Any]:
    """Insert a queue item; duplicates (same target, platform, action) are ignored and returned as `existing`."""
    problems = []
    if item.get("target_kind") not in TARGET_KINDS:
        problems.append({"path": "/target_kind", "problem": f"must be one of {', '.join(TARGET_KINDS)}"})
    if item.get("origin") not in ORIGINS:
        problems.append({"path": "/origin", "problem": f"must be one of {', '.join(ORIGINS)}"})
    if item.get("action", "fetch") not in ACTIONS:
        problems.append({"path": "/action", "problem": f"must be one of {', '.join(ACTIONS)}"})
    pr = item.get("priority", 0.5)
    if not isinstance(pr, (int, float)) or not 0 <= pr <= 1:
        problems.append({"path": "/priority", "problem": "must be between 0 and 1"})
    if not item.get("target"):
        problems.append({"path": "/target", "problem": "required"})
    if problems:
        raise CliError("VALIDATION_ERROR", "queue item failed validation", details=problems)
    platform, action = item.get("platform", ""), item.get("action", "fetch")
    with transaction(conn):
        row = conn.execute("SELECT id, status FROM explore_queue WHERE target = ? AND platform = ? AND action = ?", (item["target"], platform, action)).fetchone()
        if row:
            return {"id": row["id"], "status": "existing", "queue_status": row["status"]}
        cur = conn.execute(
            "INSERT INTO explore_queue (target, target_kind, platform, action, origin, origin_ref, reason, priority, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item["target"], item["target_kind"], platform, action, item["origin"], item.get("origin_ref"), item.get("reason"), pr, run_id))
    return {"id": int(cur.lastrowid), "status": "created"}


def next_items(conn: sqlite3.Connection, limit: int = 5, platform: str | None = None) -> list[dict[str, Any]]:
    """Highest priority first. Skips items with `not_before` in the future, platforms with exhausted budgets, and session
    platforms whose `login_state` is not `logged_in`. Returned items are marked `in_progress`."""
    now = utc_now()
    out: list[dict[str, Any]] = []
    with transaction(conn):
        rows = conn.execute("SELECT * FROM explore_queue WHERE status = 'pending' AND (not_before IS NULL OR not_before <= ?) " +
                            ("AND platform = ? " if platform else "") + "ORDER BY priority DESC, id", ([now, platform] if platform else [now])).fetchall()
        blocked: dict[str, bool] = {}
        for r in rows:
            pf = r["platform"]
            if pf and pf not in blocked:
                bad = budgets.exhausted(conn, pf)
                if not bad and requires_session(pf):
                    states = [x[0] for x in conn.execute("SELECT login_state FROM browser_sessions WHERE platform = ?", (pf,))]
                    bad = "logged_in" not in states
                blocked[pf] = bad
            if pf and blocked.get(pf):
                continue
            conn.execute("UPDATE explore_queue SET status = 'in_progress', attempts = attempts + 1, updated_at = ? WHERE id = ?", (now, r["id"]))
            d = dict(r)
            d["status"], d["attempts"] = "in_progress", r["attempts"] + 1
            out.append(d)
            if len(out) >= limit:
                break
    return out


def update(conn: sqlite3.Connection, queue_id: int, status: str, error: str | None = None, retry_after_sec: int | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        raise CliError("USAGE", f"status must be one of {', '.join(STATUSES)}")
    not_before = (datetime.now(timezone.utc) + timedelta(seconds=retry_after_sec)).strftime("%Y-%m-%dT%H:%M:%SZ") if retry_after_sec else None
    with transaction(conn):
        if conn.execute("SELECT 1 FROM explore_queue WHERE id = ?", (queue_id,)).fetchone() is None:
            raise CliError("NOT_FOUND", f"queue item {queue_id} not found")
        # a deferred item goes back to pending when it becomes due
        eff = "pending" if (status == "deferred" and not_before) else status
        conn.execute("UPDATE explore_queue SET status = ?, last_error = ?, not_before = ?, updated_at = ? WHERE id = ?", (eff, error, not_before, utc_now(), queue_id))
    return {"id": queue_id, "status": eff, "not_before": not_before}


def list_items(conn: sqlite3.Connection, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM explore_queue WHERE 1=1", []
    if status:
        sql += " AND status = ?"
        args.append(status)
    return [dict(r) for r in conn.execute(sql + " ORDER BY priority DESC, id LIMIT ?", [*args, limit])]


def release_stuck(conn: sqlite3.Connection, max_age_minutes: int = 120) -> int:
    """Put `in_progress` items that no run is working on any more back to pending."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with transaction(conn):
        return conn.execute("UPDATE explore_queue SET status = 'pending', updated_at = ? WHERE status = 'in_progress' AND updated_at < ?", (utc_now(), cutoff)).rowcount


# --- gaps -------------------------------------------------------------------------------------------------

def gap_add(conn: sqlite3.Connection, query: str, verdict: str, query_card: dict[str, Any] | None, run_id: int) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise CliError("USAGE", f"verdict must be one of {', '.join(VERDICTS)}")
    key = quote_key(query)
    with transaction(conn):
        for r in conn.execute("SELECT id, query, asked_count FROM knowledge_gaps WHERE status IN ('open', 'exploring')"):
            if quote_key(r["query"]) == key:
                conn.execute("UPDATE knowledge_gaps SET asked_count = asked_count + 1, verdict = ?, updated_at = ? WHERE id = ?", (verdict, utc_now(), r["id"]))
                return {"id": r["id"], "status": "existing", "asked_count": r["asked_count"] + 1}
        cur = conn.execute("INSERT INTO knowledge_gaps (query, query_card_json, verdict, run_id) VALUES (?, ?, ?, ?)",
                           (query, dumps(query_card) if query_card else None, verdict, run_id))
    return {"id": int(cur.lastrowid), "status": "created", "asked_count": 1}


def gap_list(conn: sqlite3.Connection, status: str | None = "open", limit: int = 100) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM knowledge_gaps WHERE 1=1", []
    if status and status != "any":
        sql += " AND status = ?"
        args.append(status)
    out = []
    for r in conn.execute(sql + " ORDER BY asked_count DESC, id LIMIT ?", [*args, limit]):
        d = dict(r)
        d["query_card"] = loads(d.pop("query_card_json"), None)
        d["filled_by_cards"] = loads(d.pop("filled_by_cards_json"), [])
        out.append(d)
    return out


def gap_update(conn: sqlite3.Connection, gap_id: int, status: str, filled_by: list[int] | None = None) -> dict[str, Any]:
    if status not in GAP_STATUSES:
        raise CliError("USAGE", f"status must be one of {', '.join(GAP_STATUSES)}")
    if status == "filled" and not filled_by:
        raise CliError("VALIDATION_ERROR", "a filled gap needs --filled-by card ids")
    with transaction(conn):
        if conn.execute("SELECT 1 FROM knowledge_gaps WHERE id = ?", (gap_id,)).fetchone() is None:
            raise CliError("NOT_FOUND", f"gap {gap_id} not found")
        conn.execute("UPDATE knowledge_gaps SET status = ?, filled_by_cards_json = CASE WHEN ? IS NULL THEN filled_by_cards_json ELSE ? END, updated_at = ? WHERE id = ?",
                     (status, dumps(filled_by) if filled_by else None, dumps(filled_by) if filled_by else None, utc_now(), gap_id))
    return {"id": gap_id, "status": status, "filled_by_cards": filled_by or []}


# --- history ----------------------------------------------------------------------------------------------

def history_pending(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT url, title, visit_count, last_visit_at FROM history_entries WHERE triage = 'pending' ORDER BY visit_count DESC, url LIMIT ?", (limit,))]


def history_mark(conn: sqlite3.Connection, urls: list[str], triage: str) -> dict[str, Any]:
    if triage not in ("queued", "not_relevant", "pending"):
        raise CliError("USAGE", "triage must be queued, not_relevant or pending")
    with transaction(conn):
        n = sum(conn.execute("UPDATE history_entries SET triage = ? WHERE url = ?", (triage, u)).rowcount for u in urls)
    return {"marked": n, "triage": triage}
