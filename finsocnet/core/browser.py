"""The one agent browser, attached over CDP (docs/spec/04 §6, ADR-006). No script may call `chromium.launch()`,
`launch_persistent_context()` or `browser.new_context()`: everything goes through `attach()` and `page()`."""

from __future__ import annotations

import fcntl
import json
import os
import random
import re
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator

import yaml

from finsocnet.core import budgets, config
from finsocnet.core.db import connect
from finsocnet.core.output import CliError

CHECK_TEXT_CHARS = 5000


def cdp_url() -> str:
    return os.getenv("CDP_URL", "http://127.0.0.1:9222")


def profile_dir() -> Path:
    return config.resolve_path(os.getenv("BROWSER_PROFILE_DIR", "data/browser-profile"))


@lru_cache(maxsize=4)
def _platforms(path: str) -> dict[str, Any]:
    return yaml.safe_load(open(path, encoding="utf-8")) or {}


def platforms() -> dict[str, Any]:
    return _platforms(str(config.repo_root() / "config" / "platforms.yaml"))


def platform_for_domain(domain: str) -> str | None:
    from finsocnet.core.sessions.formats import registrable_domain
    d = registrable_domain(domain)
    for name, cfg in platforms().items():
        if any(registrable_domain(x) == d for x in cfg.get("domains", [])):
            return name
    return None


def classify_page(platform: str, url: str, text: str) -> tuple[str, str] | None:
    """`(code, reason)` when the page is a login wall or a security checkpoint, else None. Checkpoints win."""
    cfg = platforms().get(platform, {})
    hay = f"{url}\n{text[:CHECK_TEXT_CHARS]}".lower()
    for pat in cfg.get("checkpoint_patterns", []):
        if pat.lower() in hay:
            return "CHECKPOINT", f"{platform} shows a security check ({pat!r})"
    for pat in cfg.get("logged_out_url_patterns", []):
        if pat.lower() in url.lower():
            return "LOGIN_REQUIRED", f"{platform} redirected to a login page ({pat!r})"
    return None


def reexport_hint(platform: str) -> str:
    return (f"On your machine: open {platform}, log in (and complete any check), then run "
            f"`finsocnet session export && finsocnet session push`.")


def check_page(platform: str, page: Any) -> None:
    """Raise exit-3 errors (`LOGIN_REQUIRED`/`CHECKPOINT`) when the page is a login wall or a checkpoint."""
    try:
        text = page.inner_text("body", timeout=3000)
    except Exception:  # noqa: BLE001 - a page without a body is checked by URL only
        text = ""
    hit = classify_page(platform, page.url, text)
    if hit:
        raise CliError(hit[0], hit[1], reexport_hint(platform))


def attach() -> tuple[Any, Any, Any]:
    """`connect_over_cdp` to the agent Chrome; returns (playwright, browser, default context). Never creates a context."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(cdp_url())
    except Exception as e:  # noqa: BLE001
        pw.stop()
        raise CliError("BROWSER_UNAVAILABLE", f"cannot reach the agent browser at {cdp_url()}: {type(e).__name__}",
                       "start it with `uv run .agents/skills/agent-browser/scripts/agent_browser.py start`") from e
    if not browser.contexts:
        pw.stop()
        raise CliError("BROWSER_UNAVAILABLE", "the agent browser has no default context", "restart it with agent_browser.py stop && start")
    return pw, browser, browser.contexts[0]


@contextmanager
def platform_lock(platform: str, timeout: float = 120.0) -> Iterator[None]:
    """One script per platform at a time (`data/browser-profile/.lock-<platform>`)."""
    d = profile_dir()
    d.mkdir(parents=True, exist_ok=True)
    fh = open(d / f".lock-{platform}", "w")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.monotonic() > deadline:
                fh.close()
                raise CliError("RATE_LIMITED", f"another script is using {platform}", "retry shortly", retry_after_sec=30)
            time.sleep(0.5)
    try:
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


@contextmanager
def page(platform: str, *, block: tuple[str, ...] = ("media", "font")) -> Iterator[Any]:
    """Charge the budget (exit 4 when exhausted), open a page in the default context, optionally block resource types."""
    conn = connect()
    try:
        budgets.charge(conn, platform)
    finally:
        conn.close()
    with platform_lock(platform):
        pw, browser, ctx = attach()
        pg = ctx.new_page()
        if block:
            pg.route("**/*", lambda route: route.abort() if route.request.resource_type in block else route.continue_())
        try:
            yield pg
        finally:
            try:
                pg.close()
            finally:
                pw.stop()


def goto(pg: Any, platform: str, url: str, *, wait: str = "domcontentloaded", timeout_ms: int = 30000) -> None:
    """Navigate, pause like a person, then run `check_page`. Use this instead of `page.goto` in adapters."""
    pg.goto(url, wait_until=wait, timeout=timeout_ms)
    human_pause(platform)
    check_page(platform, pg)


def human_pause(platform: str) -> None:
    lim = budgets.limits(platform)
    time.sleep(random.uniform(lim["min_delay_ms"], lim["max_delay_ms"]) / 1000)


@contextmanager
def capture_json(pg: Any, url_pattern: str) -> Iterator[list[Any]]:
    """Collect JSON bodies of responses whose URL matches `url_pattern` while the caller navigates or scrolls."""
    rx = re.compile(url_pattern)
    bodies: list[Any] = []

    def on_response(resp: Any) -> None:
        if rx.search(resp.url):
            try:
                bodies.append(resp.json())
            except Exception:  # noqa: BLE001 - not JSON or body gone
                pass

    pg.on("response", on_response)
    try:
        yield bodies
    finally:
        pg.remove_listener("response", on_response)


def scroll(pg: Any, platform: str, *, max_scrolls: int = 10, until: Callable[[], bool] | None = None) -> int:
    """Scroll with human pauses; stop at `max_scrolls`, when `until()` is true, or when the height stops growing."""
    last = pg.evaluate("document.body.scrollHeight")
    n = 0
    for n in range(1, max_scrolls + 1):
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        human_pause(platform)
        if until and until():
            break
        height = pg.evaluate("document.body.scrollHeight")
        if height == last:
            break
        last = height
    return n
