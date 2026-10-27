#!/usr/bin/env python3
"""
Retrieve full paper details, code implementations, and download open-access PDF by arXiv ID.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def extract_arxiv_id(target: str) -> str:
    target = target.strip()
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", target)
    if match:
        return match.group(1)
    if re.match(r"^\d{4}\.\d{4,5}$", target):
        return target
    raise ValueError(f"Could not extract a valid arXiv ID from: {target}")


def get_paper_details(arxiv_id: str) -> dict[str, Any]:
    url = f"https://huggingface.co/api/papers/{arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WARN] Failed to fetch paper from API ({e}), building direct entry...", file=sys.stderr)
        data = {"id": arxiv_id}

    repo = data.get("githubRepo")
    if repo and not repo.startswith("http"):
        repo = f"https://github.com/{repo.lstrip('/')}"

    authors = [a.get("name") if isinstance(a, dict) else str(a) for a in data.get("authors", [])]

    return {
        "arxiv_id": arxiv_id,
        "title": data.get("title", f"Paper {arxiv_id}"),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        "published_at": data.get("publishedAt", ""),
        "authors": authors,
        "summary": data.get("summary", ""),
        "ai_summary": data.get("ai_summary", ""),
        "ai_keywords": data.get("ai_keywords", []),
        "github_repo": repo,
        "github_stars": data.get("githubStars", 0),
        "upvotes": data.get("upvotes", 0),
        "linked_models": data.get("linkedModels", []),
        "linked_datasets": data.get("linkedDatasets", []),
    }


def download_pdf(pdf_url: str, dest_path: Path) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    print(f"Downloading PDF from {pdf_url}...", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())
    print(f"Saved PDF to: {dest_path} ({dest_path.stat().st_size / (1024 * 1024):.2f} MB)", file=sys.stderr)
    return dest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Get paper details and download PDF by arXiv ID.")
    parser.add_argument("target", help="arXiv ID (e.g. 2312.12456) or arXiv URL")
    parser.add_argument("--download-pdf", type=Path, help="Download PDF to specified file path")
    parser.add_argument("--auto-download", action="store_true", help="Auto-download PDF to data/papers/<arxiv_id>.pdf")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest paper into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    try:
        aid = extract_arxiv_id(args.target)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    paper = get_paper_details(aid)

    if args.auto_download:
        args.download_pdf = Path(f"data/papers/{aid}.pdf")

    if args.download_pdf:
        try:
            download_pdf(paper["pdf_url"], args.download_pdf)
            paper["local_pdf_path"] = str(args.download_pdf)
        except Exception as e:
            print(f"Error downloading PDF: {e}", file=sys.stderr)

    if args.ingest_db:
        from search_papers import ingest_into_knowledge_db
        ingest_into_knowledge_db([paper])

    if args.json:
        print(json.dumps(paper, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"ARXIV PAPER: {paper['title']}")
    print(f"ID:      {paper['arxiv_id']}")
    print(f"URL:     {paper['url']}")
    print(f"PDF:     {paper['pdf_url']}")
    if paper.get("github_repo"):
        print(f"CODE:    {paper['github_repo']} ({paper['github_stars']} stars)")
    if paper.get("authors"):
        print(f"AUTHORS: {', '.join(paper['authors'][:5])}")
    print("=" * 80)

    if paper.get("ai_summary"):
        print("\nAI Summary:")
        print(f"  {paper['ai_summary']}")

    if paper.get("summary"):
        print("\nAbstract:")
        clean_abs = "\n".join(paper["summary"].splitlines())
        print(clean_abs[:1500])

    return 0


if __name__ == "__main__":
    sys.exit(main())
