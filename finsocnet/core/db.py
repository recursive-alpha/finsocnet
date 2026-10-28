"""SQLite connection rules (docs/spec/01-database.md §1)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from finsocnet.core import config

MIN_SQLITE = (3, 38, 0)


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the knowledge database with the mandatory pragmas.

    The connection is in autocommit mode (`isolation_level=None`); use `transaction()` for writes.
    """
    p = Path(path) if path else config.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """`BEGIN IMMEDIATE` so concurrent writers wait instead of failing mid-transaction."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


@contextmanager
def savepoint(conn: sqlite3.Connection, name: str = "sp") -> Iterator[sqlite3.Connection]:
    """One SAVEPOINT per item inside an open transaction; a failure rolls back only this item."""
    conn.execute(f"SAVEPOINT {name}")
    try:
        yield conn
    except BaseException:
        conn.execute(f"ROLLBACK TO {name}")
        conn.execute(f"RELEASE {name}")
        raise
    else:
        conn.execute(f"RELEASE {name}")


def backup(conn: sqlite3.Connection, dest: str | Path) -> Path:
    """Copy the database with the SQLite backup API."""
    d = Path(dest)
    d.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(d)
    try:
        conn.backup(target)
    finally:
        target.close()
    return d


def default_backup_path(conn_path: Path, suffix: str = "") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return conn_path.parent / "backups" / f"knowledge-{stamp}{suffix}.db"


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def loads(text: str | None, default: Any = None) -> Any:
    return json.loads(text) if text else default


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def db_file(conn: sqlite3.Connection) -> Path:
    row = conn.execute("PRAGMA database_list").fetchone()
    return Path(row["file"])
