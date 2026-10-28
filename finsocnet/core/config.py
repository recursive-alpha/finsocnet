"""Environment loading and paths (specs/00-conventions.md §6)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(_PACKAGE_ROOT / ".env")


def repo_root() -> Path:
    """Repository root; `FINSOCNET_ROOT` overrides it (tests, relocated checkouts)."""
    override = os.getenv("FINSOCNET_ROOT")
    return Path(override).resolve() if override else _PACKAGE_ROOT


REPO_ROOT = _PACKAGE_ROOT


def resolve_path(value: str | os.PathLike[str]) -> Path:
    """Resolve a path relative to the repo root, never to the current directory."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else repo_root() / p


def db_path() -> Path:
    return resolve_path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))


def data_dir() -> Path:
    return repo_root() / "data"


def work_dir(run_id: int) -> Path:
    return data_dir() / "work" / str(run_id)


def migrations_dir() -> Path:
    return repo_root() / "migrations"


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent / "schemas"


def log_level() -> str:
    return os.getenv("FINSOCNET_LOG_LEVEL", "INFO").upper()


def env_run_id() -> int | None:
    raw = os.getenv("FINSOCNET_RUN_ID")
    return int(raw) if raw and raw.isdigit() else None
