"""Migration 003: FinSocNet v2 schema and mapping of the v1 data (specs/01-database.md §5.3).

Renames the v1 tables to legacy_*, creates the v2 schema from 003_v2_schema.sql, and maps users, contents,
transcripts, persons and appearances. Hypotheses and legacy skills are kept for Phase 2.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from finsocnet.core import config
from finsocnet.core.db import dumps
from finsocnet.core.migrations import exec_sql
from finsocnet.core.normalize import alias_key, clean_text, hash_text

V1_RENAMES = [
    ("contents", "legacy_contents"),
    ("users", "legacy_users"),
    ("hypotheses", "legacy_hypotheses"),
    ("skills", "legacy_skills"),
    ("persons", "legacy_persons"),
    ("person_appearances", "legacy_person_appearances"),
]
V1_DROPS = ["market_ideas", "person_skills", "vector_embeddings"]
MUST_BE_EMPTY = ["market_ideas", "person_skills", "vector_embeddings"]

CHANNEL_ID = re.compile(r"^UC[0-9A-Za-z_-]{22}$")
YT_VIDEO_ID = re.compile(r"^[0-9A-Za-z_-]{11}$")
PERSON_ROLES = {"owner", "guest", "host", "co_host", "author", "co_author", "commenter", "member", "archive", "mentioned"}

WINDOW_SEC = 45.0
WINDOW_CHARS = 600
MIN_PARAGRAPH = 80
STUB_CHARS = 150


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def _drop_table_and_fts(conn: sqlite3.Connection, name: str, tables: set[str]) -> None:
    for t in sorted(tables):
        if t == name or t.startswith(f"{name}_fts"):
            conn.execute(f'DROP TABLE IF EXISTS "{t}"')
    # Triggers on the dropped table go with it; leftover triggers named after it are removed explicitly.
    for (trig,) in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name = ?", (name,)).fetchall():
        conn.execute(f'DROP TRIGGER IF EXISTS "{trig}"')


def _day_or_none(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    if re.fullmatch(r"\d{8}", v):
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    return v


def map_user(uid: str, platform: str, handle: str | None, name: str) -> tuple[str | None, str | None, str, str | None]:
    """Return (source_id, kind, status, note) for a legacy user row; source_id None = no source."""
    if platform == "youtube":
        if CHANNEL_ID.match(uid):
            return f"youtube:channel:{uid}", "channel", "active", None
        h = (handle or uid).lstrip("@").lower()
        return f"youtube:handle:{h}", "handle", "needs_review", "not a real channel id"
    if uid == "x_x_trader":
        return "x:user:x_trader", "user", "needs_review", "title looks unrelated"
    if uid.startswith("x_"):
        return f"x:user:{uid[2:]}", "user", "active", None
    if uid.startswith("reddit_"):
        return f"reddit:user:{uid[7:].lower()}", "user", "active", None
    if uid.startswith("medium_"):
        return f"medium:user:{uid[7:]}", "user", "active", None
    return None, None, "active", None  # annas_archive, arxiv_org, system


def map_content_id(old: str, platform: str, content_type: str | None) -> tuple[str, str, str | None]:
    """Return (new_id, content_type, forced_status)."""
    ct = content_type or "video"
    if platform == "youtube" and YT_VIDEO_ID.match(old):
        return f"youtube:{old}", ct, None
    if old.startswith("reddit_"):
        return f"reddit:{old[7:]}", "thread", None
    if old.startswith("x_"):
        return f"x:{old[2:]}", "post", None
    if old.startswith("medium_"):
        return f"medium:{old[7:]}", "article", None
    if old.startswith("arxiv_"):
        rest = old[6:]
        return "arxiv:" + (rest.replace("_", ".", 1) if "_" in rest else rest), "paper", None
    if old.startswith("aa_"):
        return f"book:aa-{old[3:]}", "book", "needs_review"
    return f"{platform}:{old}", ct, "needs_review"


def merge_transcript(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge caption entries into windows of <= 45 s and <= 600 chars."""
    windows: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for e in entries:
        text = " ".join(str(e.get("text", "")).split())
        if not text:
            continue
        start = float(e.get("start", 0.0) or 0.0)
        end = start + float(e.get("duration", 0.0) or 0.0)
        if cur is not None:
            too_long = end - cur["start"] > WINDOW_SEC
            too_big = len(cur["text"]) + 1 + len(text) > WINDOW_CHARS
            if too_long or too_big:
                windows.append(cur)
                cur = None
        if cur is None:
            cur = {"start": start, "end": end, "text": text}
        else:
            cur["text"] += " " + text
            cur["end"] = max(cur["end"], end)
    if cur is not None:
        windows.append(cur)
    return windows


def split_paragraphs(raw: str) -> list[str]:
    """Split on blank lines; paragraphs shorter than 80 chars merge into the next one."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    out: list[str] = []
    carry = ""
    for p in parts:
        cand = f"{carry}\n\n{p}" if carry else p
        if len(cand) < MIN_PARAGRAPH:
            carry = cand
        else:
            out.append(cand)
            carry = ""
    if carry:
        if out:
            out[-1] = f"{out[-1]}\n\n{carry}"
        else:
            out.append(carry)
    return out


def _load_transcript(path_str: str | None) -> list[dict[str, Any]] | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = config.repo_root() / p
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entries = data.get("transcript") if isinstance(data, dict) else data
    return entries if isinstance(entries, list) and entries else None


def up(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = _tables(conn)

    # 1. Expected-empty v1 tables must be empty.
    for t in MUST_BE_EMPTY:
        if t in tables and conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] > 0:
            raise RuntimeError(f"migration 003 aborted: table {t} has rows but is expected to be empty")

    # 2. Rename v1 tables, drop the unused ones (each guarded by existence).
    renamed: list[str] = []
    for old, new in V1_RENAMES:
        if old in tables:
            conn.execute(f'ALTER TABLE "{old}" RENAME TO "{new}"')
            renamed.append(old)
    for t in V1_DROPS:
        if t in tables:
            _drop_table_and_fts(conn, t, tables)

    # 3. v2 DDL.
    ddl = (Path(__file__).with_name("003_v2_schema.sql")).read_text(encoding="utf-8")
    exec_sql(conn, ddl)

    # 4. Migration run.
    cur = conn.execute("INSERT INTO agent_runs (skill, goal, harness, outcome) VALUES ('migration', '003_v2_schema', 'manual', 'success')")
    run_id = cur.lastrowid

    summary: dict[str, Any] = {"run_id": run_id, "renamed": renamed, "needs_review": Counter()}
    existing = _tables(conn)

    # 5. persons
    if "legacy_persons" in existing:
        conn.execute(
            """INSERT INTO persons (id, canonical_name, moniker, bio, avatar_url, trading_style, primary_markets,
                                    verified_records, visibility)
               SELECT id, canonical_name, moniker, bio, avatar_url, trading_style, primary_markets, verified_records, 'public'
               FROM legacy_persons"""
        )
    summary["persons"] = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]

    # 6. users -> sources
    conn.execute("CREATE TABLE IF NOT EXISTS legacy_id_map (kind TEXT NOT NULL, old_id TEXT NOT NULL, new_id TEXT, PRIMARY KEY (kind, old_id))")
    sources_made = 0
    if "legacy_users" in existing:
        for u in conn.execute("SELECT id, name, handle, platform, profile_url FROM legacy_users").fetchall():
            sid, kind, status, note = map_user(u["id"], u["platform"], u["handle"], u["name"])
            if sid is None:
                conn.execute("INSERT OR IGNORE INTO legacy_id_map (kind, old_id, new_id) VALUES ('source', ?, NULL)", (u["id"],))
                continue
            platform = sid.split(":", 1)[0]
            conn.execute(
                """INSERT OR IGNORE INTO sources (id, platform, kind, url, title, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sid, platform, kind, u["profile_url"], u["name"], status, note),
            )
            conn.execute("INSERT OR REPLACE INTO legacy_id_map (kind, old_id, new_id) VALUES ('source', ?, ?)", (u["id"], sid))
            sources_made += 1
            if status == "needs_review":
                summary["needs_review"]["sources"] += 1
    summary["sources"] = sources_made

    # 7. contents + segments
    counts = Counter()
    if "legacy_contents" in existing:
        user_map = {r["old_id"]: r["new_id"] for r in conn.execute("SELECT old_id, new_id FROM legacy_id_map WHERE kind = 'source'")}
        rows = conn.execute("SELECT * FROM legacy_contents").fetchall()
        for r in rows:
            new_id, ctype, forced = map_content_id(r["id"], r["platform"], r["content_type"])
            segments: list[tuple[str, dict[str, Any], str]] = []
            transcript = _load_transcript(r["transcript_path"])
            raw = r["raw_text"] or ""
            if transcript:
                for w in merge_transcript(transcript):
                    segments.append(("transcript", {"start_sec": round(w["start"], 2), "end_sec": round(w["end"], 2)}, clean_text(w["text"])))
            elif raw.strip():
                for i, para in enumerate(split_paragraphs(raw)):
                    segments.append(("paragraph", {"para": i}, clean_text(para)))

            if not segments:
                status = "metadata_only"
            elif forced:
                status = forced
            elif len(raw.strip()) <= STUB_CHARS and not transcript:
                status = "needs_review"
            else:
                status = "new"
            if status == "needs_review":
                summary["needs_review"]["contents"] += 1

            content_hash = hash_text("\n".join(s[2] for s in segments)) if segments else None
            metrics = {"views": r["view_count"]} if r["view_count"] else {}
            conn.execute(
                """INSERT INTO contents (id, source_id, platform, content_type, url, title, description, published_at,
                                         duration_sec, metrics_json, content_hash, process_status, summary, fetch_method)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'legacy')""",
                (
                    new_id,
                    user_map.get(r["user_id"]),
                    r["platform"] if r["platform"] != "annas_archive" else "book",
                    ctype,
                    r["url"],
                    r["title"],
                    r["description"],
                    _day_or_none(r["published_date"]),
                    r["duration"] or None,
                    dumps(metrics),
                    content_hash,
                    status,
                    r["summary"],
                ),
            )
            for seq, (kind, locator, text) in enumerate(segments):
                conn.execute(
                    "INSERT INTO content_segments (content_id, seq, kind, locator_json, text) VALUES (?, ?, ?, ?, ?)",
                    (new_id, seq, kind, dumps(locator), text),
                )
            conn.execute("INSERT OR REPLACE INTO legacy_id_map (kind, old_id, new_id) VALUES ('content', ?, ?)", (r["id"], new_id))
            counts[status] += 1
        summary["contents"] = {"total": len(rows), "by_status": dict(counts)}
    else:
        summary["contents"] = {"total": 0, "by_status": {}}

    # 8. appearances + aliases
    appearances = 0
    if "legacy_person_appearances" in existing:
        content_map = {r["old_id"]: r["new_id"] for r in conn.execute("SELECT old_id, new_id FROM legacy_id_map WHERE kind = 'content'")}
        source_map = {r["old_id"]: r["new_id"] for r in conn.execute("SELECT old_id, new_id FROM legacy_id_map WHERE kind = 'source'")}
        for a in conn.execute("SELECT * FROM legacy_person_appearances").fetchall():
            role = a["role"] if a["role"] in PERSON_ROLES else "mentioned"
            source_id = source_map.get(a["platform_id"]) if a["platform_id"] else None
            content_id = content_map.get(a["content_id"]) if a["content_id"] else None
            conn.execute(
                """INSERT OR IGNORE INTO person_appearances (person_id, content_id, source_id, role, evidence, run_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (a["person_id"], content_id, source_id, role, a["notes"], run_id),
            )
            appearances += 1
            name = a["handle_or_name"]
            if name and name.strip():
                conn.execute(
                    "INSERT OR IGNORE INTO person_aliases (alias_key, alias, platform, person_id) VALUES (?, ?, ?, ?)",
                    (alias_key(name), name.strip(), a["platform"] or "", a["person_id"]),
                )
            if role == "owner" and source_id:
                conn.execute("UPDATE sources SET person_id = ? WHERE id = ? AND person_id IS NULL", (a["person_id"], source_id))
    summary["person_appearances"] = appearances
    summary["person_aliases"] = conn.execute("SELECT COUNT(*) FROM person_aliases").fetchone()[0]

    # 9. legacy_hypotheses / legacy_skills stay for Phase 2.
    summary["legacy_kept"] = [t for t in ("legacy_hypotheses", "legacy_skills") if t in existing]
    summary["needs_review"] = dict(summary["needs_review"])
    return summary
