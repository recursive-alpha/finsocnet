#!/usr/bin/env python3
"""
Search X (Twitter) for posts, trading topics, tickers ($AAPL), and creator discussions.
Supports authenticated live searching with search-engine fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("X_SESSION_FILE", "data/sessions/x_session.json"))


def search_x_authenticated(query: str, limit: int = 10, session_file: Path = DEFAULT_SESSION_FILE) -> list[dict[str, Any]]:
    if not session_file.exists():
        return []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=str(session_file),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            encoded = urllib.parse.quote(query)
            url = f"https://x.com/search?q={encoded}&f=live"
            print(f"Executing authenticated X search: {url}...", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            if "login" in page.url:
                browser.close()
                return []

            posts = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('article[data-testid="tweet"]').forEach(t => {
                    const authorEl = t.querySelector('[data-testid="User-Name"]');
                    const textEl = t.querySelector('[data-testid="tweetText"]');
                    const timeEl = t.querySelector('time');
                    const linkEl = t.querySelector('a[href*="/status/"]');
                    if (textEl) {
                        out.push({
                            author: authorEl ? authorEl.innerText.split('\\n')[0] : 'Unknown',
                            handle: authorEl ? (authorEl.innerText.match(/@[A-Za-z0-9_]+/) || [''])[0] : '',
                            text: textEl.innerText.trim(),
                            time: timeEl ? timeEl.getAttribute('datetime') : '',
                            url: linkEl ? linkEl.href : '',
                            source: 'x_live'
                        });
                    }
                });
                return out;
            }""")
            browser.close()
            return posts[:limit]
    except Exception as e:
        print(f"[WARN] Live X search failed: {e}", file=sys.stderr)
        return []


def search_x_fallback(query: str, limit: int = 10) -> list[dict[str, Any]]:
    search_script = Path(__file__).resolve().parent.parent.parent / "web-searcher" / "scripts" / "search_web.py"
    import subprocess

    cmd = [sys.executable, str(search_script), query, "--site", "x.com", "--limit", str(limit), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    posts = []

    if proc.returncode == 0:
        try:
            results = json.loads(proc.stdout)
            for r in results:
                url = r.get("url", "")
                if not ("x.com" in url or "twitter.com" in url):
                    continue
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                author = title.split("(@")[0].strip() if "(@" in title else (title.split("/")[0].strip() if "/" in title else title)
                handle_match = re.search(r"@[A-Za-z0-9_]+", title)
                handle = handle_match.group(0) if handle_match else ""

                posts.append({
                    "author": author,
                    "handle": handle,
                    "text": snippet or title,
                    "url": url,
                    "time": "",
                    "source": "search_fallback",
                })
        except Exception:
            pass

    return posts[:limit]


def search_x(query: str, limit: int = 10, session_file: Path = DEFAULT_SESSION_FILE) -> list[dict[str, Any]]:
    print(f"Searching X for: '{query}'...", file=sys.stderr)
    posts = search_x_authenticated(query, limit=limit, session_file=session_file)
    if not posts:
        print("[INFO] Authenticated search unavailable. Using public search fallback...", file=sys.stderr)
        posts = search_x_fallback(query, limit=limit)
    return posts[:limit]

def ingest_posts_into_knowledge_db(posts: list[dict[str, Any]]) -> None:
    import sqlite3
    db_path = Path("data/knowledge.db")
    conn = sqlite3.connect(db_path)

    count = 0
    for p in posts:
        url = p.get("url") or ""
        handle = p.get("handle") or "@x_trader"
        author = p.get("author") or handle
        user_id = f"x_{handle.lstrip('@').lower()}" if handle else f"x_{abs(hash(author))}"

        # Upsert user
        conn.execute("""
            INSERT INTO users (id, name, handle, platform, topics, updated_at)
            VALUES (?, ?, ?, 'x', 'X Posts, Market Analysis', CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, handle=excluded.handle;
        """, (user_id, author, handle))

        status_match = re.search(r"status/(\d+)", url)
        content_id = f"x_{status_match.group(1)}" if status_match else f"x_{abs(hash(url or p['text']))}"
        title = f"X Post by {author}: {p['text'][:60]}..."

        conn.execute("""
            INSERT INTO contents (id, user_id, platform, title, url, content_type, description, raw_text)
            VALUES (?, ?, 'x', ?, ?, 'post', ?, ?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, raw_text=excluded.raw_text;
        """, (content_id, user_id, title, url, p["text"][:300], p["text"]))
        count += 1

    conn.commit()
    conn.close()
    print(f"Ingested {count} X posts into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search X for tweets, traders, and topics.")
    parser.add_argument("query", help="Search query (e.g. Qullamaggie, $NVDA, #daytrading)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest found posts into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    results = search_x(args.query, limit=args.limit, session_file=args.session_file)

    if args.ingest_db and results:
        ingest_posts_into_knowledge_db(results)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"X SEARCH RESULTS: '{args.query}' ({len(results)} found)")
    print("=" * 80)

    for i, p in enumerate(results, start=1):
        author_info = f"{p['author']} ({p['handle']})" if p.get('handle') else p['author']
        print(f"[{i:02d}] {author_info}")
        print(f"     {p['text']}")
        if p.get('url'):
            print(f"     URL: {p['url']}")
        print()

    return 0


if __name__ == "__main__":
    import re
    sys.exit(main())
