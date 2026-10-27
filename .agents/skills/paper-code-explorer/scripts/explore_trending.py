#!/usr/bin/env python3
"""
Explore daily and weekly trending scientific papers across arXiv and Papers With Code.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_trending_papers(limit: int = 15) -> list[dict[str, Any]]:
    url = f"https://huggingface.co/api/daily_papers?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to fetch trending papers: {e}", file=sys.stderr)
        return []

    papers = []
    for item in data:
        p = item.get("paper", item)
        aid = p.get("id", "")
        repo = p.get("githubRepo")
        if repo and not repo.startswith("http"):
            repo = f"https://github.com/{repo.lstrip('/')}"

        authors = [a.get("name") if isinstance(a, dict) else str(a) for a in p.get("authors", [])]

        papers.append({
            "title": p.get("title", ""),
            "arxiv_id": aid,
            "url": f"https://arxiv.org/abs/{aid}",
            "pdf_url": f"https://arxiv.org/pdf/{aid}.pdf",
            "published_at": p.get("publishedAt", ""),
            "authors": authors,
            "summary": (p.get("summary") or "").strip(),
            "github_repo": repo,
            "github_stars": p.get("githubStars") or 0,
            "upvotes": p.get("upvotes") or 0,
        })

    return papers


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore trending papers on arXiv & Papers With Code.")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max papers to return (default: 10)")
    parser.add_argument("--has-code", action="store_true", help="Only show papers with open-source code")
    parser.add_argument("--save-json", type=Path, help="Save to JSON file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    papers = fetch_trending_papers(limit=args.limit * 2)
    if args.has_code:
        papers = [p for p in papers if p.get("github_repo")]

    papers = papers[:args.limit]

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(papers)} trending papers to: {args.save_json}", file=sys.stderr)

    if args.json:
        print(json.dumps(papers, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"TRENDING RESEARCH PAPERS ({len(papers)} retrieved)")
    print("=" * 80)

    for i, p in enumerate(papers, start=1):
        code_str = f"Code: {p['github_repo']} ({p['github_stars']} stars)" if p.get('github_repo') else "Code: None"
        print(f"[{i:02d}] {p['title']}")
        print(f"     arXiv: {p['arxiv_id']} | Upvotes: {p['upvotes']} | {code_str}")
        print(f"     PDF: {p['pdf_url']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
