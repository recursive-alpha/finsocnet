#!/usr/bin/env python3
"""
Search Reddit across trading communities for creator mentions, strategies, and reviews.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def search_reddit(query: str, limit: int = 10, subreddit: Optional[str] = None) -> list[dict[str, Any]]:
    search_script = Path(__file__).resolve().parent.parent.parent / "web-searcher" / "scripts" / "search_web.py"
    import subprocess

    site_query = f"reddit.com/r/{subreddit}" if subreddit else "reddit.com"
    cmd = [sys.executable, str(search_script), query, "--site", site_query, "--limit", str(limit), "--json"]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    posts = []

    if proc.returncode == 0:
        try:
            results = json.loads(proc.stdout)
            for r in results:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                url = r.get("url", "")

                sub_match = re.search(r"r/([A-Za-z0-9_]+)", url)
                sub_name = f"r/{sub_match.group(1)}" if sub_match else "r/unknown"

                posts.append({
                    "title": title.replace(" - Reddit", "").replace(" : r/", " - r/"),
                    "subreddit": sub_name,
                    "url": url,
                    "snippet": snippet,
                })
        except Exception as e:
            print(f"[WARN] Failed to parse search results: {e}", file=sys.stderr)

    return posts[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Reddit trading discussions.")
    parser.add_argument("query", help="Search query (e.g. Qullamaggie, Humbled Trader, SMC)")
    parser.add_argument("--sub", help="Filter by specific subreddit (e.g. RealDayTrading)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    results = search_reddit(args.query, limit=args.limit, subreddit=args.sub)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"REDDIT SEARCH: '{args.query}' ({len(results)} discussions found)")
    print("=" * 80)

    for i, p in enumerate(results, start=1):
        print(f"[{i:02d}] {p['title']} ({p['subreddit']})")
        print(f"     URL: {p['url']}")
        if p.get("snippet"):
            print(f"     Snippet: {p['snippet'][:160]}...")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
