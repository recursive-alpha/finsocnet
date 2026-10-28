"""Final acceptance checklist of specs/08-phases.md as executable checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
PY = [p for d in ("finsocnet", ".agents") for p in (ROOT / d).rglob("*.py") if "__pycache__" not in p.parts]


def frontmatter(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    assert text.startswith("---"), p
    return yaml.safe_load(text.split("---", 2)[1])


def test_sqlite_only_no_vector_stack():
    bad = re.compile(r"chromadb|sentence_transformers|SentenceTransformer|vector_store")  # the grep of specs/08 Phase 0
    offenders = [str(p.relative_to(ROOT)) for p in PY if bad.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
    deps = (ROOT / "pyproject.toml").read_text()
    assert not re.search(r"chromadb|sentence-transformers|torch|faiss|duckduckgo-search", deps)
    assert not (ROOT / "data" / "chroma_db").exists()


def test_no_llm_sdk_in_any_script():
    bad = re.compile(r"^\s*(import|from)\s+(anthropic|openai|litellm|google\.generativeai|ollama|mistralai|cohere)\b", re.M)
    assert [str(p.relative_to(ROOT)) for p in PY if bad.search(p.read_text(encoding="utf-8"))] == []


def test_no_browser_launch_in_skills_or_adapters():
    bad = re.compile(r"chromium\.launch\(|launch_persistent_context\(|\.new_context\(")
    scan = [p for p in PY if ".agents" in p.parts or "adapters" in p.parts]
    assert [str(p.relative_to(ROOT)) for p in scan if bad.search(p.read_text(encoding="utf-8"))] == []


def test_every_skill_has_valid_agentskills_frontmatter():
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir():
            continue
        fm = frontmatter(d / "SKILL.md")
        assert fm["name"] == d.name and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", d.name) and len(d.name) <= 64, d.name
        assert 20 < len(fm["description"]) <= 1024, d.name
        assert len(str(fm.get("compatibility", ""))) <= 500, d.name


def test_skill_docs_only_reference_scripts_that_exist():
    allscripts = {p.name for p in SKILLS.glob("*/scripts/*.py")}
    missing = []
    for md in SKILLS.glob("*/SKILL.md"):
        for m in set(re.findall(r"scripts/([\w.-]+\.py)", md.read_text())):
            if m not in allscripts:
                missing.append((md.parent.name, m))
    assert missing == []


def test_no_person_skill_folders_and_every_folder_is_core_or_locked():
    lock = json.loads((ROOT / "config" / "skills.lock.json").read_text())["skills"]
    people = {p.stem for p in (ROOT / "data" / "persons").glob("*.json")} if (ROOT / "data" / "persons").exists() else set()
    person_like = re.compile(r"(minervini|qullamaggie|breitstein|lewis-kelly|humbled|bellafiore|smb-capital|trader-dante|peter-brandt|chat-with-traders|furey)")
    names = [d.name for d in SKILLS.iterdir() if d.is_dir()]
    assert [n for n in names if person_like.search(n) or n in people] == []
    core = {n for n in names if n not in lock}
    assert {"knowledge-db", "knowledge-transformer", "knowledge-dedup", "knowledge-search", "market-idea-miner", "person-matcher", "source-explorer", "self-improver", "skill-installer"} <= core
    for n in lock:
        assert (SKILLS / n).exists(), f"locked skill {n} missing on disk"


def test_env_example_has_no_credentials_and_no_vector_settings():
    keys = {l.split("=")[0].strip().lstrip("# ").strip() for l in (ROOT / ".env.example").read_text().splitlines() if "=" in l}
    removed = {"X_AUTH_TOKEN", "X_USERNAME", "X_PASSWORD", "X_SESSION_FILE", "REDDIT_USERNAME", "REDDIT_PASSWORD", "REDDIT_SESSION_FILE", "MEDIUM_SID", "MEDIUM_UID", "MEDIUM_SESSION_FILE",
               "CHROMA_PERSIST_DIR", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "HEADLESS_BROWSER"}
    assert keys & removed == set()
    assert not list(SKILLS.glob("*/scripts/login_*.py"))


def test_docs_describe_v2_only():
    for name in ("AGENTS.md", "README.md"):
        t = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"(?i)chroma|hypothesis-miner|user-skill-synthesizer|vector-search|rag-search|login_x|X_PASSWORD|sentence-transformers", t), name
        assert "knowledge.db" in t and "Knowledge Card" in t, name


def test_slash_command_sources_are_complete():
    names = {p.stem for p in (ROOT / "commands").glob("*.md")}
    assert {"finsocnet", "search", "card", "person", "strategy", "compare", "explore", "explore-step", "mine", "gaps", "sessions", "improve", "feedback", "skills", "install-skill"} <= names
    for p in (ROOT / "commands").glob("*.md"):
        assert frontmatter(p).get("description"), p.name


def test_schema_files_are_valid_json_schema():
    from jsonschema import Draft202012Validator
    for p in (ROOT / "finsocnet" / "core" / "schemas").glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(p.read_text()))


def test_installer_renders_every_harness_and_uninstalls_cleanly(tmp_path, monkeypatch):
    from finsocnet import installer
    monkeypatch.setenv("FINSOCNET_INSTALL_HOME", str(tmp_path))
    monkeypatch.setattr(installer, "CONFIG", tmp_path / "cfg")
    monkeypatch.setattr(installer, "MANIFEST", tmp_path / "cfg" / "installed.json")
    res = installer.install_harness("all")
    assert {r["harness"] for r in res} == set(installer.HARNESSES) and all("error" not in r for r in res)
    claude = tmp_path / ".claude" / "commands"
    assert (claude / "finsocnet.md").exists() and (claude / "finsocnet" / "search.md").read_text().count("$ARGUMENTS") >= 1
    link = tmp_path / ".claude" / "skills" / "knowledge-db"
    assert link.is_symlink() and link.resolve() == (SKILLS / "knowledge-db").resolve()
    ts = (tmp_path / ".omp" / "agent" / "extensions" / "finsocnet.ts").read_text()
    assert "registerCommand" in ts and '"strategy"' in ts and str(ROOT) in ts
    bridge = (tmp_path / ".codex" / "skills" / "finsocnet-bridge" / "SKILL.md").read_text()
    assert bridge.startswith("---") and "/finsocnet:search" in bridge and (tmp_path / ".codex" / "skills" / "market-idea-miner").is_symlink()
    installer.install_harness("all")  # idempotent
    installer.install_harness("all", uninstall=True)
    leftovers = [p for p in tmp_path.rglob("*") if p.is_file() or p.is_symlink()]
    assert [str(p) for p in leftovers if "cfg" not in p.parts] == []
