"""Migration runner for `.sql` and `.py` migrations (specs/01-database.md §5.1).

A `.py` migration defines `up(conn)`. Each migration runs in one transaction with foreign keys off, followed by
`PRAGMA foreign_key_check`. A backup is taken before any pending migration is applied.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from finsocnet.core import config
from finsocnet.core.db import backup, db_file, default_backup_path

log = logging.getLogger("finsocnet.migrations")

_NAME_RE = re.compile(r"^(\d+)_(.+)\.(sql|py)$")


class MigrationError(RuntimeError):
    pass


def split_sql(script: str) -> list[str]:
    """Split a script into statements without breaking trigger bodies (uses sqlite3.complete_statement)."""
    statements: list[str] = []
    buf = ""
    for line in script.splitlines(keepends=True):
        buf += line
        if buf.strip() and sqlite3.complete_statement(buf):
            statements.append(buf.strip())
            buf = ""
    if buf.strip() and not all(l.strip().startswith("--") or not l.strip() for l in buf.splitlines()):
        statements.append(buf.strip())
    return statements


def exec_sql(conn: sqlite3.Connection, script: str) -> None:
    """Run a script statement by statement inside the caller's transaction (no implicit commit)."""
    for stmt in split_sql(script):
        conn.execute(stmt)


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               version INTEGER PRIMARY KEY,
               name TEXT NOT NULL,
               applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )


def discover(migrations_dir: Path | None = None) -> list[tuple[int, str, Path]]:
    """Migrations sorted by version. When `.py` and `.sql` share a number, the `.py` runs (it executes the `.sql`)."""
    d = migrations_dir or config.migrations_dir()
    found: dict[int, tuple[int, str, Path]] = {}
    for p in sorted(d.iterdir()) if d.exists() else []:
        m = _NAME_RE.match(p.name)
        if not m:
            continue
        version = int(m.group(1))
        if version in found and p.suffix == ".sql":
            continue
        found[version] = (version, m.group(2), p)
    return [found[v] for v in sorted(found)]


def applied_versions(conn: sqlite3.Connection) -> set[int]:
    ensure_migrations_table(conn)
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def status(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[dict[str, Any]]:
    ensure_migrations_table(conn)
    applied = {r[0]: r[2] for r in conn.execute("SELECT version, name, applied_at FROM schema_migrations")}
    return [
        {
            "version": v,
            "name": name,
            "filename": path.name,
            "status": "applied" if v in applied else "pending",
            "applied_at": applied.get(v),
        }
        for v, name, path in discover(migrations_dir)
    ]


def pending(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[tuple[int, str, Path]]:
    done = applied_versions(conn)
    return [m for m in discover(migrations_dir) if m[0] not in done]


def _has_user_tables(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name <> 'schema_migrations'"
    ).fetchone()
    return row[0] > 0


def _load_py(path: Path):
    spec = importlib.util.spec_from_file_location(f"finsocnet_migration_{path.stem}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "up"):
        raise MigrationError(f"{path.name} does not define up(conn)")
    return mod


def migrate(
    conn: sqlite3.Connection,
    migrations_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply pending migrations. Returns `{pending, applied, backups, summaries, warnings}`."""
    todo = pending(conn, migrations_dir)
    result: dict[str, Any] = {
        "pending": [f"{v:03d}_{n}" for v, n, _ in todo],
        "applied": [],
        "backups": [],
        "summaries": {},
        "warnings": [],
    }
    if dry_run or not todo:
        return result

    dbfile = db_file(conn)
    had_data = _has_user_tables(conn)  # a brand-new database has nothing worth backing up
    for version, name, path in todo:
        if had_data:
            dest = default_backup_path(dbfile, f"-pre-{version:03d}")
            try:
                backup(conn, dest)
            except Exception as e:  # abort if the backup fails
                raise MigrationError(f"backup before migration {version:03d} failed: {e}") from e
            result["backups"].append(str(dest))

        log.info("applying migration %s", path.name)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            summary: Any = None
            if path.suffix == ".sql":
                exec_sql(conn, path.read_text(encoding="utf-8"))
            else:
                summary = _load_py(path).up(conn)
            all_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            # legacy_* tables are kept as-is for Phase 2 and may carry orphans from v1 (FKs were never enforced there).
            legacy = [v for v in all_violations if str(v[0]).startswith("legacy_")]
            violations = [v for v in all_violations if not str(v[0]).startswith("legacy_")]
            if legacy:
                result["warnings"].append(f"{path.name}: {len(legacy)} pre-existing foreign-key orphan(s) in legacy_* tables were left untouched")
            if violations:
                sample = [tuple(v) for v in violations[:5]]
                raise MigrationError(f"foreign_key_check failed after {path.name}: {len(violations)} violation(s), e.g. {sample}")
            ensure_migrations_table(conn)
            conn.execute("INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (version, name))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        result["applied"].append(f"{version:03d}_{name}")
        if summary is not None:
            result["summaries"][f"{version:03d}_{name}"] = summary
    return result
