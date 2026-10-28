"""HTTP client for platform adapters: retries with backoff, user agent, proxy, budgets, error mapping to exit codes."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from finsocnet.core import budgets
from finsocnet.core.db import connect
from finsocnet.core.output import CliError

log = logging.getLogger("finsocnet.http")
USER_AGENT = "FinSocNet/2.0 (+https://github.com/recursive-alpha/finsocnet)"
_transport: httpx.BaseTransport | None = None  # tests inject httpx.MockTransport here


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _transport
    _transport = t


def _charge(platform: str) -> None:
    try:
        conn = connect()
    except Exception:  # noqa: BLE001 - no database yet (e.g. a first run): do not block fetching
        return
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'budget_usage'").fetchone():
            budgets.charge(conn, platform)
    finally:
        conn.close()


def request(method: str, url: str, *, platform: str = "default", params: dict[str, Any] | None = None, headers: dict[str, str] | None = None,
            json: Any = None, data: Any = None, timeout: float = 30.0, retries: int = 3, charge: bool = True, follow_redirects: bool = True) -> httpx.Response:
    """One budgeted request. 5xx and network errors retry with exponential backoff; 4xx map to the exit-code table."""
    if charge:
        _charge(platform)
    h = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9, */*;q=0.8", **(headers or {})}
    proxy = os.getenv("FINSOCNET_PROXY") or None
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(transport=_transport, proxy=None if _transport else proxy, timeout=timeout, follow_redirects=follow_redirects, headers=h) as c:
                r = c.request(method, url, params=params, json=json, data=data)
        except httpx.HTTPError as e:
            last = e
            log.warning("%s %s failed (%s), attempt %d", method, url, type(e).__name__, attempt + 1)
            time.sleep(min(2 ** attempt, 8) if _transport is None else 0)
            continue
        if r.status_code >= 500 and attempt < retries:
            time.sleep(min(2 ** attempt, 8) if _transport is None else 0)
            continue
        raise_for_status(r, platform)
        return r
    raise CliError("RATE_LIMITED", f"network error talking to {platform}: {type(last).__name__}", "retry later", retry_after_sec=60)


def raise_for_status(r: httpx.Response, platform: str) -> None:
    code = r.status_code
    if code < 400:
        return
    if code == 429:
        ra = r.headers.get("Retry-After", "")
        raise CliError("RATE_LIMITED", f"{platform} rate limit (HTTP 429)", "wait before retrying", retry_after_sec=int(ra) if ra.isdigit() else 120)
    if code in (401, 403):
        raise CliError("LOGIN_REQUIRED", f"{platform} refused the request (HTTP {code})",
                       "the content needs a login or a different network path; export your session (`finsocnet session export`) or use the browser adapter")
    if code == 404:
        raise CliError("NOT_FOUND", f"{r.request.url} not found (HTTP 404)")
    if code == 410:
        raise CliError("GONE", f"{r.request.url} is gone (HTTP 410)")
    raise CliError("RATE_LIMITED", f"{platform} answered HTTP {code}", "retry later", retry_after_sec=300)


def get_json(url: str, **kw: Any) -> Any:
    return request("GET", url, **kw).json()


def get_text(url: str, **kw: Any) -> str:
    return request("GET", url, **kw).text
