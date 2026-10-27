#!/usr/bin/env python3
"""
Read a Reddit thread: extracts original post body, author, score, and top community comments.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright


def extract_reddit_thread(url: str, max_comments: int = 10, timeout_ms: int = 25000) -> dict[str, Any]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--host-resolver-rules=MAP www.reddit.com 151.101.1.140"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        print(f"Reading thread: {url}...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(3000)

        data = page.evaluate("""(maxComments) => {
            const titleEl = document.querySelector('h1, [slot="title"]');
            const postEl = document.querySelector('shreddit-post');
            const author = postEl ? postEl.getAttribute('author') : '';
            const score = postEl ? postEl.getAttribute('score') : '';
            const subreddit = postEl ? postEl.getAttribute('subreddit-prefixed-name') : '';

            // Body text
            const bodyEl = document.querySelector('shreddit-post [slot="text-body"], div[data-testid="post-body"], .text-neutral-content');
            const body = bodyEl ? bodyEl.innerText.trim() : '';

            // Top comments
            const comments = [];
            document.querySelectorAll('shreddit-comment, [data-testid="comment"]').forEach(c => {
                const cAuthor = c.getAttribute('author') || '';
                const cScore = c.getAttribute('score') || '';
                const textEl = c.querySelector('div[id*="-comment-rtjson-content"], p, [slot="comment"]');
                if (textEl && textEl.innerText.trim().length > 10) {
                    comments.push({
                        author: cAuthor,
                        score: cScore,
                        text: textEl.innerText.trim()
                    });
                }
            });

            return {
                title: titleEl ? titleEl.innerText.trim() : '',
                author: author,
                subreddit: subreddit,
                score: score,
                body: body,
                comments: comments.slice(0, maxComments)
            };
        }""", max_comments)

        browser.close()
        data["url"] = url
        return data


def ingest_into_knowledge_db(thread_data: dict[str, Any]) -> None:
    db_script = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts" / "db.py"
    import subprocess

    thread_id = re.search(r"comments/([A-Za-z0-9_]+)", thread_data["url"])
    content_id = f"reddit_{thread_id.group(1)}" if thread_id else f"reddit_{abs(hash(thread_data['url']))}"
    user_id = f"reddit_{thread_data.get('author') or 'community'}"
    user_name = thread_data.get("author") or "Reddit Community"

    # Add user
    cmd_user = [
        sys.executable, str(db_script), "add-user",
        user_id, user_name,
        "--handle", f"u/{thread_data.get('author', 'community')}",
        "--platform", "reddit",
        "--profile-url", f"https://reddit.com/u/{thread_data.get('author', '')}",
        "--topics", thread_data.get("subreddit", "trading"),
    ]
    subprocess.run(cmd_user, capture_output=True, check=True)

    # Ingest content into SQLite
    import sqlite3
    db_path = Path("data/knowledge.db")
    conn = sqlite3.connect(db_path)
    full_text = thread_data["title"] + "\n\n" + thread_data["body"]
    if thread_data["comments"]:
        full_text += "\n\nTop Comments:\n" + "\n".join(f"- u/{c['author']} ({c['score']} pts): {c['text']}" for c in thread_data["comments"])

    conn.execute("""
        INSERT INTO contents (id, user_id, platform, title, url, content_type, description, raw_text)
        VALUES (?, ?, 'reddit', ?, ?, 'thread', ?, ?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, raw_text=excluded.raw_text;
    """, (content_id, user_id, thread_data["title"], thread_data["url"], thread_data["body"][:500], full_text))
    conn.commit()
    conn.close()

    print(f"Ingested Reddit thread '{thread_data['title']}' ({content_id}) into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Reddit thread and top comments.")
    parser.add_argument("url", help="Reddit thread URL")
    parser.add_argument("--comments", "-c", type=int, default=8, help="Number of comments to extract")
    parser.add_argument("--save-json", type=Path, help="Save to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest thread into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    data = extract_reddit_thread(args.url, max_comments=args.comments)

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved thread to: {args.save_json}", file=sys.stderr)

    if args.ingest_db:
        ingest_into_knowledge_db(data)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"THREAD: {data['title']}")
    print(f"COMMUNITY: {data['subreddit']} | AUTHOR: u/{data['author']} | SCORE: {data['score']}")
    print(f"URL: {data['url']}")
    print("=" * 80)

    if data["body"]:
        print("\nPost Body:")
        print(data["body"][:1500])
        if len(data["body"]) > 1500:
            print(f"... [{len(data['body']) - 1500} more chars]")

    if data["comments"]:
        print(f"\nTop Community Comments ({len(data['comments'])}):")
        for i, c in enumerate(data["comments"], 1):
            print(f"[{i:02d}] u/{c['author']} ({c['score']} pts):")
            print(f"     {c['text'][:300]}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
