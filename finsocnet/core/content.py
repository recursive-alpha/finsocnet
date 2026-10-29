"""Sources, contents and segments: add_content(), get_content(), view, chunks, status changes, search.

Write semantics follow specs/01-database.md §3.1. Contents, segments and citations are never deleted.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from finsocnet.core import fts
from finsocnet.core.db import dumps, loads, transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.normalize import clean_text, hash_text
from finsocnet.core.output import CliError
from finsocnet.core.records import check_contiguous, schema_errors

DUPLICATE_MIN_CHARS = 500
CLAIM_TTL = timedelta(hours=2)
IDENTITY_KEYS = ("comment_id", "message_id", "start_sec", "page", "para")
SOURCE_STATUSES = ("active", "paused", "blocked", "gone", "needs_review")


def _json_cols(row: dict[str, Any]) -> dict[str, Any]:
    for col in [c for c in row if c.endswith("_json")]:
        row[col[:-5]] = loads(row.pop(col), None)
    return row


# --- sources --------------------------------------------------------------------------------------------

def upsert_source(conn: sqlite3.Connection, src: dict[str, Any]) -> dict[str, Any]:
    """Insert a source; update title/url (and status/notes/person when given) if it exists."""
    sid = src.get("id")
    if not sid or ":" not in sid:
        raise CliError("VALIDATION_ERROR", "source needs an id like '<platform>:<kind>:<native>'",
                       details=[{"path": "/id", "problem": "missing or malformed"}])
    status = src.get("status")
    if status is not None and status not in SOURCE_STATUSES:
        raise CliError("VALIDATION_ERROR", f"source status must be one of {', '.join(SOURCE_STATUSES)}")
    parts = sid.split(":")
    platform = src.get("platform") or parts[0]
    kind = src.get("kind") or (parts[1] if len(parts) > 2 else "site")
    existing = conn.execute("SELECT * FROM sources WHERE id = ?", (sid,)).fetchone()
    if existing is None:
        conn.execute(
            """INSERT INTO sources (id, platform, kind, url, title, person_id, requires_session, status, notes, avatar_url, avatar_path, avatar_sha256)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, platform, kind, src.get("url"), src.get("title"), src.get("person_id"),
             1 if src.get("requires_session") else 0, status or "active", src.get("notes"), src.get("avatar_url"), src.get("avatar_path"), src.get("avatar_sha256")),
        )
        return {"id": sid, "status": "created"}
    changes = {}
    for col in ("url", "title", "notes", "avatar_url", "avatar_path", "avatar_sha256"):
        if src.get(col) and src[col] != existing[col]:
            changes[col] = src[col]
    if src.get("person_id") and src["person_id"] != existing["person_id"]:
        changes["person_id"] = src["person_id"]
    if status and status != existing["status"]:
        changes["status"] = status
    if src.get("requires_session") is not None and int(bool(src["requires_session"])) != existing["requires_session"]:
        changes["requires_session"] = int(bool(src["requires_session"]))
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(f"UPDATE sources SET {sets} WHERE id = ?", [*changes.values(), sid])
    return {"id": sid, "status": "updated" if changes else "unchanged"}


def get_source(conn: sqlite3.Connection, source_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if row is None:
        raise CliError("NOT_FOUND", f"source {source_id} not found")
    d = dict(row)
    d["contents"] = conn.execute("SELECT COUNT(*) FROM contents WHERE source_id = ?", (source_id,)).fetchone()[0]
    return d


def list_sources(conn: sqlite3.Connection, platform: str | None = None, person: str | None = None,
                 status: str | None = None, limit: int = 100, no_person: bool = False, search: str | None = None, kind: str | None = None, medium: str | None = None) -> list[dict[str, Any]]:
    from finsocnet.core import taxonomy
    sql, args = f"SELECT *, {taxonomy.DIMENSIONS['sources.medium']['column']} AS medium FROM sources WHERE 1=1", []
    d_fmt = taxonomy.DIMENSIONS["sources.medium"]
    for col, val, dim in (("platform", platform, None), (d_fmt["column"], medium, "sources.medium"), ("kind", kind, "sources.kind"), ("person_id", person, None), ("status", status, None)):
        if val:
            clause, a = taxonomy.clause(dim, col, val) if dim else (f"{col} = ?", [val])
            sql += f" AND {clause}"
            args += a
    if no_person:
        sql += " AND person_id IS NULL"
    if search:
        sql += " AND (id LIKE ? OR title LIKE ? OR url LIKE ?)"
        args += [f"%{search}%"] * 3
    sql += " ORDER BY id LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def set_source_cursor(conn: sqlite3.Connection, source_id: str, cursor: str | None) -> dict[str, Any]:
    if conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone() is None:
        raise CliError("NOT_FOUND", f"source {source_id} not found")
    conn.execute("UPDATE sources SET crawl_cursor = ?, last_crawled_at = ? WHERE id = ?", (cursor, utc_now(), source_id))
    return {"id": source_id, "crawl_cursor": cursor}


# --- add_content ----------------------------------------------------------------------------------------

def locator_key(kind: str, locator: dict[str, Any]) -> str:
    """Identity key used to match re-fetched segments to stored ones."""
    for k in IDENTITY_KEYS:
        if k in locator and locator[k] is not None:
            return f"{k}={locator[k]}"
    return "loc=" + json.dumps(locator, sort_keys=True, separators=(",", ":"))


def _content_hash(texts: list[str]) -> str | None:
    return hash_text("\n".join(texts)) if texts else None


def add_content(conn: sqlite3.Connection, record: dict[str, Any], run_id: int) -> dict[str, Any]:
    """Store a ContentRecord. Returns `{id, status: created|updated|duplicate, segments_added, duplicate_of, warnings}`."""
    errs = schema_errors("content_record", record) + check_contiguous(record.get("segments", []))
    if errs:
        raise CliError("VALIDATION_ERROR", f"content record failed validation ({len(errs)} problem(s))", details=errs)

    segments = []
    for i, s in enumerate(record["segments"]):
        text = clean_text(s["text"])
        if not text:
            raise CliError("VALIDATION_ERROR", f"segment {i} is empty after cleaning",
                           details=[{"path": f"/segments/{i}/text", "problem": "empty after clean_text"}])
        segments.append({**s, "text": text, "locator": s.get("locator") or {}})

    cid = record["id"]
    warnings: list[str] = []
    author = record.get("author") or {}
    with transaction(conn):
        source_id = None
        if record.get("source"):
            upsert_source(conn, record["source"])
            source_id = record["source"]["id"]

        existing = conn.execute("SELECT * FROM contents WHERE id = ?", (cid,)).fetchone()
        if existing is None:
            result = _insert_content(conn, record, segments, source_id, author)
        else:
            result = _update_content(conn, existing, record, segments, source_id, author, warnings)
    result["warnings"] = warnings
    return result


def _insert_content(conn, record, segments, source_id, author) -> dict[str, Any]:
    cid = record["id"]
    texts = [s["text"] for s in segments]
    h = _content_hash(texts)
    total = sum(len(t) for t in texts)
    duplicate_of = None
    status = "metadata_only" if not segments else "new"
    if h and total >= DUPLICATE_MIN_CHARS:
        dup = conn.execute("SELECT id FROM contents WHERE content_hash = ? AND id <> ? AND duplicate_of IS NULL ORDER BY created_at LIMIT 1", (h, cid)).fetchone()
        if dup:
            duplicate_of, status = dup["id"], "skipped_duplicate"
    conn.execute(
        """INSERT INTO contents (id, source_id, platform, content_type, url, title, description, author_handle,
               author_platform_user_id, published_at, language, duration_sec, metrics_json, links_json, mentions_json,
               media_json, extra_json, parent_content_id, raw_path, fetch_method, fetched_at, content_hash,
               duplicate_of, process_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cid, source_id, record["platform"], record["content_type"], record.get("url"), record.get("title"),
         record.get("description"), author.get("handle"), author.get("platform_user_id"), record.get("published_at"),
         record.get("language"), record.get("duration_sec"), dumps(record.get("metrics") or {}),
         dumps(record.get("links") or []), dumps(record.get("mentions") or []), dumps(record.get("media") or []),
         dumps(record.get("extra") or {}), record.get("parent_content_id"), record.get("raw_path"),
         record.get("fetch_method"), record.get("fetched_at") or utc_now(), h, duplicate_of, status),
    )
    for seq, s in enumerate(segments):
        _insert_segment(conn, cid, seq, s)
    return {"id": cid, "status": "duplicate" if duplicate_of else "created", "segments_added": len(segments),
            "duplicate_of": duplicate_of, "process_status": status}


def _insert_segment(conn: sqlite3.Connection, cid: str, seq: int, s: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO content_segments (content_id, seq, kind, locator_json, author_handle, speaker_hint, text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cid, seq, s["kind"], dumps(s["locator"]), (s.get("author") or {}).get("handle"), s.get("speaker_hint"), s["text"]),
    )


def _update_content(conn, existing, record, segments, source_id, author, warnings) -> dict[str, Any]:
    cid = existing["id"]
    stored = conn.execute("SELECT seq, kind, locator_json, text FROM content_segments WHERE content_id = ? ORDER BY seq", (cid,)).fetchall()
    by_key = {locator_key(r["kind"], loads(r["locator_json"], {})): r for r in stored}
    next_seq = (stored[-1]["seq"] + 1) if stored else 0
    cited = {r[0] for r in conn.execute("SELECT segment_seq FROM card_citations WHERE content_id = ? AND segment_seq IS NOT NULL", (cid,))}

    added = 0
    for s in segments:
        key = locator_key(s["kind"], s["locator"])
        match = by_key.get(key)
        if match is None:
            _insert_segment(conn, cid, next_seq, s)
            by_key[key] = {"seq": next_seq, "text": s["text"]}
            next_seq += 1
            added += 1
        elif match["text"] != s["text"]:
            if match["seq"] in cited:
                warnings.append(f"segment {match['seq']} changed upstream but is cited; stored text kept")
            else:
                conn.execute("UPDATE content_segments SET text = ? WHERE content_id = ? AND seq = ?", (s["text"], cid, match["seq"]))

    extra = dict(record.get("extra") or {})
    old_extra = loads(existing["extra_json"], {})
    if "_claim" in old_extra:
        extra["_claim"] = old_extra["_claim"]
    texts = [r[0] for r in conn.execute("SELECT text FROM content_segments WHERE content_id = ? ORDER BY seq", (cid,))]
    status = existing["process_status"]
    if added and status in ("processed", "metadata_only"):
        status = "new"
    elif not texts:
        status = "metadata_only"
    conn.execute(
        """UPDATE contents SET source_id = COALESCE(?, source_id), url = COALESCE(?, url), title = COALESCE(?, title),
               description = COALESCE(?, description), author_handle = COALESCE(?, author_handle),
               author_platform_user_id = COALESCE(?, author_platform_user_id), published_at = COALESCE(?, published_at),
               language = COALESCE(?, language), duration_sec = COALESCE(?, duration_sec), metrics_json = ?,
               links_json = ?, mentions_json = ?, media_json = ?, extra_json = ?, raw_path = COALESCE(?, raw_path),
               fetch_method = COALESCE(?, fetch_method), fetched_at = ?, content_hash = ?, process_status = ?,
               updated_at = ? WHERE id = ?""",
        (source_id, record.get("url"), record.get("title"), record.get("description"), author.get("handle"),
         author.get("platform_user_id"), record.get("published_at"), record.get("language"), record.get("duration_sec"),
         dumps(record.get("metrics") or loads(existing["metrics_json"], {})), dumps(record.get("links") or loads(existing["links_json"], [])),
         dumps(record.get("mentions") or loads(existing["mentions_json"], [])), dumps(record.get("media") or loads(existing["media_json"], [])),
         dumps(extra), record.get("raw_path"), record.get("fetch_method"), record.get("fetched_at") or utc_now(),
         _content_hash(texts), status, utc_now(), cid),
    )
    return {"id": cid, "status": "updated", "segments_added": added, "duplicate_of": existing["duplicate_of"],
            "process_status": status}


# --- reading --------------------------------------------------------------------------------------------

def _require(conn: sqlite3.Connection, content_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM contents WHERE id = ?", (content_id,)).fetchone()
    if row is None:
        raise CliError("NOT_FOUND", f"content {content_id} not found")
    return row


def _people(conn: sqlite3.Connection, content_id: str) -> list[dict[str, Any]]:
    return [
        dict(r) for r in conn.execute(
            "SELECT person_id, role, match_confidence, match_status FROM person_appearances "
            "WHERE content_id = ? AND match_status <> 'rejected' ORDER BY id", (content_id,))
    ]


def get_content(conn: sqlite3.Connection, content_id: str, meta_only: bool = False) -> dict[str, Any]:
    row = _require(conn, content_id)
    d = _json_cols(dict(row))
    d.pop("content_hash", None)
    d["extra"] = {k: v for k, v in (d.get("extra") or {}).items() if not k.startswith("_")}
    stats = conn.execute("SELECT COUNT(*) AS n, COALESCE(MAX(seq), -1) AS max_seq FROM content_segments WHERE content_id = ?", (content_id,)).fetchone()
    d["segment_count"], d["max_seq"] = stats["n"], stats["max_seq"]
    d["people"] = _people(conn, content_id)
    if meta_only:
        for k in ("description", "links", "mentions", "media", "extra", "summary", "metrics"):
            d.pop(k, None)
    return d


def _fmt_time(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def describe_locator(kind: str, locator: dict[str, Any], author: str | None) -> str:
    if "start_sec" in locator:
        return f"{_fmt_time(locator['start_sec'])}-{_fmt_time(locator.get('end_sec', locator['start_sec']))}"
    if "comment_id" in locator:
        bits = [f"comment {locator['comment_id']}"]
        if author:
            bits.append(author)
        if locator.get("score") is not None:
            bits.append(f"score {locator['score']}")
        return " | ".join(bits)
    if "message_id" in locator:
        return " | ".join([f"message {locator['message_id']}"] + ([author] if author else []))
    if "page" in locator:
        return f"page {locator['page']}"
    if "line_start" in locator:
        path = locator.get("path") or ""
        return f"code {path}:{locator['line_start']}-{locator.get('line_end', locator['line_start'])}"
    if "para" in locator:
        ch = f"{locator['chapter']} " if locator.get("chapter") else ""
        return f"{ch}para {locator['para']}"
    return kind


def view_content(conn: sqlite3.Connection, content_id: str, from_seq: int | None = None, to_seq: int | None = None) -> dict[str, Any]:
    """Render segments for the agent (specs/03-pipelines.md §1.2)."""
    c = _require(conn, content_id)
    bounds = conn.execute("SELECT COALESCE(MIN(seq), 0) AS lo, COALESCE(MAX(seq), -1) AS hi FROM content_segments WHERE content_id = ?", (content_id,)).fetchone()
    lo = bounds["lo"] if from_seq is None else from_seq
    hi = bounds["hi"] if to_seq is None else to_seq
    rows = conn.execute("SELECT * FROM content_segments WHERE content_id = ? AND seq BETWEEN ? AND ? ORDER BY seq", (content_id, lo, hi)).fetchall()

    src = conn.execute("SELECT title, person_id FROM sources WHERE id = ?", (c["source_id"],)).fetchone() if c["source_id"] else None
    people = _people(conn, content_id)
    date = (c["published_at"] or "")[:10]
    lines = [f'CONTENT {c["id"]} | {c["content_type"]} | "{c["title"] or ""}" | {date}']
    if c["source_id"]:
        owner = f" | owner person: {src['person_id']}" if src and src["person_id"] else ""
        lines.append(f'SOURCE  {c["source_id"]} ({src["title"] if src else ""}){owner}')
    if people:
        lines.append("PEOPLE  " + ", ".join(f"{p['person_id']} ({p['role']})" for p in people))
    lines.append(f"SEGMENTS {rows[0]['seq'] if rows else lo}-{rows[-1]['seq'] if rows else hi} of {bounds['lo']}-{bounds['hi']}")
    upto = c["processed_upto_seq"]
    for r in rows:
        loc = loads(r["locator_json"], {})
        desc = describe_locator(r["kind"], loc, r["author_handle"])
        speaker = r["person_id"] or r["speaker_hint"] or "?"
        ctx = "(context) " if r["seq"] <= upto else ""
        if "start_sec" in loc:
            lines.append(f"{ctx}[#{r['seq']} | {desc} | speaker {speaker}] {r['text']}")
        else:
            lines.append(f"{ctx}[#{r['seq']} | {desc}] {r['text']}")
    return {"content_id": content_id, "from_seq": rows[0]["seq"] if rows else None,
            "to_seq": rows[-1]["seq"] if rows else None, "segments": len(rows), "text": "\n".join(lines)}


def chunks(conn: sqlite3.Connection, content_id: str, max_chars: int = 12000, overlap: int = 2) -> list[dict[str, Any]]:
    """Chunk plan starting at `processed_upto_seq + 1`; later chunks repeat `overlap` segments as context."""
    c = _require(conn, content_id)
    start = c["processed_upto_seq"] + 1
    segs = conn.execute(
        "SELECT seq, LENGTH(text) AS n FROM content_segments WHERE content_id = ? AND seq >= ? ORDER BY seq", (content_id, start)
    ).fetchall()
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(segs):
        j, chars = i, 0
        while j < len(segs) and (j == i or chars + segs[j]["n"] <= max_chars):
            chars += segs[j]["n"]
            j += 1
        out.append({"chunk": len(out) + 1, "from_seq": segs[i]["seq"], "to_seq": segs[j - 1]["seq"], "chars": chars})
        if j >= len(segs):
            break
        i = max(j - overlap, i + 1)
    return out


# --- status changes -------------------------------------------------------------------------------------

def _claim_info(extra_json: str | None) -> dict[str, Any] | None:
    return (loads(extra_json, {}) or {}).get("_claim")


def claim_content(conn: sqlite3.Connection, content_id: str, run_id: int, reprocess: bool = False) -> dict[str, Any]:
    with transaction(conn):
        c = _require(conn, content_id)
        status = c["process_status"]
        if status in ("metadata_only", "skipped_duplicate"):
            raise CliError("CONFLICT", f"{content_id} is {status} and cannot be mined",
                           "metadata_only has no text yet; skipped_duplicate points to duplicate_of.")
        if status == "processed" and not reprocess:
            raise CliError("CONFLICT", f"{content_id} is already processed", "Use --reprocess to mine it again (decisions are idempotent).")
        claim = _claim_info(c["extra_json"])
        if status == "processing" and claim and claim.get("run_id") != run_id:
            held = datetime.strptime(claim["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - held < CLAIM_TTL:
                raise CliError("CONFLICT", f"{content_id} is being processed by run {claim['run_id']}",
                               "Wait (claims expire after 2 hours) or pick another content.")
        extra = loads(c["extra_json"], {}) or {}
        extra["_claim"] = {"run_id": run_id, "at": utc_now()}
        upto = -1 if reprocess else c["processed_upto_seq"]
        conn.execute("UPDATE contents SET process_status = 'processing', extra_json = ?, processed_upto_seq = ?, updated_at = ? WHERE id = ?",
                     (dumps(extra), upto, utc_now(), content_id))
    return {"id": content_id, "process_status": "processing", "processed_upto_seq": upto}


def set_done(conn: sqlite3.Connection, content_id: str, upto_seq: int, cards: int, transformer: str | None, run_id: int) -> dict[str, Any]:
    with transaction(conn):
        c = _require(conn, content_id)
        max_seq = conn.execute("SELECT COALESCE(MAX(seq), -1) FROM content_segments WHERE content_id = ?", (content_id,)).fetchone()[0]
        if upto_seq > max_seq:
            raise CliError("VALIDATION_ERROR", f"upto-seq {upto_seq} is beyond the last segment ({max_seq})")
        upto = max(upto_seq, c["processed_upto_seq"])
        finished = upto >= max_seq
        extra = loads(c["extra_json"], {}) or {}
        if finished:
            extra.pop("_claim", None)
            status = "processed"
        else:
            status = "processing" if c["process_status"] == "processing" else "new"
            if status == "processing":
                extra["_claim"] = {"run_id": run_id, "at": utc_now()}
        conn.execute(
            """UPDATE contents SET processed_upto_seq = ?, cards_count = ?, process_status = ?, extra_json = ?,
                   processed_with = COALESCE(?, processed_with), processed_at = CASE WHEN ? THEN ? ELSE processed_at END,
                   process_error = NULL, updated_at = ? WHERE id = ?""",
            (upto, cards, status, dumps(extra), transformer, 1 if finished else 0, utc_now(), utc_now(), content_id),
        )
    return {"id": content_id, "process_status": status, "processed_upto_seq": upto, "max_seq": max_seq, "cards_count": cards}


def set_failed(conn: sqlite3.Connection, content_id: str, error: str) -> dict[str, Any]:
    with transaction(conn):
        c = _require(conn, content_id)
        extra = loads(c["extra_json"], {}) or {}
        extra.pop("_claim", None)
        conn.execute("UPDATE contents SET process_status = 'failed', process_error = ?, extra_json = ?, updated_at = ? WHERE id = ?",
                     (error, dumps(extra), utc_now(), content_id))
    return {"id": content_id, "process_status": "failed"}


def link_duplicate(conn: sqlite3.Connection, content_id: str, of: str) -> dict[str, Any]:
    if content_id == of:
        raise CliError("VALIDATION_ERROR", "a content cannot duplicate itself")
    with transaction(conn):
        _require(conn, content_id)
        _require(conn, of)
        conn.execute("UPDATE contents SET duplicate_of = ?, process_status = 'skipped_duplicate', updated_at = ? WHERE id = ?",
                     (of, utc_now(), content_id))
    return {"id": content_id, "duplicate_of": of, "process_status": "skipped_duplicate"}


# --- listing and search ---------------------------------------------------------------------------------

def list_contents(conn: sqlite3.Connection, status: str | None = None, platform: str | None = None,
                  source: str | None = None, person: str | None = None, limit: int = 50, provenance: str | None = None,
                  search: str | None = None, content_type: str | None = None, medium: str | None = None) -> list[dict[str, Any]]:
    from finsocnet.core import taxonomy
    sql = ("SELECT id, platform, content_type, " + taxonomy._type_case() + " AS medium, title, url, source_id, person_id, published_at, process_status, cards_count, fetch_method, "
           "(SELECT COUNT(*) FROM content_segments s WHERE s.content_id = c.id) AS segments FROM contents c WHERE 1=1")
    args: list[Any] = []
    for col, val, dim in (("process_status", status, None), ("platform", platform, None), ("source_id", source, None), ("person_id", person, None),
                          ("content_type", content_type, "content.type"), (taxonomy.DIMENSIONS["content.medium"]["column"], medium, "content.medium")):
        if val:
            clause, a = taxonomy.clause(dim, col, val) if dim else (f"{col} = ?", [val])
            sql += f" AND {clause}"
            args += a
    if provenance == "fetched":
        sql += " AND fetch_method IS NOT NULL AND process_status != 'metadata_only'"
    elif provenance == "missing":
        sql += " AND fetch_method IS NULL AND process_status != 'metadata_only'"
    elif provenance == "metadata_only":
        sql += " AND process_status = 'metadata_only'"
    if search:
        sql += " AND (id LIKE ? OR title LIKE ? OR url LIKE ?)"
        args += [f"%{search}%"] * 3
    sql += " ORDER BY COALESCE(published_at, created_at) DESC, id LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def search_segments(conn: sqlite3.Connection, text: str, platform: str | None = None, person: str | None = None,
                    content: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """BM25 search over segments_fts. All terms must match; falls back to any term when nothing matches."""
    sql = """SELECT s.content_id, s.seq, s.kind, s.locator_json, s.author_handle,
                    snippet(segments_fts, 0, '[', ']', '…', 16) AS snippet, c.title, bm25(segments_fts) AS rank
             FROM segments_fts
             JOIN content_segments s ON s.id = segments_fts.rowid
             JOIN contents c ON c.id = s.content_id
             WHERE segments_fts MATCH ?"""
    tail, args = "", []
    if platform:
        tail += " AND c.platform = ?"
        args.append(platform)
    if person:
        tail += " AND COALESCE(s.person_id, c.person_id) = ?"
        args.append(person)
    if content:
        tail += " AND s.content_id = ?"
        args.append(content)
    tail += " ORDER BY rank LIMIT ?"
    for mode in ("and", "or"):
        expr = fts.match_text(text, mode)
        if expr is None:
            return []
        rows = conn.execute(sql + tail, [expr, *args, limit]).fetchall()
        if rows:
            break
    out = []
    for r in rows:
        d = dict(r)
        d["locator"] = loads(d.pop("locator_json"), {})
        out.append(d)
    return out
