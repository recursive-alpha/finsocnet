"""Read-only access for agents that need a question the other `kb` commands do not answer: `kb query`, `kb schema`.

Agents must never open `knowledge.db` themselves (no python/sqlite3 scripts); this is the sanctioned way to read. Writes always go
through the typed `kb` commands, which validate and keep provenance."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from finsocnet.core import config
from finsocnet.core.output import CliError

MAX_ROWS = 1000
_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
_HIDDEN = re.compile(r"(_fts($|_)|^sqlite_|embeddings?$)")


def _readonly() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{config.db_path()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def query(sql: str, limit: int = 200) -> dict[str, Any]:
    """Run one SELECT (or WITH ... SELECT). Anything else is refused by the SQLite authorizer, not by pattern matching."""
    sql = sql.strip().rstrip(";")
    if not sql or ";" in sql:
        raise CliError("VALIDATION_ERROR", "send exactly one SELECT statement", "no semicolons, no multiple statements")
    if not re.match(r"(?is)^(select|with)\b", sql):
        raise CliError("VALIDATION_ERROR", "only SELECT queries are allowed", "writes go through the typed kb commands (docs/agent-guide.md)")
    limit = max(1, min(int(limit), MAX_ROWS))
    conn = _readonly()
    try:
        conn.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY)
        try:
            cur = conn.execute(sql)
            rows = cur.fetchmany(limit + 1)
        except sqlite3.Error as e:
            raise CliError("VALIDATION_ERROR", f"{type(e).__name__}: {e}", "see `kb schema` for tables and columns") from e
        cols = [d[0] for d in cur.description or []]
        out = [dict(zip(cols, [v if not isinstance(v, bytes) else f"<{len(v)} bytes>" for v in r])) for r in rows[:limit]]
        return {"columns": cols, "rows": out, "count": len(out), "truncated": len(rows) > limit}
    finally:
        conn.close()


def schema(table: str | None = None) -> dict[str, Any]:
    conn = _readonly()
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name") if not _HIDDEN.search(r[0])]
        if table:
            if table not in names:
                raise CliError("NOT_FOUND", f"table {table} not found", f"tables: {', '.join(names)}")
            names = [table]
        out = {}
        for n in names:
            cols = [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"]), "notnull": bool(c["notnull"])} for c in conn.execute(f"PRAGMA table_info({n})")]
            out[n] = {"columns": cols, "rows": conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]} if table else {"columns": [c["name"] for c in cols], "rows": conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]}
        return {"tables": out}
    finally:
        conn.close()
