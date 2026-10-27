#!/usr/bin/env python3
"""
Explore Reddit communities (subreddits) for trading strategies, discussions, and creator reviews.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright


def normalize_subreddit(sub: str) -> str:
    s = sub.strip().lstrip("r/").lstrip("/")
    if "reddit.com" in s:
        m = re.search(r"r/([A-Za-z0-9_]+)", s)
        if m:
            return m.group(1)
    return s


def fetch_subreddit_posts(subreddit: str, sort: str = "hot", limit: int = 20) -> list[dict[str, Any]]:
    sub = normalize_subreddit(subreddit)
    url = f"https://www.reddit.com/r/{sub}/{sort}/"

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

        print(f"Loading r/{sub} ({sort})...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)

        posts = page.evaluate("""() => {
            const out = [];
            const seen = new Set();
            document.querySelectorAll('shreddit-post, article').forEach(el => {
                const title = el.getAttribute('post-title') || (el.querySelector('a[slot="title"]') ? el.querySelector('a[slot="title"]').innerText : '');
                const author = el.getAttribute('author') || '';
                const score = el.getAttribute('score') || '';
                const comments = el.getAttribute('comment-count') || '';
                const permalink = el.getAttribute('permalink') || (el.querySelector('a[slot="title"]') ? el.querySelector('a[slot="title"]').href : '');
                const fullUrl = permalink.startsWith('http') ? permalink : 'https://www.reddit.com' + permalink;

                if (title && !seen.has(title)) {
                    seen.add(title);
                    out.push({
                        title: title.trim(),
                        author: author,
                        score: score,
                        comments: comments,
                        url: fullUrl
                    });
                }
            });
            return out;
        }""")

        browser.close()
        return posts[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore Reddit trading communities.")
    parser.add_argument("subreddit", help="Subreddit name (e.g. RealDayTrading, Daytrading, options)")
    parser.add_argument("--sort", choices=["hot", "new", "top"], default="hot", help="Sort order")
    parser.add_argument("--limit", "-n", type=int, default=15, help="Number of posts to retrieve")
    parser.add_argument("--save-json", type=Path, help="Save result to JSON file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    posts = fetch_subreddit_posts(args.subreddit, sort=args.sort, limit=args.limit)

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "subreddit": f"r/{normalize_subreddit(args.subreddit)}",
            "sort": args.sort,
            "post_count": len(posts),
            "posts": posts,
        }
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(posts)} posts to: {args.save_json}", file=sys.stderr)

    if args.json:
        print(json.dumps(posts, indent=2))
        return 0

    sub_name = normalize_subreddit(args.subreddit)
    print("\n" + "=" * 80)
    print(f"COMMUNITY: r/{sub_name} (Sort: {args.sort})")
    print(f"Retrieved {len(posts)} posts:")
    print("=" * 80)

    for i, p in enumerate(posts, start=1):
        score_str = f"Score: {p['score']}" if p.get('score') else ""
        comm_str = f"{p['comments']} comments" if p.get('comments') else ""
        meta = " | ".join(filter(None, [f"u/{p['author']}" if p.get('author') else "", score_str, comm_str]))

        print(f"[{i:02d}] {p['title']}")
        if meta:
            print(f"     {meta}")
        print(f"     URL: {p['url']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
