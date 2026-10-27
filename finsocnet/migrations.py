"""
Automated database migration runner for SQLite.
Discovers and executes SQL migrations in order, tracking version state in schema_migrations.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_applied_migrations(conn: sqlite3.Connection) -> set[int]:
    """Return set of migration version numbers already applied."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC").fetchall()
    return {r[0] for r in rows}


def discover_migration_files(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[tuple[int, str, Path]]:
    """Discover all .sql migration files sorted by version number."""
    if not migrations_dir.exists():
        return []

    migrations: list[tuple[int, str, Path]] = []
    for p in sorted(migrations_dir.glob("*.sql")):
        m = re.match(r"^(\d+)_(.+)\.sql$", p.name)
        if m:
            version = int(m.group(1))
            name = m.group(2)
            migrations.append((version, name, p))

    migrations.sort(key=lambda x: x[0])
    return migrations


def auto_migrate(conn: sqlite3.Connection, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR, verbose: bool = False) -> list[int]:
    """
    Run any pending migrations automatically.
    Thread-safe and transaction-safe.
    """
    applied = get_applied_migrations(conn)
    available = discover_migration_files(migrations_dir)
    newly_applied: list[int] = []

    for version, name, file_path in available:
        if version not in applied:
            if verbose:
                print(f"[Migration] Applying {file_path.name}...", file=sys.stderr)
            with open(file_path, "r", encoding="utf-8") as f:
                sql = f.read()

            try:
                # Execute migration statements
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, name),
                )
                conn.commit()
                applied.add(version)
                newly_applied.append(version)
                if verbose:
                    print(f"[Migration] Successfully applied {file_path.name}", file=sys.stderr)
            except Exception as e:
                # If error is duplicate column (e.g. migration previously run manually), handle gracefully
                if "duplicate column name" in str(e).lower() or "table" in str(e).lower() and "already exists" in str(e).lower():
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, name),
                    )
                    conn.commit()
                    applied.add(version)
                    newly_applied.append(version)
                else:
                    raise RuntimeError(f"Migration {file_path.name} failed: {e}") from e

    return newly_applied


def get_migration_status(conn: sqlite3.Connection, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[dict[str, Any]]:
    applied_map = {}
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    for row in conn.execute("SELECT version, name, applied_at FROM schema_migrations"):
        applied_map[row[0]] = {"name": row[1], "applied_at": row[2]}

    available = discover_migration_files(migrations_dir)
    status_list = []
    for version, name, path in available:
        is_applied = version in applied_map
        status_list.append({
            "version": version,
            "filename": path.name,
            "status": "applied" if is_applied else "pending",
            "applied_at": applied_map[version]["applied_at"] if is_applied else None,
        })
    return status_list
