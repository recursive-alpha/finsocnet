"""Visited-item tracking (specs/11-explore-visited-open-topics.md §1).

Every item an explorer looks at (search hit, list entry, fetched page) gets a row keyed by its canonical item id, so a later `search` / `list`
can say "you already saw this" even when it was never ingested (rejected as irrelevant, failed, still queued). `contents` stays the record of
what was stored; `seen_items` is the record of what was *looked at*.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from finsocnet.core.db import transaction
from finsocnet.core.output import CliError

STATUSES = ("seen", "queued", "fetched", "skipped", "failed")
# A later `seen` must not downgrade a decision that was already made.
_RANK = {"seen": 0, "queued": 1, "failed": 2, "skipped": 3, "fetched": 4}
VISITED = ("fetched", "skipped")  # statuses that make an item `known` (do not fetch it again)


def lookup(conn: sqlite3.Connection, keys: Iterable[str]) -> dict[str, dict[str, Any]]:
    keys = list(dict.fromkeys(keys))
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(keys), 500):
        chunk = keys[i:i + 500]
        for r in conn.execute(f"SELECT key, status, times_seen, first_seen, last_seen, note FROM seen_items WHERE key IN ({','.join('?' * len(chunk))})", chunk):
            out[r["key"]] = dict(r)
    return out


def mark_seen(conn: sqlite3.Connection, platform: str, items: list[dict[str, Any]], run_id: int | None, source_id: str | None = None) -> int:
    """Upsert one row per item (search / list results). Counts the sighting, never lowers a status."""
    if not items:
        return 0
    with transaction(conn):
        for it in items:
            conn.execute(
                """INSERT INTO seen_items (key, platform, kind, url, title, source_id, run_id) VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET times_seen = times_seen + 1, last_seen = strftime('%Y-%m-%dT%H:%M:%SZ','now'),
                       title = COALESCE(seen_items.title, excluded.title), url = COALESCE(seen_items.url, excluded.url),
                       source_id = COALESCE(seen_items.source_id, excluded.source_id)""",
                (it["id"], platform, it.get("kind"), it.get("ref"), (it.get("title") or "")[:300] or None, source_id, run_id))
    return len(items)


def set_status(conn: sqlite3.Connection, key: str, status: str, run_id: int | None, *, platform: str | None = None, note: str | None = None,
               url: str | None = None, title: str | None = None) -> dict[str, Any]:
    """Record a decision about an item. Creates the row when the item was never listed (e.g. a URL pasted by the user)."""
    if status not in STATUSES:
        raise CliError("USAGE", f"unknown status {status!r}", f"one of {', '.join(STATUSES)}")
    with transaction(conn):
        cur = conn.execute("SELECT status FROM seen_items WHERE key = ?", (key,)).fetchone()
        if cur is None:
            conn.execute("INSERT INTO seen_items (key, platform, url, title, status, note, run_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (key, platform or key.split(":", 1)[0], url, title, status, note, run_id))
        elif _RANK[status] >= _RANK[cur["status"]] or note is not None and status == cur["status"]:
            conn.execute("UPDATE seen_items SET status = ?, note = COALESCE(?, note), last_seen = strftime('%Y-%m-%dT%H:%M:%SZ','now'), run_id = COALESCE(?, run_id) WHERE key = ?",
                         (status, note, run_id, key))
    return conn.execute("SELECT * FROM seen_items WHERE key = ?", (key,)).fetchone() and dict(conn.execute("SELECT * FROM seen_items WHERE key = ?", (key,)).fetchone())


def annotate(conn: sqlite3.Connection, items: list[dict[str, Any]]) -> None:
    """Add `visited` (status or None) and `seen_count` to each item; `known` is true for stored contents and for fetched/skipped items."""
    if conn is None or not items:
        return
    try:
        got = lookup(conn, [i["id"] for i in items])
    except sqlite3.OperationalError:  # database not migrated to 004 yet: everything is unseen
        got = {}
    for it in items:
        s = got.get(it["id"])
        it["visited"] = s["status"] if s else None
        it["seen_count"] = s["times_seen"] if s else 0
        if s and s["status"] in VISITED:
            it["known"] = True


def list_items(conn: sqlite3.Connection, *, platform: str | None = None, status: str | None = None, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    where, args = [], []
    for col, val in (("platform", platform), ("status", status), ("source_id", source)):
        if val:
            where.append(f"{col} = ?")
            args.append(val)
    q = "SELECT * FROM seen_items" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY last_seen DESC, key LIMIT ?"
    return [dict(r) for r in conn.execute(q, (*args, limit))]


def stats(conn: sqlite3.Connection) -> dict[str, Any]:
    by = [dict(r) for r in conn.execute("SELECT platform, status, COUNT(*) AS n FROM seen_items GROUP BY platform, status ORDER BY platform, status")]
    total = conn.execute("SELECT COUNT(*), COALESCE(SUM(times_seen), 0) FROM seen_items").fetchone()
    return {"items": total[0], "sightings": total[1], "by_platform_status": by}
