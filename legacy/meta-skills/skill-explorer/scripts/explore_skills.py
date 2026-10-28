#!/usr/bin/env python3
"""
Skill Explorer: Vector search and capability discovery over synthesized Agent Skills.
Uses Chroma vector embeddings to match trader queries to specific strategies.
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

load_dotenv()

# Add knowledge-db script path
KNOWLEDGE_DB_SCRIPTS = Path(".agents/skills/knowledge-db/scripts")
if str(KNOWLEDGE_DB_SCRIPTS.resolve()) not in sys.path:
    sys.path.insert(0, str(KNOWLEDGE_DB_SCRIPTS.resolve()))

try:
    from vector_store import index_skill_in_vector_store, search_skills_vectors
except ImportError as e:
    print(f"Error importing vector store: {e}", file=sys.stderr)
    sys.exit(1)


def parse_skill_yaml_frontmatter(skill_md_path: Path) -> dict[str, Any]:
    if not skill_md_path.exists():
        return {}
    content = skill_md_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_text = parts[1]
    meta: dict[str, Any] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            meta[k] = v
    return meta


def reindex_all_skills(skills_root: Path = Path(".agents/skills")) -> int:
    indexed = 0
    print(f"Scanning skills under {skills_root}...")
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        fm = parse_skill_yaml_frontmatter(skill_file)
        skill_name = fm.get("name", skill_dir.name)
        meta = {
            "skill_name": skill_name,
            "creator": fm.get("creator") or fm.get("author") or "Unknown",
            "person_id": fm.get("person_id") or fm.get("user_id") or "",
            "platform": fm.get("platform") or "multi-platform",
            "skill_type": fm.get("skill_type") or "tooling",
            "description": fm.get("description", ""),
        }
        index_skill_in_vector_store(skill_name, skill_dir, metadata=meta)
        indexed += 1
        print(f"  Indexed skill: {skill_name} ({meta['creator']} - {meta['skill_type']})")
    print(f"Successfully indexed {indexed} skills into Chroma vector store.")
    return indexed


def search_skills(
    query: str,
    limit: int = 5,
    platform: Optional[str] = None,
    skill_type: Optional[str] = None,
) -> None:
    results = search_skills_vectors(query, n_results=limit, platform=platform, skill_type=skill_type)
    print(f"=== Vector Search Results for Skill Query: '{query}' ({len(results)} found) ===\n")
    for r in results:
        m = r["metadata"]
        print(f"• [Score: {r['score']:.4f}] {m.get('skill_name')} | Creator: {m.get('creator')} ({m.get('skill_type', 'skill')})")
        print(f"  Description: {m.get('description')}")
        print(f"  Path: {m.get('skill_dir')}")
        print("-" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore and vector-search synthesized Agent Skills in Chroma.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # reindex
    subparsers.add_parser("reindex", help="Scan and index all .agents/skills/ into Chroma vector store")

    # search
    search_p = subparsers.add_parser("search", help="Semantic vector search over skills")
    search_p.add_argument("query", help="Trading style, setup query, or rules to search for")
    search_p.add_argument("--limit", type=int, default=5, help="Number of results")
    search_p.add_argument("--platform", help="Filter by platform")
    search_p.add_argument("--skill-type", choices=["creator-strategy", "tooling"], help="Filter by skill type")

    args = parser.parse_args()

    if args.command == "reindex":
        reindex_all_skills()
    elif args.command == "search":
        search_skills(args.query, limit=args.limit, platform=args.platform, skill_type=args.skill_type)
    return 0


if __name__ == "__main__":
    sys.exit(main())
