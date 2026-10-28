"""Canonical persons, aliases, appearances, merge (docs/spec/03-pipelines.md §5–§6, 01 §2.3)."""

from __future__ import annotations

import sqlite3
from typing import Any

from finsocnet.core import fts
from finsocnet.core.db import loads, transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.normalize import alias_key
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors

ROLES = ("owner", "guest", "host", "co_host", "author", "co_author", "commenter", "member", "archive", "mentioned")
MATCH_STATUSES = ("confirmed", "needs_review", "rejected")


def resolve_id(conn: sqlite3.Connection, person_id: str) -> str:
    """Follow `merged_into` chains."""
    seen: set[str] = set()
    while person_id not in seen:
        seen.add(person_id)
        r = conn.execute("SELECT status, merged_into FROM persons WHERE id = ?", (person_id,)).fetchone()
        if r is None or r["status"] != "merged" or not r["merged_into"]:
            break
        person_id = r["merged_into"]
    return person_id


def candidates(conn: sqlite3.Connection, name: str | None = None, handle: str | None = None, platform: str | None = None,
               context: str | None = None, content_id: str | None = None) -> list[dict[str, Any]]:
    """Score persons for a name/handle (03 §5.1); top 5 with reasons."""
    scores: dict[str, dict[str, Any]] = {}

    def bump(pid: str, score: float, reason: str) -> None:
        pid = resolve_id(conn, pid)
        e = scores.setdefault(pid, {"score": 0.0, "reasons": []})
        e["reasons"].append(reason)
        e["score"] = max(e["score"], score)

    for label, text in (("handle", handle), ("name", name)):
        if not text:
            continue
        key = alias_key(text)
        for r in conn.execute("SELECT person_id, platform, alias FROM person_aliases WHERE alias_key = ?", (key,)):
            if platform and r["platform"] == platform:
                bump(r["person_id"], 1.0, f"{label} alias '{r['alias']}' on {platform}")
            elif r["platform"] == "":
                bump(r["person_id"], 0.9, f"{label} alias '{r['alias']}' (any platform)")
    if content_id:
        r = conn.execute("SELECT s.person_id FROM contents c JOIN sources s ON s.id = c.source_id WHERE c.id = ? AND s.person_id IS NOT NULL", (content_id,)).fetchone()
        if r:
            bump(r["person_id"], 0.9, "owner of the content's source")
    q = fts.match_text(" ".join(t for t in (name, (handle or "").lstrip("@")) if t), "or")
    if q:
        try:
            rows = conn.execute("SELECT person_id FROM persons_fts WHERE persons_fts MATCH ? ORDER BY bm25(persons_fts, 0.0, 3.0, 1.0) LIMIT 5", (q,)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        for rank, r in enumerate(rows, 1):
            bump(r["person_id"], 0.6 if rank == 1 else 0.4, f"name search rank {rank}")
    out = []
    low = (context or "").lower()
    for pid, e in scores.items():
        p = conn.execute("SELECT canonical_name, status FROM persons WHERE id = ?", (pid,)).fetchone()
        if p is None or p["status"] != "active":
            continue
        if low and p["canonical_name"].lower() in low:
            e["score"] += 0.1
            e["reasons"].append("context mentions the canonical name")
        out.append({"person": {"id": pid, "canonical_name": p["canonical_name"]}, "score": round(e["score"], 2), "reasons": e["reasons"]})
    out.sort(key=lambda x: (-x["score"], x["person"]["id"]))
    return out[:5]


def upsert(conn: sqlite3.Connection, person: dict[str, Any], run_id: int) -> dict[str, Any]:
    errs = schema_errors("person", person)
    if errs:
        raise CliError("VALIDATION_ERROR", f"person failed validation ({len(errs)} problem(s))", details=errs)
    pid = person["id"]
    cols = ("canonical_name", "moniker", "bio", "avatar_url", "trading_style", "primary_markets", "verified_records", "visibility")
    with transaction(conn):
        existing = conn.execute("SELECT * FROM persons WHERE id = ?", (pid,)).fetchone()
        if existing is None:
            vals = {c: person.get(c) for c in cols}
            vals["visibility"] = vals["visibility"] or "public"
            conn.execute(f"INSERT INTO persons (id, {', '.join(cols)}) VALUES (?, {', '.join('?' * len(cols))})", [pid, *vals.values()])
            status = "created"
        else:
            sets = {c: person[c] for c in cols if c in person}
            if sets:
                conn.execute(f"UPDATE persons SET {', '.join(f'{k} = ?' for k in sets)}, updated_at = ? WHERE id = ?", [*sets.values(), utc_now(), pid])
            status = "updated"
        added = [add_alias(conn, pid, a["alias"], a.get("platform", "")) for a in person.get("aliases", [])]
        # the canonical name and moniker always resolve to the person
        add_alias(conn, pid, person.get("canonical_name") or existing["canonical_name"], "", quiet=True)
    return {"id": pid, "status": status, "aliases_added": sum(1 for a in added if a)}


def add_alias(conn: sqlite3.Connection, person_id: str, alias: str, platform: str = "", quiet: bool = False) -> bool:
    key = alias_key(alias)
    if not key:
        raise CliError("VALIDATION_ERROR", "alias is empty")
    if conn.execute("SELECT 1 FROM persons WHERE id = ?", (person_id,)).fetchone() is None:
        raise CliError("NOT_FOUND", f"person {person_id} not found")
    row = conn.execute("SELECT person_id FROM person_aliases WHERE alias_key = ? AND platform = ?", (key, platform)).fetchone()
    if row:
        if row["person_id"] != person_id and not quiet:
            raise CliError("CONFLICT", f"alias '{alias}' on '{platform or 'any'}' already belongs to {row['person_id']}",
                           "use `kb person merge` if these are the same person")
        return False
    conn.execute("INSERT INTO person_aliases (alias_key, alias, platform, person_id) VALUES (?, ?, ?, ?)", (key, alias, platform, person_id))
    return True


def alias_add(conn: sqlite3.Connection, person_id: str, alias: str, platform: str = "") -> dict[str, Any]:
    with transaction(conn):
        return {"person_id": person_id, "alias": alias, "platform": platform, "added": add_alias(conn, person_id, alias, platform)}


def add_appearance(conn: sqlite3.Connection, a: dict[str, Any], run_id: int) -> dict[str, Any]:
    details = []
    if a.get("role") not in ROLES:
        details.append({"path": "/role", "problem": f"role must be one of {', '.join(ROLES)}"})
    conf = a.get("match_confidence", 1.0)
    if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        details.append({"path": "/match_confidence", "problem": "must be between 0 and 1"})
    status = a.get("match_status") or ("confirmed" if conf >= 0.7 else "needs_review")
    if status not in MATCH_STATUSES:
        details.append({"path": "/match_status", "problem": f"must be one of {', '.join(MATCH_STATUSES)}"})
    if not a.get("content_id") and not a.get("source_id"):
        details.append({"path": "/", "problem": "content_id or source_id is required"})
    if details:
        raise CliError("VALIDATION_ERROR", "appearance failed validation", details=details)
    pid = a.get("person_id")
    for table, col, val in (("persons", "id", pid), ("contents", "id", a.get("content_id")), ("sources", "id", a.get("source_id"))):
        if val and conn.execute(f"SELECT 1 FROM {table} WHERE {col} = ?", (val,)).fetchone() is None:
            raise CliError("NOT_FOUND", f"{table[:-1]} {val} not found")
    with transaction(conn):
        dup = conn.execute("SELECT id FROM person_appearances WHERE person_id = ? AND content_id IS ? AND source_id IS ? AND role = ?",
                           (pid, a.get("content_id"), a.get("source_id"), a["role"])).fetchone()
        if dup:
            conn.execute("UPDATE person_appearances SET match_confidence = ?, match_status = ?, evidence = COALESCE(?, evidence) WHERE id = ?",
                         (conf, status, a.get("evidence"), dup["id"]))
            return {"appearance_id": dup["id"], "status": "updated"}
        cur = conn.execute("INSERT INTO person_appearances (person_id, content_id, source_id, role, match_confidence, match_status, evidence, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (pid, a.get("content_id"), a.get("source_id"), a["role"], conf, status, a.get("evidence"), run_id))
        if a["role"] == "owner" and a.get("source_id") and status == "confirmed":
            conn.execute("UPDATE sources SET person_id = ? WHERE id = ? AND person_id IS NULL", (pid, a["source_id"]))
        if a["role"] in ("owner", "author") and a.get("content_id") and status == "confirmed":
            conn.execute("UPDATE contents SET person_id = ? WHERE id = ? AND person_id IS NULL", (pid, a["content_id"]))
    return {"appearance_id": int(cur.lastrowid), "status": "created"}


def get(conn: sqlite3.Connection, person_id: str) -> dict[str, Any]:
    r = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    if r is None:
        raise CliError("NOT_FOUND", f"person {person_id} not found")
    d = dict(r)
    d["aliases"] = [dict(x) for x in conn.execute("SELECT alias, platform FROM person_aliases WHERE person_id = ? ORDER BY platform, alias", (person_id,))]
    s = conn.execute("SELECT cards, appearances, sources FROM person_stats WHERE person_id = ?", (person_id,)).fetchone()
    d["stats"] = dict(s) if s else {}
    d["sources"] = [dict(x) for x in conn.execute("SELECT id, title, status FROM sources WHERE person_id = ?", (person_id,))]
    d["appearances"] = [dict(x) for x in conn.execute(
        "SELECT a.id, a.content_id, a.source_id, a.role, a.match_confidence, a.match_status, c.title FROM person_appearances a LEFT JOIN contents c ON c.id = a.content_id "
        "WHERE a.person_id = ? ORDER BY a.id LIMIT 100", (person_id,))]
    return d


def list_persons(conn: sqlite3.Connection, needs_review: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    if needs_review:
        return [dict(r) for r in conn.execute(
            "SELECT a.id AS appearance_id, a.person_id, p.canonical_name, a.content_id, a.source_id, a.role, a.match_confidence, a.evidence "
            "FROM person_appearances a JOIN persons p ON p.id = a.person_id WHERE a.match_status = 'needs_review' ORDER BY a.id LIMIT ?", (limit,))]
    return [dict(r) for r in conn.execute(
        "SELECT p.id, p.canonical_name, p.moniker, p.visibility, s.cards, s.appearances, s.sources FROM persons p JOIN person_stats s ON s.person_id = p.id ORDER BY s.cards DESC, p.id LIMIT ?", (limit,))]


def person_cards(conn: sqlite3.Connection, person_id: str, category: str | None = None) -> dict[str, Any]:
    """Active cards with at least one citation by the person, grouped by category (input of the rulebook synthesizer)."""
    if conn.execute("SELECT 1 FROM persons WHERE id = ?", (person_id,)).fetchone() is None:
        raise CliError("NOT_FOUND", f"person {person_id} not found")
    sql = ("SELECT DISTINCT k.id FROM knowledge_cards k JOIN card_citations c ON c.card_id = k.id "
           "WHERE c.person_id = ? AND k.status = 'active'")
    args: list[Any] = [person_id]
    if category:
        sql += " AND k.category = ?"
        args.append(category)
    from finsocnet.core import cards as cards_mod
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in conn.execute(sql + " ORDER BY k.id", args):
        card = cards_mod.card_row(conn, r["id"])
        card["citations"] = [c for c in cards_mod._citations(conn, r["id"]) if c["person_id"] == person_id]
        card["stats"] = cards_mod._stats(conn, r["id"])
        groups.setdefault(card["category"], []).append(card)
    return {"person_id": person_id, "total": sum(len(v) for v in groups.values()), "categories": groups}


def merge(conn: sqlite3.Connection, src: str, dst: str, run_id: int) -> dict[str, Any]:
    if src == dst:
        raise CliError("VALIDATION_ERROR", "cannot merge a person into itself")
    moved: dict[str, int] = {}
    with transaction(conn):
        for pid in (src, dst):
            r = conn.execute("SELECT status FROM persons WHERE id = ?", (pid,)).fetchone()
            if r is None:
                raise CliError("NOT_FOUND", f"person {pid} not found")
            if r["status"] != "active":
                raise CliError("CONFLICT", f"person {pid} is {r['status']}")
        conn.execute("UPDATE person_aliases SET person_id = ? WHERE person_id = ?", (dst, src))  # (alias_key, platform) is globally unique, so no clashes
        moved["aliases"] = conn.execute("SELECT COUNT(*) FROM person_aliases WHERE person_id = ?", (dst,)).fetchone()[0]
        for a in conn.execute("SELECT id, content_id, source_id, role FROM person_appearances WHERE person_id = ?", (src,)).fetchall():
            if conn.execute("SELECT 1 FROM person_appearances WHERE person_id = ? AND content_id IS ? AND source_id IS ? AND role = ?",
                            (dst, a["content_id"], a["source_id"], a["role"])).fetchone():
                conn.execute("UPDATE person_appearances SET match_status = 'rejected', evidence = COALESCE(evidence, '') || ' [merged duplicate]' WHERE id = ?", (a["id"],))
            else:
                conn.execute("UPDATE person_appearances SET person_id = ? WHERE id = ?", (dst, a["id"]))
        for table in ("card_citations", "content_segments", "contents", "sources"):
            cur = conn.execute(f"UPDATE {table} SET person_id = ? WHERE person_id = ?", (dst, src))
            moved[table] = cur.rowcount
        skipped = 0
        for sk in conn.execute("SELECT id, skill_name, category FROM person_skills WHERE person_id = ?", (src,)).fetchall():
            if conn.execute("SELECT 1 FROM person_skills WHERE person_id = ? AND skill_name = ? AND category = ?", (dst, sk["skill_name"], sk["category"])).fetchone():
                skipped += 1
            else:
                conn.execute("UPDATE person_skills SET person_id = ? WHERE id = ?", (dst, sk["id"]))
        moved["person_skills_skipped"] = skipped
        conn.execute("UPDATE persons SET status = 'merged', merged_into = ?, updated_at = ? WHERE id = ?", (dst, utc_now(), src))
        conn.execute("UPDATE persons SET updated_at = ? WHERE id = ?", (utc_now(), dst))  # fires the persons_fts refresh trigger (aliases moved)
    return {"merged": src, "into": dst, "moved": moved, "note": "rebuild the rulebook of the target person (`person-skill-synthesizer`)"}


def review_appearance(conn: sqlite3.Connection, appearance_id: int, action: str, to_person: str | None = None) -> dict[str, Any]:
    """Resolve a `needs_review` appearance: confirm, reject, or reassign it to another person."""
    if action not in ("confirm", "reject", "reassign"):
        raise CliError("USAGE", "action must be confirm, reject or reassign")
    with transaction(conn):
        a = conn.execute("SELECT * FROM person_appearances WHERE id = ?", (appearance_id,)).fetchone()
        if a is None:
            raise CliError("NOT_FOUND", f"appearance {appearance_id} not found")
        if action == "confirm":
            conn.execute("UPDATE person_appearances SET match_status = 'confirmed', match_confidence = MAX(match_confidence, 0.9) WHERE id = ?", (appearance_id,))
        elif action == "reject":
            conn.execute("UPDATE person_appearances SET match_status = 'rejected' WHERE id = ?", (appearance_id,))
            if a["content_id"]:
                conn.execute("UPDATE card_citations SET person_id = NULL WHERE content_id = ? AND person_id = ?", (a["content_id"], a["person_id"]))
        else:
            if not to_person or conn.execute("SELECT 1 FROM persons WHERE id = ?", (to_person,)).fetchone() is None:
                raise CliError("NOT_FOUND", f"person {to_person} not found")
            conn.execute("UPDATE person_appearances SET match_status = 'rejected' WHERE id = ?", (appearance_id,))
            if a["content_id"]:
                conn.execute("UPDATE card_citations SET person_id = ? WHERE content_id = ? AND person_id = ?", (to_person, a["content_id"], a["person_id"]))
            dup = conn.execute("SELECT id FROM person_appearances WHERE person_id = ? AND content_id IS ? AND source_id IS ? AND role = ?", (to_person, a["content_id"], a["source_id"], a["role"])).fetchone()
            if dup is None:
                conn.execute("INSERT INTO person_appearances (person_id, content_id, source_id, role, match_confidence, match_status, evidence) VALUES (?, ?, ?, ?, 1.0, 'confirmed', 'reassigned by user')",
                             (to_person, a["content_id"], a["source_id"], a["role"]))
    return {"appearance_id": appearance_id, "action": action, "to": to_person}
