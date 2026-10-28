"""Agent runs, lessons and feedback (docs/spec/01-database.md §2.1, §2.7)."""

from __future__ import annotations

import sqlite3
from typing import Any

from finsocnet.core import config
from finsocnet.core.db import dumps, loads, transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.output import CliError

OUTCOMES = ("success", "partial", "failed", "aborted")
LESSON_KINDS = ("data_fix", "vocabulary", "few_shot", "instruction", "script_bug", "platform_change", "other")
LESSON_STATUSES = ("open", "applied", "proposed", "rejected", "duplicate")
FEEDBACK_TARGETS = ("card", "answer", "person_match", "dedup", "person_skill", "gap")


def resolve_run(conn: sqlite3.Connection, run_id: int | None) -> int:
    """The run id for a write command: `--run` or `FINSOCNET_RUN_ID`. Missing → RUN_REQUIRED (exit 2)."""
    rid = run_id if run_id is not None else config.env_run_id()
    if rid is None:
        raise CliError("RUN_REQUIRED", "this command writes to the database and needs a run id",
                       "Start one with `finsocnet kb run start --skill <skill> --goal <goal>` and pass `--run <id>` (or set FINSOCNET_RUN_ID).")
    if conn.execute("SELECT 1 FROM agent_runs WHERE id = ?", (rid,)).fetchone() is None:
        raise CliError("RUN_REQUIRED", f"run {rid} does not exist", "Start a run with `finsocnet kb run start`.")
    return rid


def produced_by(conn: sqlite3.Connection, run_id: int) -> str:
    """`<harness>/<model>` derived from the run."""
    row = conn.execute("SELECT harness, model FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return "unknown/unknown"
    return f"{row['harness'] or 'unknown'}/{row['model'] or 'unknown'}"


def start_run(conn: sqlite3.Connection, skill: str, goal: str | None = None, harness: str | None = None,
              model: str | None = None, parent: int | None = None) -> int:
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO agent_runs (skill, goal, harness, model, parent_run_id) VALUES (?, ?, ?, ?, ?)",
            (skill, goal, harness, model, parent),
        )
    return int(cur.lastrowid)


def end_run(conn: sqlite3.Connection, run_id: int, outcome: str, stats: Any = None, errors: Any = None) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise CliError("USAGE", f"outcome must be one of {', '.join(OUTCOMES)}")
    row = conn.execute("SELECT id FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise CliError("NOT_FOUND", f"run {run_id} not found")
    with transaction(conn):
        conn.execute(
            "UPDATE agent_runs SET finished_at = ?, outcome = ?, stats_json = COALESCE(?, stats_json), "
            "errors_json = COALESCE(?, errors_json) WHERE id = ?",
            (utc_now(), outcome, dumps(stats) if stats is not None else None, dumps(errors) if errors is not None else None, run_id),
        )
    return {"run_id": run_id, "outcome": outcome}


def list_runs(conn: sqlite3.Connection, skill: str | None = None, since: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM agent_runs WHERE 1=1", []
    if skill:
        sql += " AND skill = ?"
        args.append(skill)
    if since:
        sql += " AND started_at >= ?"
        args.append(since)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    out = []
    for r in conn.execute(sql, args):
        d = dict(r)
        d["stats"] = loads(d.pop("stats_json"), {})
        d["errors"] = loads(d.pop("errors_json"), [])
        out.append(d)
    return out


# --- lessons --------------------------------------------------------------------------------------------

def add_lesson(conn: sqlite3.Connection, run_id: int, skill: str, kind: str, observation: str,
               evidence: str | None = None, proposal: str | None = None) -> int:
    if kind not in LESSON_KINDS:
        raise CliError("USAGE", f"lesson kind must be one of {', '.join(LESSON_KINDS)}")
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO lessons (run_id, skill, kind, observation, evidence, proposal) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, skill, kind, observation, evidence, proposal),
        )
    return int(cur.lastrowid)


def list_lessons(conn: sqlite3.Connection, status: str | None = None, skill: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM lessons WHERE 1=1", []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if skill:
        sql += " AND skill = ?"
        args.append(skill)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def update_lesson(conn: sqlite3.Connection, lesson_id: int, status: str | None = None, ref: str | None = None) -> dict[str, Any]:
    if status is not None and status not in LESSON_STATUSES:
        raise CliError("USAGE", f"lesson status must be one of {', '.join(LESSON_STATUSES)}")
    if conn.execute("SELECT 1 FROM lessons WHERE id = ?", (lesson_id,)).fetchone() is None:
        raise CliError("NOT_FOUND", f"lesson {lesson_id} not found")
    with transaction(conn):
        conn.execute(
            "UPDATE lessons SET status = COALESCE(?, status), ref = COALESCE(?, ref), updated_at = ? WHERE id = ?",
            (status, ref, utc_now(), lesson_id),
        )
    return dict(conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone())


# --- feedback -------------------------------------------------------------------------------------------

def add_feedback(conn: sqlite3.Connection, target_type: str, target_id: str, rating: int, comment: str | None = None) -> int:
    if target_type not in FEEDBACK_TARGETS:
        raise CliError("USAGE", f"target type must be one of {', '.join(FEEDBACK_TARGETS)}")
    if rating not in (-1, 0, 1):
        raise CliError("USAGE", "rating must be -1, 0 or 1")
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO feedback (target_type, target_id, rating, comment) VALUES (?, ?, ?, ?)",
            (target_type, str(target_id), rating, comment),
        )
    return int(cur.lastrowid)


def list_feedback(conn: sqlite3.Connection, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM feedback WHERE 1=1", []
    if status:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def handle_feedback(conn: sqlite3.Connection, feedback_id: int) -> dict[str, Any]:
    if conn.execute("SELECT 1 FROM feedback WHERE id = ?", (feedback_id,)).fetchone() is None:
        raise CliError("NOT_FOUND", f"feedback {feedback_id} not found")
    with transaction(conn):
        conn.execute("UPDATE feedback SET status = 'handled' WHERE id = ?", (feedback_id,))
    return {"feedback_id": feedback_id, "status": "handled"}
