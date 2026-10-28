"""Rate budgets per platform (specs/04-sessions-browser.md §7), counted in `budget_usage`."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import yaml

from finsocnet.core import config
from finsocnet.core.db import transaction
from finsocnet.core.output import CliError

WINDOWS = {"minute": ("per_minute", timedelta(minutes=1)), "hour": ("per_hour", timedelta(hours=1)), "day": ("per_day", timedelta(days=1))}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    return yaml.safe_load(open(path, encoding="utf-8")) or {}


def load_budgets() -> dict[str, Any]:
    return _load(str(config.repo_root() / "config" / "budgets.yaml"))


def limits(platform: str) -> dict[str, int]:
    b = load_budgets()
    return {**b.get("default", {}), **b.get(platform, {})}


def window_start(now: datetime, kind: str) -> datetime:
    if kind == "minute":
        return now.replace(second=0, microsecond=0)
    if kind == "hour":
        return now.replace(minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _fmt(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def charge(conn: sqlite3.Connection, platform: str, units: int = 1, now: datetime | None = None) -> dict[str, int]:
    """Count `units` against the minute/hour/day windows in one transaction; exit 4 BUDGET_EXHAUSTED when any is full."""
    now = now or datetime.now(timezone.utc)
    lim = limits(platform)
    with transaction(conn):
        remaining: dict[str, int] = {}
        for kind, (key, span) in WINDOWS.items():
            start = window_start(now, kind)
            row = conn.execute("SELECT count FROM budget_usage WHERE platform = ? AND window_kind = ? AND window_start = ?",
                               (platform, kind, _fmt(start))).fetchone()
            used = row["count"] if row else 0
            if used + units > lim[key]:
                retry = max(1, int((start + span - now).total_seconds()) + 1)
                raise CliError("BUDGET_EXHAUSTED", f"{platform} {kind} budget of {lim[key]} is used up",
                               f"retry after the {kind} window ends", retry_after_sec=retry)
            remaining[kind] = lim[key] - used - units
        for kind in WINDOWS:
            conn.execute(
                "INSERT INTO budget_usage (platform, window_kind, window_start, count) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (platform, window_kind, window_start) DO UPDATE SET count = count + excluded.count",
                (platform, kind, _fmt(window_start(now, kind)), units))
    return remaining


def remaining(conn: sqlite3.Connection, platform: str, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    lim = limits(platform)
    out = {}
    for kind, (key, _) in WINDOWS.items():
        row = conn.execute("SELECT count FROM budget_usage WHERE platform = ? AND window_kind = ? AND window_start = ?",
                           (platform, kind, _fmt(window_start(now, kind)))).fetchone()
        out[kind] = lim[key] - (row["count"] if row else 0)
    return out


def exhausted(conn: sqlite3.Connection, platform: str, now: datetime | None = None) -> bool:
    return any(v <= 0 for v in remaining(conn, platform, now).values())
