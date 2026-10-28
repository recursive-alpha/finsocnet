"""Core vs installed skills (docs/spec/07 §5.1): core = every folder in `.agents/skills/` that is not in `config/skills.lock.json`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from finsocnet.core import skill_install

SKILLS_DIR = Path(__file__).resolve().parent.parent / ".agents" / "skills"


def parse_skill_md(skill_md_path: Path) -> dict[str, Any]:
    if not skill_md_path.exists():
        return {}
    fm = skill_install.frontmatter_of(skill_md_path.read_text(encoding="utf-8", errors="replace")) or {}
    meta = fm.get("metadata") or {}
    return {"name": fm.get("name") or skill_md_path.parent.name, "description": str(fm.get("description", "")), "author": str(meta.get("author", "")), "version": str(meta.get("version", "")),
            "path": str(skill_md_path.parent)}


def list_all_skills(skills_dir: Path = SKILLS_DIR, skill_type: Optional[str] = None) -> list[dict[str, Any]]:
    """Rows with `type` in {core, installed}; `skill_type` filters ('system' is accepted as an alias of 'core')."""
    wanted = {"system": "core", "improved": "installed"}.get(skill_type or "", skill_type)
    out = []
    for row in skill_install.list_skills():
        if wanted and row["type"] != wanted:
            continue
        info = parse_skill_md(skills_dir / row["name"] / "SKILL.md")
        out.append({**info, **row})
    return out
