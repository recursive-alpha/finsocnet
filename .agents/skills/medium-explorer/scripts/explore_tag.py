#!/usr/bin/env python3
"""
Explore Medium tags and topics (e.g. trading, algorithmic-trading, finance) for articles and authors.
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


def normalize_tag(tag: str) -> str:
    t = tag.strip().lower()
    t = re.sub(r"[^a-z0-9-]+", "-", t).strip("-")
    return t


def fetch_medium_tag_articles(
    tag: str,
    limit: int = 15,
    sort: str = "recommended",
    session_file: Path = DEFAULT_SESSION_FILE,
) -> list[dict[str, Any]]:
    clean_tag = normalize_tag(tag)
    url = f"https://medium.com/tag/{clean_tag}" if sort == "recommended" else f"https://medium.com/tag/{clean_tag}/latest"

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

        print(f"Loading Medium tag '{clean_tag}' ({url})...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)

        articles = page.evaluate("""() => {
            const out = [];
            const seen = new Set();

            document.querySelectorAll('article').forEach(a => {
                const titleEl = a.querySelector('h2, h3');
                if (!titleEl) return;
                const title = titleEl.innerText.trim();
                if (!title || seen.has(title)) return;
                seen.add(title);

                const link = titleEl.closest('a') || a.querySelector('a[href*="/"]');
                const authorEl = a.querySelector('p, span[data-testid="authorName"], [data-testid="storyAuthor"]');
                const author = authorEl ? authorEl.innerText.trim() : '';

                // Extract URL without tracking queries
                let cleanUrl = link ? link.href : '';
                if (cleanUrl.includes('?')) {
                    cleanUrl = cleanUrl.split('?')[0];
                }

                out.push({
                    title: title,
                    author: author,
                    url: cleanUrl
                });
            });

            return out;
        }""")

        browser.close()
        return articles[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore articles on Medium by topic tag.")
    parser.add_argument("tag", default="trading", nargs="?", help="Medium tag (e.g. trading, algorithmic-trading, finance)")
    parser.add_argument("--sort", choices=["recommended", "latest"], default="recommended", help="Sort order")
    parser.add_argument("--limit", "-n", type=int, default=15, help="Number of articles to retrieve")
    parser.add_argument("--save-json", type=Path, help="Save articles to JSON file")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    articles = fetch_medium_tag_articles(
        args.tag,
        limit=args.limit,
        sort=args.sort,
        session_file=args.session_file,
    )

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tag": args.tag,
            "sort": args.sort,
            "article_count": len(articles),
            "articles": articles,
        }
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(articles)} articles to: {args.save_json}", file=sys.stderr)

    if args.json:
        print(json.dumps(articles, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"MEDIUM TAG: #{normalize_tag(args.tag)} ({args.sort.upper()})")
    print(f"Retrieved {len(articles)} articles:")
    print("=" * 80)

    for i, a in enumerate(articles, start=1):
        author_str = f"by {a['author']}" if a.get('author') else ""
        print(f"[{i:02d}] {a['title']}")
        if author_str:
            print(f"     {author_str}")
        print(f"     URL: {a['url']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
