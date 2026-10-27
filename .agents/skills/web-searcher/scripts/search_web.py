#!/usr/bin/env python3
"""
Web search utility using DuckDuckGo (ddgs) and Bing fallback.
Enables querying the internet for creators, X profiles, Reddit discussions, and market research.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def search_ddgs(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search DuckDuckGo using ddgs library."""
    try:
        from ddgs import DDGS

        with DDGS(timeout=10) as ddgs:
            results = list(ddgs.text(query, max_results=limit))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "engine": "duckduckgo",
                }
                for r in results
            ]
    except Exception:
        return []


def decode_bing_redirect(raw_url: str) -> str:
    """Decode real URL from Bing redirect url parameter."""
    if "u=a1" in raw_url:
        try:
            m = re.search(r"u=a1([A-Za-z0-9_-]+)", raw_url)
            if m:
                b64 = m.group(1).replace("-", "+").replace("_", "/")
                # add padding
                b64 += "=" * ((4 - len(b64) % 4) % 4)
                return base64.b64decode(b64).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return raw_url


def search_bing(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fallback search using Bing HTML endpoint."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded}&setlang=en-US"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        matches = re.findall(r"<h2><a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a></h2>", html, re.DOTALL)

        results = []
        for href, t in matches:
            clean_title = re.sub(r"<[^>]+>", "", t).strip()
            real_url = decode_bing_redirect(href)
            if real_url and not real_url.startswith("javascript:") and "bing.com/search" not in real_url:
                results.append({
                    "title": clean_title,
                    "url": real_url,
                    "snippet": "",
                    "engine": "bing",
                })
        return results[:limit]
    except Exception as e:
        print(f"[WARN] Bing search fallback failed: {e}", file=sys.stderr)
        return []


def search_web(query: str, limit: int = 10, site: Optional[str] = None) -> list[dict[str, Any]]:
    """Execute search across DuckDuckGo with Bing fallback."""
    effective_query = f"site:{site} {query}".strip() if site else query.strip()
    print(f"Searching web for: '{effective_query}' (limit: {limit})...", file=sys.stderr)

    results = search_ddgs(effective_query, limit=limit)
    if not results and site:
        # Retry with site name keyword instead of site:
        fallback_query = f"{query} {site}".strip()
        results = search_ddgs(fallback_query, limit=limit)

    if not results:
        results = search_bing(effective_query, limit=limit)

    return results[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Web search utility.")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--site", help="Domain filter (e.g. x.com, reddit.com)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()
    results = search_web(args.query, limit=args.limit, site=args.site)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"Web Search Results for: {args.query} ({len(results)} found)")
    print("=" * 80)

    for i, r in enumerate(results, start=1):
        print(f"[{i:02d}] {r['title']} ({r['engine']})")
        print(f"     URL: {r['url']}")
        if r.get("snippet"):
            print(f"     Snippet: {r['snippet'][:180]}...")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
