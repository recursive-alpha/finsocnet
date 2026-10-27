#!/usr/bin/env python3
"""
Search Anna's Archive (https://annas-archive.gl) for books, papers, and trading resources.
Extracts titles, authors, publishers, file formats (PDF/EPUB), sizes, and MD5 links.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("ANNAS_ARCHIVE_SESSION_FILE", "data/sessions/annas_archive_session.json"))
BASE_URL = os.getenv("ANNAS_ARCHIVE_URL", "https://annas-archive.gl").rstrip("/")


def search_archive_browser(
    query: str,
    ext: Optional[str] = None,
    lang: str = "en",
    limit: int = 15,
    session_file: Path = DEFAULT_SESSION_FILE,
    base_url: str = BASE_URL,
) -> list[dict[str, Any]]:
    """Search Anna's Archive directly using Playwright with session cookies."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context_kwargs = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 900},
            }
            if session_file.exists():
                context_kwargs["storage_state"] = str(session_file)

            context = browser.new_context(**context_kwargs)
            page = context.new_page()

            params = {"q": query}
            if ext:
                params["ext"] = ext.lower()
            if lang and lang != "all":
                params["lang"] = lang.lower()

            search_url = f"{base_url}/search?{urllib.parse.urlencode(params)}"
            print(f"Navigating to Anna's Archive: {search_url}...", file=sys.stderr)
            page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # If stuck on DDoS-guard check without session
            if "check=1" in page.url or "ddos" in page.title().lower():
                print("[WARN] DDoS-Guard challenge active. Use session_manager.py --interactive to save session.", file=sys.stderr)
                browser.close()
                return []

            books = page.evaluate("""() => {
                const items = [];
                const seen = new Set();

                document.querySelectorAll('a[href*="/md5/"]').forEach(a => {
                    const h3 = a.querySelector('h3');
                    if (!h3) return;
                    const title = h3.innerText.trim();
                    if (!title || seen.has(title)) return;
                    seen.add(title);

                    const fullText = a.innerText.trim();
                    const lines = fullText.split('\\n').map(l => l.trim()).filter(Boolean);

                    // Extract format and size info (e.g. "English [en], pdf, 14.5MB")
                    const metaLine = lines.find(l => l.includes('[') || l.includes('MB') || l.includes('KB') || l.includes('pdf') || l.includes('epub')) || '';
                    const authorLine = lines.length > 2 ? lines[1] : '';

                    let href = a.getAttribute('href') || '';
                    const md5Match = href.match(/md5\\/([a-f0-9]{32})/);
                    const md5 = md5Match ? md5Match[1] : '';

                    items.push({
                        title: title,
                        author: authorLine,
                        md5: md5,
                        url: href.startsWith('http') ? href : window.location.origin + href,
                        details: metaLine
                    });
                });

                return items;
            }""")

            browser.close()
            return books[:limit]
    except Exception as e:
        print(f"[WARN] Direct browser search failed: {e}", file=sys.stderr)
        return []


def search_archive_fallback(query: str, limit: int = 15) -> list[dict[str, Any]]:
    """Fallback search using web-searcher targeting site:annas-archive.gl."""
    search_script = Path(__file__).resolve().parent.parent.parent / "web-searcher" / "scripts" / "search_web.py"
    import subprocess

    cmd = [sys.executable, str(search_script), query, "--site", "annas-archive.gl", "--limit", str(limit), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    books = []

    if proc.returncode == 0:
        try:
            results = json.loads(proc.stdout)
            for r in results:
                url = r.get("url", "")
                title = r.get("title", "").replace(" - Anna's Archive", "").replace(" | Anna's Archive", "").strip()
                snippet = r.get("snippet", "")

                md5_match = re.search(r"/md5/([a-f0-9]{32})", url)
                md5 = md5_match.group(1) if md5_match else ""

                if "/md5/" in url or "book" in url.lower() or "search" not in url:
                    books.append({
                        "title": title,
                        "author": "",
                        "md5": md5,
                        "url": url,
                        "details": snippet,
                    })
        except Exception:
            pass

    return books[:limit]


def search_annas_archive(
    query: str,
    ext: Optional[str] = None,
    lang: str = "en",
    limit: int = 15,
    session_file: Path = DEFAULT_SESSION_FILE,
) -> list[dict[str, Any]]:
    print(f"Searching Anna's Archive for: '{query}'...", file=sys.stderr)
    books = search_archive_browser(query, ext=ext, lang=lang, limit=limit, session_file=session_file)
    if not books:
        print("[INFO] Direct search restricted or unauthenticated. Using search index fallback...", file=sys.stderr)
        books = search_archive_fallback(query, limit=limit)
    return books[:limit]


def ingest_into_knowledge_db(books: list[dict[str, Any]], query: str) -> None:
    import sqlite3
    db_path = Path("data/knowledge.db")
    conn = sqlite3.connect(db_path)

    # User entry for Anna's Archive
    conn.execute(
        """
        INSERT INTO users (id, name, handle, platform, topics, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO NOTHING;
        """,
        ("annas_archive", "Anna's Archive", "@annas_archive", "annas_archive", "Books, Research Papers, Trading Textbooks"),
    )

    count = 0
    for b in books:
        content_id = f"aa_{b['md5']}" if b.get('md5') else f"aa_{abs(hash(b['url']))}"
        title = b["title"]
        url = b["url"]
        desc = b.get("details", "")

        conn.execute("""
            INSERT INTO contents (id, user_id, platform, title, url, content_type, description, raw_text)
            VALUES (?, 'annas_archive', 'annas_archive', ?, ?, 'book', ?, ?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, description=excluded.description;
        """, (content_id, title, url, desc, f"Book: {title}\nAuthor/Details: {desc}\nURL: {url}"))
        count += 1

    conn.commit()
    conn.close()
    print(f"Ingested {count} books from Anna's Archive into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Anna's Archive for books and papers.")
    parser.add_argument("query", help="Search query (e.g. Market Wizards, Technical Analysis, Al Brooks)")
    parser.add_argument("--ext", choices=["pdf", "epub", "mobi"], help="File format filter")
    parser.add_argument("--lang", default="en", help="Language code (default: en, use 'all' for any)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    parser.add_argument("--save-json", type=Path, help="Save search results to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest discovered books into knowledge.db")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    books = search_annas_archive(
        args.query,
        ext=args.ext,
        lang=args.lang,
        limit=args.limit,
        session_file=args.session_file,
    )

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(books, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(books)} books to: {args.save_json}", file=sys.stderr)

    if args.ingest_db and books:
        ingest_into_knowledge_db(books, args.query)

    if args.json:
        print(json.dumps(books, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"ANNA'S ARCHIVE SEARCH: '{args.query}' ({len(books)} found)")
    print("=" * 80)

    for i, b in enumerate(books, start=1):
        author_str = f"| {b['author']}" if b.get('author') else ""
        md5_str = f"| MD5: {b['md5']}" if b.get('md5') else ""
        print(f"[{i:02d}] {b['title']} {author_str} {md5_str}")
        print(f"     URL: {b['url']}")
        if b.get("details"):
            print(f"     Details: {b['details'][:160]}...")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
