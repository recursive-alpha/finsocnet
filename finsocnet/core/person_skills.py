"""Person rulebooks stored in `person_skills` (specs/03-pipelines.md §7). Nothing is written to disk (P7)."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from finsocnet.core.cards import TIMESTAMP_RE
from finsocnet.core.db import dumps, loads, transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors
from finsocnet.core.runs import produced_by

ORDER = ["overview", "setup_and_screening", "entry_and_execution", "trade_management", "risk_and_sizing", "psychology_and_review", "checklists"]


def validate_skill(conn: sqlite3.Connection, skill: dict[str, Any]) -> tuple[list[dict[str, str]], set[int]]:
    problems = [{"path": e["path"], "problem": e["problem"]} for e in schema_errors("person_skill", skill)]
    ids: set[int] = set()
    if problems:
        return problems, ids
    pid = skill["person_id"]
    if conn.execute("SELECT 1 FROM persons WHERE id = ?", (pid,)).fetchone() is None:
        problems.append({"path": "/person_id", "problem": f"person {pid} does not exist"})
    for i, rule in enumerate(skill["rules"]):
        for cid in rule["card_ids"]:
            ids.add(cid)
            row = conn.execute("SELECT status FROM knowledge_cards WHERE id = ?", (cid,)).fetchone()
            if row is None:
                problems.append({"path": f"/rules/{i}/card_ids", "problem": f"card {cid} does not exist"})
            elif row["status"] != "active":
                problems.append({"path": f"/rules/{i}/card_ids", "problem": f"card {cid} is {row['status']}"})
            elif not conn.execute("SELECT 1 FROM card_citations WHERE card_id = ? AND person_id = ?", (cid, pid)).fetchone():
                problems.append({"path": f"/rules/{i}/card_ids", "problem": f"card {cid} has no citation by {pid}"})
    for field in ("title", "summary", "content_markdown"):
        if TIMESTAMP_RE.search(skill.get(field) or ""):
            problems.append({"path": f"/{field}", "problem": "timestamps are not allowed in rulebooks (use card ids)"})
    for i, rule in enumerate(skill["rules"]):
        if TIMESTAMP_RE.search(rule["rule"]):
            problems.append({"path": f"/rules/{i}/rule", "problem": "timestamps are not allowed in rulebooks"})
    return problems, ids


def upsert_skill(conn: sqlite3.Connection, skill: dict[str, Any], run_id: int) -> dict[str, Any]:
    problems, ids = validate_skill(conn, skill)
    if problems:
        raise CliError("VALIDATION_ERROR", f"person skill failed validation ({len(problems)} problem(s))", details=problems)
    with transaction(conn):
        existing = conn.execute("SELECT id FROM person_skills WHERE person_id = ? AND skill_name = ? AND category = ?",
                                (skill["person_id"], skill["skill_name"], skill["category"])).fetchone()
        vals = (skill["title"], skill.get("summary"), skill["content_markdown"], dumps(skill["rules"]), dumps(sorted(ids)),
                produced_by(conn, run_id), run_id, utc_now())
        if existing:
            conn.execute("UPDATE person_skills SET title = ?, summary = ?, content_markdown = ?, rules_json = ?, source_card_ids_json = ?, produced_by = ?, run_id = ?, updated_at = ? WHERE id = ?",
                         (*vals, existing["id"]))
            return {"id": existing["id"], "status": "updated"}
        cur = conn.execute("INSERT INTO person_skills (title, summary, content_markdown, rules_json, source_card_ids_json, produced_by, run_id, updated_at, person_id, skill_name, category) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (*vals, skill["person_id"], skill["skill_name"], skill["category"]))
    return {"id": int(cur.lastrowid), "status": "created"}


def get_skills(conn: sqlite3.Connection, person_id: str, skill_name: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM person_skills WHERE person_id = ?", [person_id]
    if skill_name:
        sql += " AND skill_name = ?"
        args.append(skill_name)
    if category:
        sql += " AND category = ?"
        args.append(category)
    rows = []
    for r in conn.execute(sql, args):
        d = dict(r)
        d["rules"] = loads(d.pop("rules_json"), [])
        d["source_card_ids"] = loads(d.pop("source_card_ids_json"), [])
        rows.append(d)
    rows.sort(key=lambda d: (ORDER.index(d["category"]), d["skill_name"]))
    return rows


def render_markdown(conn: sqlite3.Connection, person_id: str, skill_name: str | None = None, category: str | None = None) -> str:
    p = conn.execute("SELECT canonical_name FROM persons WHERE id = ?", (person_id,)).fetchone()
    if p is None:
        raise CliError("NOT_FOUND", f"person {person_id} not found")
    rows = get_skills(conn, person_id, skill_name, category)
    if not rows:
        raise CliError("NOT_FOUND", f"no rulebook for {person_id}", "build it with the person-skill-synthesizer skill")
    out = [f"# {p['canonical_name']} — rulebook ({person_id})", ""]
    for r in rows:
        out += [f"## {r['title']}", f"_{r['skill_name']} · {r['category']}_", ""]
        if r["summary"]:
            out += [r["summary"], ""]
        out += [r["content_markdown"].strip(), ""]
    return "\n".join(out).rstrip() + "\n"


def list_skills(conn: sqlite3.Connection, person_id: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT person_id, skill_name, category, title, updated_at, json_array_length(source_card_ids_json) AS cards FROM person_skills"
    args: list[Any] = []
    if person_id:
        sql += " WHERE person_id = ?"
        args.append(person_id)
    return [dict(r) for r in conn.execute(sql + " ORDER BY person_id, skill_name, category", args)]
