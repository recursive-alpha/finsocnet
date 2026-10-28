"""Language and translation bookkeeping (specs/10-semantic-search.md §3).

Scripts never detect a language and never translate: the agent does both with the `translator` skill and stores the results here.
`contents.language` is the agent's verdict for a whole content (BCP-47, `en`, `vi`, `mixed`); a segment can override it through its
row in `segment_translations` (`source_lang` = `en` with the original text, or any other language with the English text).
Only English text is embedded, so a content whose language is still unknown is not embedded until the agent has looked at it.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from finsocnet.core.db import transaction
from finsocnet.core.output import CliError

SAMPLE_SEGMENTS = 3
SAMPLE_CHARS = 700


def is_english_tag(language: str | None) -> bool:
    return bool(language) and language.lower().replace("_", "-").split("-")[0] == "en"


def detect_pending(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    """Contents whose language the agent has not set yet, each with a sample of the text to look at."""
    out = []
    for c in conn.execute("""SELECT id, platform, content_type, title, url FROM contents
                             WHERE (language IS NULL OR language = '') AND process_status != 'skipped_duplicate'
                               AND EXISTS (SELECT 1 FROM content_segments s WHERE s.content_id = contents.id)
                             ORDER BY created_at DESC, id LIMIT ?""", (limit,)):
        sample = [r[0][:SAMPLE_CHARS] for r in conn.execute("SELECT text FROM content_segments WHERE content_id = ? ORDER BY seq LIMIT ?", (c["id"], SAMPLE_SEGMENTS))]
        out.append({"content_id": c["id"], "platform": c["platform"], "title": c["title"], "sample": sample})
    return out


def set_language(conn: sqlite3.Connection, items: list[dict[str, Any]], run_id: int) -> dict[str, Any]:
    """`[{content_id, language}]` with a BCP-47 tag (`en`, `vi`, `pt-BR`), or `mixed` when segments differ."""
    problems = []
    for i, it in enumerate(items):
        lang = (it.get("language") or "").strip()
        if not lang or len(lang) > 12:
            problems.append({"path": f"/{i}/language", "code": "VALIDATION_ERROR", "problem": "give a BCP-47 tag such as en, vi, pt-BR, or mixed"})
        if not conn.execute("SELECT 1 FROM contents WHERE id = ?", (it.get("content_id"),)).fetchone():
            problems.append({"path": f"/{i}/content_id", "code": "NOT_FOUND", "problem": f"content {it.get('content_id')} does not exist"})
    if problems:
        raise CliError("VALIDATION_ERROR", f"{len(problems)} problem(s)", details=problems)
    with transaction(conn):
        for it in items:
            conn.execute("UPDATE contents SET language = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?", (it["language"].strip(), it["content_id"]))
    return {"updated": len(items)}


def pending(conn: sqlite3.Connection, *, content_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Segments the agent must translate: the content is not English (`language` set, not `en`) and the segment has no row yet."""
    q = """SELECT s.content_id, s.seq, s.text, c.language, c.title FROM content_segments s JOIN contents c ON c.id = s.content_id
           LEFT JOIN segment_translations t ON t.content_id = s.content_id AND t.seq = s.seq
           WHERE t.seq IS NULL AND c.language IS NOT NULL AND c.language != '' AND lower(c.language) NOT LIKE 'en%'
             AND c.process_status != 'skipped_duplicate' {where} ORDER BY s.content_id, s.seq LIMIT ?"""
    args: tuple[Any, ...] = (content_id, limit) if content_id else (limit,)
    return [{"content_id": r["content_id"], "seq": r["seq"], "language": r["language"], "title": r["title"], "text": r["text"]}
            for r in conn.execute(q.format(where="AND s.content_id = ?" if content_id else ""), args)]


def put(conn: sqlite3.Connection, items: list[dict[str, Any]], run_id: int) -> dict[str, Any]:
    """`[{content_id, seq, source_lang, text_en}]`. For a segment that is already English (inside a mixed content) give
    `source_lang: "en"` and omit `text_en`: the original text is recorded as its English text."""
    problems: list[dict[str, Any]] = []
    rows = []
    for i, it in enumerate(items):
        seg = conn.execute("SELECT text FROM content_segments WHERE content_id = ? AND seq = ?", (it.get("content_id"), it.get("seq"))).fetchone()
        if seg is None:
            problems.append({"path": f"/{i}", "code": "NOT_FOUND", "problem": f"segment {it.get('content_id')}#{it.get('seq')} does not exist"})
            continue
        lang = (it.get("source_lang") or "").strip() or None
        text = (it.get("text_en") or "").strip()
        if not text and is_english_tag(lang):
            text = seg["text"]
        if not text:
            problems.append({"path": f"/{i}/text_en", "code": "VALIDATION_ERROR", "problem": "text_en is required unless source_lang is en"})
            continue
        rows.append((it["content_id"], it["seq"], lang, text))
    if problems:
        raise CliError("VALIDATION_ERROR", f"{len(problems)} problem(s) in the translations", details=problems)
    with transaction(conn):
        for cid, seq, lang, text in rows:
            conn.execute("INSERT INTO segment_translations (content_id, seq, source_lang, text_en, run_id) VALUES (?, ?, ?, ?, ?) "
                         "ON CONFLICT(content_id, seq) DO UPDATE SET source_lang = excluded.source_lang, text_en = excluded.text_en, run_id = excluded.run_id",
                         (cid, seq, lang, text, run_id))
    return {"stored": len(rows)}


def get(conn: sqlite3.Connection, content_id: str, seq: int | None = None) -> list[dict[str, Any]]:
    q = "SELECT content_id, seq, source_lang, text_en FROM segment_translations WHERE content_id = ?" + (" AND seq = ?" if seq is not None else "") + " ORDER BY seq"
    return [dict(r) for r in conn.execute(q, (content_id, seq) if seq is not None else (content_id,))]
