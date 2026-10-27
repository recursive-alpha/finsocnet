#!/usr/bin/env python3
"""
Search scientific papers and code implementations across arXiv and Papers With Code (Hugging Face Papers).
Filters by open-source code availability, GitHub stars, and quantitative finance topics.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_papers(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Query Hugging Face Papers API (Papers With Code index)."""
    encoded = urllib.parse.quote(query)
    url = f"https://huggingface.co/api/papers?q={encoded}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to query papers API: {e}", file=sys.stderr)
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
            "ai_keywords": p.get("ai_keywords", []),
        })

    return papers


def ingest_into_knowledge_db(papers: list[dict[str, Any]]) -> None:
    db_script = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts" / "db.py"
    import sqlite3

    db_path = Path("data/knowledge.db")
    conn = sqlite3.connect(db_path)

    # Upsert arXiv institution user
    conn.execute("""
        INSERT INTO users (id, name, handle, platform, topics, updated_at)
        VALUES ('arxiv_org', 'arXiv & Papers With Code', '@arxiv', 'arxiv', 'Scientific Research Papers, ML Trading, Quantitative Finance', CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO NOTHING;
    """)

    count = 0
    for p in papers:
        content_id = f"arxiv_{p['arxiv_id'].replace('.', '_')}"
        title = p["title"]
        url = p["url"]
        desc = p["summary"][:600]

        raw_text = (
            f"Title: {title}\n"
            f"arXiv ID: {p['arxiv_id']}\n"
            f"Authors: {', '.join(p['authors'])}\n"
            f"Published: {p['published_at']}\n"
            f"GitHub Code: {p.get('github_repo') or 'No code repository linked'}\n\n"
            f"Abstract:\n{p['summary']}"
        )

        conn.execute("""
            INSERT INTO contents (id, user_id, platform, title, url, content_type, description, raw_text)
            VALUES (?, 'arxiv_org', 'arxiv', ?, ?, 'paper', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                raw_text = excluded.raw_text;
        """, (content_id, title, url, desc, raw_text))
        count += 1

    conn.commit()
    conn.close()
    print(f"Ingested {count} papers into knowledge.db (platform='arxiv')", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search scientific research papers and code implementations.")
    parser.add_argument("query", help="Search query (e.g. quantitative trading, market microstructure, time series)")
    parser.add_argument("--has-code", action="store_true", help="Only return papers with open-source GitHub code")
    parser.add_argument("--min-stars", type=int, default=0, help="Minimum GitHub stars threshold")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max papers to return (default: 10)")
    parser.add_argument("--save-json", type=Path, help="Save results to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest papers into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    papers = fetch_papers(args.query, limit=args.limit * 2)

    if args.has_code:
        papers = [p for p in papers if p.get("github_repo")]

    if args.min_stars > 0:
        papers = [p for p in papers if p.get("github_stars", 0) >= args.min_stars]

    papers = papers[:args.limit]

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(papers)} papers to: {args.save_json}", file=sys.stderr)

    if args.ingest_db and papers:
        ingest_into_knowledge_db(papers)

    if args.json:
        print(json.dumps(papers, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"ARXIV & PAPERS WITH CODE: '{args.query}' ({len(papers)} found)")
    print("=" * 80)

    for i, p in enumerate(papers, start=1):
        code_str = f"Code: {p['github_repo']} ({p['github_stars']} stars)" if p.get('github_repo') else "Code: None"
        print(f"[{i:02d}] {p['title']}")
        print(f"     arXiv: {p['arxiv_id']} | Published: {p['published_at'][:10]} | Upvotes: {p['upvotes']}")
        print(f"     URL:  {p['url']} | PDF: {p['pdf_url']}")
        print(f"     {code_str}")
        if p.get("summary"):
            clean_sum = p["summary"].replace("\n", " ")[:180]
            print(f"     Abstract: {clean_sum}...")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
