#!/usr/bin/env python3
"""
Database manager for User Knowledge, Experiences, and Hypotheses.
Stores users/creators, content, transcripts, and structured trading hypotheses across platforms
(YouTube, TikTok, Facebook, X, etc.) in SQLite and Chroma vector store.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
SCHEMA_PATH = Path(__file__).parent.parent / "references" / "schema.sql"

try:
    from vector_store import (
        index_content_chunks,
        index_hypothesis_in_vector_store,
        search_content_chunks_vectors,
        search_hypotheses_vectors,
    )
except ImportError:
    _script_dir = Path(__file__).resolve().parent
    if str(_script_dir) not in sys.path:
        sys.path.insert(0, str(_script_dir))
    from vector_store import (
        index_content_chunks,
        index_hypothesis_in_vector_store,
        search_content_chunks_vectors,
        search_hypotheses_vectors,
    )


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    try:
        _root_dir = Path(__file__).resolve().parent.parent.parent.parent
        if str(_root_dir) not in sys.path:
            sys.path.insert(0, str(_root_dir))
        from finsocnet.migrations import auto_migrate
        auto_migrate(conn)
    except Exception:
        pass
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    conn.close()


def upsert_user(
    conn: sqlite3.Connection,
    user_id: str,
    name: str,
    handle: Optional[str] = None,
    platform: str = "youtube",
    profile_url: Optional[str] = None,
    topics: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO users (id, name, handle, platform, profile_url, topics, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            handle = COALESCE(excluded.handle, users.handle),
            platform = excluded.platform,
            profile_url = COALESCE(excluded.profile_url, users.profile_url),
            topics = COALESCE(excluded.topics, users.topics),
            updated_at = CURRENT_TIMESTAMP;
        """,
        (user_id, name, handle, platform.lower(), profile_url, topics),
    )
    conn.commit()


def upsert_content(
    conn: sqlite3.Connection,
    content_id: str,
    user_id: str,
    title: str,
    url: str,
    platform: str = "youtube",
    content_type: str = "video",
    duration: int = 0,
    published_date: Optional[str] = None,
    view_count: int = 0,
    description: Optional[str] = None,
    transcript_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    summary: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO contents (
            id, user_id, platform, title, url, content_type, duration,
            published_date, view_count, description, transcript_path, raw_text, summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            duration = excluded.duration,
            published_date = COALESCE(excluded.published_date, contents.published_date),
            view_count = excluded.view_count,
            description = COALESCE(excluded.description, contents.description),
            transcript_path = COALESCE(excluded.transcript_path, contents.transcript_path),
            raw_text = COALESCE(excluded.raw_text, contents.raw_text),
            summary = COALESCE(excluded.summary, contents.summary);
        """,
        (
            content_id, user_id, platform.lower(), title, url, content_type,
            duration, published_date, view_count, description, transcript_path, raw_text, summary
        ),
    )
    conn.commit()


def ingest_transcript_json(conn: sqlite3.Connection, json_path: Path, platform: str = "youtube") -> dict[str, str]:
    """Ingest a video/content JSON file into users and contents."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    content_id = meta.get("video_id") or meta.get("content_id") or json_path.stem
    user_id = meta.get("channel_id") or meta.get("user_id") or f"{platform}_{content_id}"
    user_name = meta.get("channel") or meta.get("uploader") or meta.get("user_name") or "Content Creator"
    handle = meta.get("uploader_id") or meta.get("handle") or ""
    profile_url = meta.get("channel_url") or meta.get("profile_url") or ""

    upsert_user(
        conn,
        user_id=user_id,
        name=user_name,
        handle=handle,
        platform=platform,
        profile_url=profile_url,
    )

    content_url = meta.get("url") or f"https://www.youtube.com/watch?v={content_id}"
    upsert_content(
        conn,
        content_id=content_id,
        user_id=user_id,
        platform=platform,
        title=meta.get("title", f"Content {content_id}"),
        url=content_url,
        content_type=meta.get("content_type", "video"),
        duration=meta.get("duration", 0),
        published_date=meta.get("upload_date"),
        view_count=meta.get("view_count", 0),
        description=meta.get("description", "")[:1000],
        transcript_path=str(json_path),
    )

    snippets = data.get("transcript")
    if snippets and isinstance(snippets, list):
        try:
            chunks = index_content_chunks(
                content_id=content_id,
                user_id=user_id,
                platform=platform,
                content_title=meta.get("title", f"Content {content_id}"),
                snippets=snippets,
            )
            print(f"[VectorStore] Indexed {chunks} content chunks into Chroma.")
        except Exception as e:
            print(f"[WARN] Vector indexing of transcript chunks failed: {e}", file=sys.stderr)

    return {"content_id": content_id, "user_id": user_id, "title": meta.get("title", "")}


def add_hypothesis(
    conn: sqlite3.Connection,
    content_id: str,
    user_id: str,
    title: str,
    category: str,
    direction: str,
    hypothesis_statement: str,
    verbatim_quote: str,
    setup_conditions: Optional[str] = None,
    holding_period: Optional[str] = None,
    statistical_claim: Optional[str] = None,
    invalidation_risk: Optional[str] = None,
    instrument: str = "equities",
    timestamp_start: float = 0.0,
    timestamp_end: float = 0.0,
    timestamp_formatted: Optional[str] = None,
    platform: str = "youtube",
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO hypotheses (
            content_id, user_id, title, category, direction, instrument,
            hypothesis_statement, setup_conditions, holding_period,
            statistical_claim, invalidation_risk, timestamp_start,
            timestamp_end, timestamp_formatted, verbatim_quote
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            user_id,
            title,
            category,
            direction.upper(),
            instrument,
            hypothesis_statement,
            setup_conditions,
            holding_period,
            statistical_claim,
            invalidation_risk,
            timestamp_start,
            timestamp_end,
            timestamp_formatted,
            verbatim_quote,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid

    try:
        index_hypothesis_in_vector_store({
            "id": row_id,
            "content_id": content_id,
            "user_id": user_id,
            "platform": platform,
            "title": title,
            "category": category,
            "direction": direction.upper(),
            "hypothesis_statement": hypothesis_statement,
            "setup_conditions": setup_conditions,
            "holding_period": holding_period,
            "statistical_claim": statistical_claim,
            "timestamp_formatted": timestamp_formatted,
            "verbatim_quote": verbatim_quote,
        })
    except Exception as e:
        print(f"[WARN] Vector indexing failed for hypothesis #{row_id}: {e}", file=sys.stderr)

    return row_id


def query_hypotheses(
    conn: sqlite3.Connection,
    query: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    user_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> list[sqlite3.Row]:
    sql = """
        SELECT h.*, u.name as user_name, u.handle as user_handle, u.platform as user_platform,
               c.title as content_title, c.url as content_url
        FROM hypotheses h
        JOIN users u ON h.user_id = u.id
        JOIN contents c ON h.content_id = c.id
        WHERE 1=1
    """
    params: list[Any] = []
    if category:
        sql += " AND h.category = ?"
        params.append(category)
    if direction:
        sql += " AND h.direction = ?"
        params.append(direction.upper())
    if user_id:
        sql += " AND (h.user_id = ? OR u.handle = ?)"
        params.extend([user_id, user_id])
    if platform:
        sql += " AND u.platform = ?"
        params.append(platform.lower())
    if query:
        sql += " AND (h.title LIKE ? OR h.hypothesis_statement LIKE ? OR h.setup_conditions LIKE ? OR h.verbatim_quote LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term, term])

    sql += " ORDER BY h.id ASC"
    return conn.execute(sql, params).fetchall()


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    u_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c_count = conn.execute("SELECT COUNT(*) FROM contents").fetchone()[0]
    h_count = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
    platforms = conn.execute("SELECT platform, COUNT(*) as c FROM users GROUP BY platform").fetchall()
    categories = conn.execute("SELECT category, COUNT(*) as c FROM hypotheses GROUP BY category").fetchall()
    directions = conn.execute("SELECT direction, COUNT(*) as c FROM hypotheses GROUP BY direction").fetchall()

    return {
        "users": u_count,
        "contents": c_count,
        "hypotheses": h_count,
        "platforms": {row["platform"]: row["c"] for row in platforms},
        "categories": {row["category"]: row["c"] for row in categories},
        "directions": {row["direction"]: row["c"] for row in directions},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="User Knowledge & Hypothesis Database Manager")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    sub.add_parser("init", help="Initialize or upgrade schema")

    # add-user
    user_p = sub.add_parser("add-user", help="Add or update a user/creator profile")
    user_p.add_argument("user_id", help="Unique User ID")
    user_p.add_argument("name", help="User/Creator display name")
    user_p.add_argument("--handle", help="User handle (e.g. @username)")
    user_p.add_argument("--platform", default="youtube", choices=["youtube", "tiktok", "facebook", "x", "reddit", "medium", "annas_archive", "arxiv", "podcast", "web"])
    user_p.add_argument("--profile-url", help="Profile URL")
    user_p.add_argument("--topics", help="Comma-separated topics")

    # ingest-content
    ingest_p = sub.add_parser("ingest-content", help="Ingest a content JSON file into users/contents")
    ingest_p.add_argument("json_file", type=Path, help="Path to transcript/content JSON")
    ingest_p.add_argument("--platform", default="youtube", choices=["youtube", "tiktok", "facebook", "x", "reddit", "medium", "annas_archive", "arxiv", "podcast", "web"])

    # ingest-hypotheses
    add_hyps_p = sub.add_parser("ingest-hypotheses", help="Ingest hypotheses from a JSON file into SQLite and Chroma")
    add_hyps_p.add_argument("json_file", type=Path, help="JSON file containing array of hypothesis objects")
    add_hyps_p.add_argument("--platform", default="youtube")

    # search
    search_p = sub.add_parser("search", help="Search hypotheses in SQLite")
    search_p.add_argument("--query", "-q", help="Text search query")
    search_p.add_argument("--category", "-c", help="Filter by category")
    search_p.add_argument("--direction", "-d", choices=["LONG", "SHORT", "NEUTRAL", "BOTH"])
    search_p.add_argument("--user", help="Filter by user ID or handle")
    search_p.add_argument("--platform", help="Filter by platform")

    # stats
    sub.add_parser("stats", help="Show database counts and distribution")

    # vector-search
    vec_p = sub.add_parser("vector-search", help="Semantic vector search for hypotheses using Hugging Face embeddings")
    vec_p.add_argument("query", help="Natural language query")
    vec_p.add_argument("--limit", "-k", type=int, default=5, help="Number of results")
    vec_p.add_argument("--category", "-c", help="Filter by category")
    vec_p.add_argument("--direction", "-d", choices=["LONG", "SHORT", "NEUTRAL", "BOTH"])
    vec_p.add_argument("--platform", help="Filter by platform")

    # rag-search
    rag_p = sub.add_parser("rag-search", help="Semantic vector search across raw content chunks")
    rag_p.add_argument("query", help="Natural language query")
    rag_p.add_argument("--limit", "-k", type=int, default=5, help="Number of results")
    rag_p.add_argument("--content-id", help="Filter by content ID")
    rag_p.add_argument("--platform", help="Filter by platform")

    # reindex-vectors
    sub.add_parser("reindex-vectors", help="Re-index all hypotheses and content chunks into Chroma")

    args = parser.parse_args()
    init_db(args.db)
    conn = get_connection(args.db)

    if args.cmd == "init":
        print(f"Database initialized at {args.db}")

    elif args.cmd == "add-user":
        upsert_user(
            conn,
            user_id=args.user_id,
            name=args.name,
            handle=args.handle,
            platform=args.platform,
            profile_url=args.profile_url,
            topics=args.topics,
        )
        print(f"Upserted user '{args.name}' ({args.user_id}) on platform '{args.platform}'")

    elif args.cmd == "ingest-content":
        res = ingest_transcript_json(conn, args.json_file, platform=args.platform)
        print(f"Ingested content '{res['title']}' ({res['content_id']}) for user '{res['user_id']}'")

    elif args.cmd == "ingest-hypotheses":
        with open(args.json_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        if isinstance(items, dict) and "hypotheses" in items:
            items = items["hypotheses"]
        count = 0
        for item in items:
            c_id = item.get("content_id") or item.get("video_id")
            u_id = item.get("user_id") or item.get("channel_id")
            plat = item.get("platform") or args.platform
            add_hypothesis(
                conn,
                content_id=c_id,
                user_id=u_id,
                title=item["title"],
                category=item.get("category", "edge"),
                direction=item.get("direction", "NEUTRAL"),
                instrument=item.get("instrument", "equities"),
                hypothesis_statement=item["hypothesis_statement"],
                verbatim_quote=item["verbatim_quote"],
                setup_conditions=item.get("setup_conditions"),
                holding_period=item.get("holding_period"),
                statistical_claim=item.get("statistical_claim"),
                invalidation_risk=item.get("invalidation_risk"),
                timestamp_start=float(item.get("timestamp_start", 0.0)),
                timestamp_end=float(item.get("timestamp_end", 0.0)),
                timestamp_formatted=item.get("timestamp_formatted"),
                platform=plat,
            )
            count += 1
        print(f"Ingested {count} hypotheses into database.")

    elif args.cmd == "search":
        rows = query_hypotheses(conn, query=args.query, category=args.category, direction=args.direction, user_id=args.user, platform=args.platform)
        print(f"Found {len(rows)} hypotheses:\n")
        for r in rows:
            print(f"[{r['id']}] [{r['direction']}] {r['title']} ({r['user_name']} - {r['user_platform']})")
            print(f"    Statement: {r['hypothesis_statement']}")
            print(f"    Conditions: {r['setup_conditions'] or 'N/A'}")
            print(f"    Holding Period: {r['holding_period'] or 'N/A'}")
            print(f"    Time: {r['timestamp_formatted'] or 'N/A'} | Quote: \"{r['verbatim_quote'][:120]}...\"")
            print()

    elif args.cmd == "stats":
        stats = get_stats(conn)
        print("Knowledge DB Statistics:")
        print(f"  Users:      {stats['users']}")
        print(f"  Contents:   {stats['contents']}")
        print(f"  Hypotheses: {stats['hypotheses']}")
        print(f"  Platforms:  {json.dumps(stats['platforms'])}")
        print(f"  Categories: {json.dumps(stats['categories'])}")
        print(f"  Directions: {json.dumps(stats['directions'])}")

    elif args.cmd == "vector-search":
        results = search_hypotheses_vectors(args.query, n_results=args.limit, category=args.category, direction=args.direction, platform=args.platform)
        print(f"Semantic Vector Search Results for: '{args.query}' ({len(results)} found)\n")
        for r in results:
            m = r["metadata"]
            print(f"[Score: {r['score']:.4f}] #{m.get('hypothesis_id')} [{m.get('direction')}] {m.get('title')} ({m.get('category')}) - {m.get('platform')}")
            print(f"  Time: {m.get('timestamp_formatted')} | Holding: {m.get('holding_period')}")
            print(f"  Preview:\n{r['document']}")
            print("-" * 60)

    elif args.cmd == "rag-search":
        results = search_content_chunks_vectors(args.query, n_results=args.limit, content_id=args.content_id, platform=args.platform)
        print(f"RAG Content Vector Search Results for: '{args.query}' ({len(results)} found)\n")
        for r in results:
            m = r["metadata"]
            print(f"[Score: {r['score']:.4f}] Content: {m.get('title')} ({m.get('content_id')}) [{m.get('platform')}] at [{m.get('timestamp_formatted')}]")
            print(f"  Text:\n{r['document']}")
            print("-" * 60)

    elif args.cmd == "reindex-vectors":
        hyps = conn.execute("SELECT * FROM hypotheses").fetchall()
        print(f"Indexing {len(hyps)} hypotheses into Chroma...")
        for h in hyps:
            index_hypothesis_in_vector_store(dict(h))

        conts = conn.execute("SELECT id, user_id, platform, title, transcript_path FROM contents WHERE transcript_path IS NOT NULL").fetchall()
        total_chunks = 0
        for c in conts:
            t_path = Path(c["transcript_path"])
            if t_path.exists():
                with open(t_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                snippets = data.get("transcript", [])
                if snippets:
                    c_count = index_content_chunks(c["id"], c["user_id"], c["platform"], c["title"], snippets)
                    total_chunks += c_count
                    print(f"  Indexed {c_count} chunks for content {c['id']}")
        print(f"Re-indexing complete: {len(hyps)} hypotheses, {total_chunks} content chunks.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
