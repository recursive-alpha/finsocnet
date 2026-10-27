#!/usr/bin/env python3
"""
Read a Medium article, extract title, author, claps, and full body text, with knowledge.db ingestion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("MEDIUM_SESSION_FILE", "data/sessions/medium_session.json"))


def extract_medium_article(url: str, session_file: Path = DEFAULT_SESSION_FILE) -> dict[str, Any]:
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

        print(f"Reading article: {url}...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)

        data = page.evaluate("""() => {
            const titleEl = document.querySelector('h1, [data-testid="storyTitle"]');
            const authorEl = document.querySelector('span[data-testid="authorName"], a[data-testid="authorName"], a[href*="/@"]');
            const clapsEl = document.querySelector('[data-testid="clapCount"], button[data-testid="headerClapButton"]');

            // Paragraphs & headings inside article
            const contentNodes = document.querySelectorAll('article p, article h2, article h3, article blockquote, article pre');
            const bodyParts = [];
            contentNodes.forEach(node => {
                const text = node.innerText.trim();
                // Skip member notice / footer buttons
                if (text && !text.includes('Member-only story') && !text.includes('Listen') && !text.includes('Share')) {
                    if (node.tagName.toLowerCase() === 'h2' || node.tagName.toLowerCase() === 'h3') {
                        bodyParts.push('\\n### ' + text + '\\n');
                    } else if (node.tagName.toLowerCase() === 'blockquote') {
                        bodyParts.push('> ' + text);
                    } else if (node.tagName.toLowerCase() === 'pre') {
                        bodyParts.push('```\\n' + text + '\\n```');
                    } else {
                        bodyParts.push(text);
                    }
                }
            });

            return {
                title: titleEl ? titleEl.innerText.trim() : document.title.split('|')[0].trim(),
                author: authorEl ? authorEl.innerText.trim() : '',
                claps: clapsEl ? clapsEl.innerText.trim() : '',
                body: bodyParts.join('\\n\\n')
            };
        }""")

        browser.close()
        data["url"] = url
        return data


def ingest_into_knowledge_db(article_data: dict[str, Any]) -> None:
    db_script = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts" / "db.py"
    import subprocess
    import sqlite3

    url = article_data["url"]
    slug_match = re.search(r"/([^/?]+)(?:\?|$)", url)
    content_id = f"medium_{slug_match.group(1)}" if slug_match else f"medium_{abs(hash(url))}"

    author = article_data.get("author") or "Medium Author"
    user_id = f"medium_{re.sub(r'[^a-zA-Z0-9_]+', '', author.lower())}"

    # Add user
    cmd_user = [
        sys.executable, str(db_script), "add-user",
        user_id, author,
        "--handle", f"@{author}",
        "--platform", "medium",
        "--profile-url", f"https://medium.com/@{author.replace(' ', '')}",
        "--topics", "trading, finance, technical analysis",
    ]
    subprocess.run(cmd_user, capture_output=True, check=True)

    # Ingest content into SQLite
    db_path = Path("data/knowledge.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO contents (id, user_id, platform, title, url, content_type, description, raw_text)
        VALUES (?, ?, 'medium', ?, ?, 'article', ?, ?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, raw_text=excluded.raw_text;
    """, (content_id, user_id, article_data["title"], url, article_data["body"][:400], article_data["body"]))
    conn.commit()
    conn.close()

    print(f"Ingested Medium article '{article_data['title']}' ({content_id}) into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Medium article and extract full text.")
    parser.add_argument("url", help="Medium story URL")
    parser.add_argument("--save-json", type=Path, help="Save article data to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest article into knowledge.db")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    data = extract_medium_article(args.url, session_file=args.session_file)

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved article to: {args.save_json}", file=sys.stderr)

    if args.ingest_db:
        ingest_into_knowledge_db(data)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"ARTICLE: {data['title']}")
    author_str = f"by {data['author']}" if data.get('author') else ""
    claps_str = f"({data['claps']} claps)" if data.get('claps') else ""
    print(f"AUTHOR:  {author_str} {claps_str}")
    print(f"URL:     {data['url']}")
    print("=" * 80 + "\n")

    print(data["body"][:2500])
    if len(data["body"]) > 2500:
        print(f"\n... [{len(data['body']) - 2500} more characters]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
