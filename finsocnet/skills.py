"""
Skills registry and classification for FinSocNet.
Classifies skills into System Skills (core infrastructure) vs Improved Strategy Skills.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILLS_DIR = Path(__file__).resolve().parent.parent / ".agents" / "skills"

SYSTEM_SKILL_NAMES = {
    "youtube-extractor",
    "audio-transcriber",
    "x-explorer",
    "reddit-explorer",
    "medium-explorer",
    "web-searcher",
    "web-reader",
    "annas-archive-explorer",
    "paper-code-explorer",
    "knowledge-db",
    "hypothesis-miner",
    "user-skill-synthesizer",
}


def parse_skill_md(skill_md_path: Path) -> dict[str, Any]:
    if not skill_md_path.exists():
        return {}

    with open(skill_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k:
                        meta[k] = v

    skill_name = meta.get("name") or skill_md_path.parent.name
    skill_type = "system" if skill_name in SYSTEM_SKILL_NAMES else "improved"

    return {
        "name": skill_name,
        "type": skill_type,
        "description": meta.get("description", ""),
        "author": meta.get("author", "finsocnet"),
        "version": meta.get("version", "1.0.0"),
        "path": str(skill_md_path.parent),
    }


def list_all_skills(skills_dir: Path = SKILLS_DIR, skill_type: Optional[str] = None) -> list[dict[str, Any]]:
    skills = []
    if not skills_dir.exists():
        return []

    for d in sorted(skills_dir.iterdir()):
        if d.is_dir():
            md_path = d / "SKILL.md"
            if md_path.exists():
                info = parse_skill_md(md_path)
                if skill_type and info["type"] != skill_type:
                    continue
                skills.append(info)

    return skills
